#!/usr/bin/env python3
"""Vorlese-Board: lokaler Server fuer Licht- und Klang-Cues beim Vorlesen.

Nur Python-Standardbibliothek. Start:
    python3 server.py            # Server auf Port 8765
    python3 server.py --pair     # einmalig: App-Key von der Bridge holen
    python3 server.py --scenes   # alle Hue-Szenen mit Raum auflisten

Ohne config.json laeuft der Server im Trockenmodus: Szenenaufrufe werden
nur protokolliert, Sounds funktionieren trotzdem.
"""
import json
import ssl
import sys
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
PORT = 8765


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


class Bridge:
    """Minimaler Client fuer die Hue CLIP API v2 (Bridge v2 und Pro)."""

    def __init__(self, base_url, app_key):
        self.base_url = base_url.rstrip("/")
        self.app_key = app_key
        # Die Bridge nutzt ein selbstsigniertes Zertifikat; im Heimnetz akzeptiert.
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self._scene_cache = None

    def _request(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self.base_url + path, data=data, method=method,
            headers={"hue-application-key": self.app_key,
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, context=self.ctx, timeout=5) as resp:
            return json.loads(resp.read().decode())

    def scenes(self, refresh=False):
        """Liste von {id, name, room} fuer alle Szenen."""
        if self._scene_cache is None or refresh:
            groups = {}
            for kind in ("room", "zone"):
                for g in self._request("GET", f"/clip/v2/resource/{kind}")["data"]:
                    groups[g["id"]] = g["metadata"]["name"]
            self._scene_cache = [
                {"id": s["id"], "name": s["metadata"]["name"],
                 "room": groups.get(s["group"]["rid"], "?")}
                for s in self._request("GET", "/clip/v2/resource/scene")["data"]]
        return self._scene_cache

    def resolve(self, name, room=None):
        matches = [s for s in self.scenes()
                   if s["name"].lower() == name.lower()
                   and (room is None or s["room"].lower() == room.lower())]
        if not matches:
            matches = [s for s in self.scenes(refresh=True)
                       if s["name"].lower() == name.lower()
                       and (room is None or s["room"].lower() == room.lower())]
        if len(matches) != 1:
            where = f" in {room}" if room else ""
            raise LookupError(
                f"Szene '{name}'{where}: {len(matches)} Treffer. "
                "Bei mehreren Treffern im Buch einen Raum angeben.")
        return matches[0]["id"]

    def recall(self, name, room=None, dynamic=False):
        scene_id = self.resolve(name, room)
        action = "dynamic_palette" if dynamic else "active"
        self._request("PUT", f"/clip/v2/resource/scene/{scene_id}",
                      {"recall": {"action": action}})
        return scene_id


def make_bridge(config):
    if config.get("app_key") and (config.get("bridge_ip") or config.get("bridge_url")):
        url = config.get("bridge_url") or f"https://{config['bridge_ip']}"
        return Bridge(url, config["app_key"])
    return None


class Handler(SimpleHTTPRequestHandler):
    bridge = None  # wird in main() gesetzt

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        if "/api/" in (self.path or ""):
            super().log_message(fmt, *args)

    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/static/index.html"
        if self.path == "/api/books":
            books = []
            for f in sorted((ROOT / "books").glob("*.json")):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    books.append({"id": f.stem, "title": data.get("title", f.stem),
                                  "cues": len(data.get("cues", []))})
                except json.JSONDecodeError as e:
                    books.append({"id": f.stem, "title": f.stem, "error": str(e)})
            return self._json(200, {"books": books,
                                    "lights": self.bridge is not None})
        if self.path.startswith("/api/books/"):
            book_id = self.path.rsplit("/", 1)[-1]
            f = ROOT / "books" / f"{book_id}.json"
            if not f.exists() or not book_id.replace("-", "").replace("_", "").isalnum():
                return self._json(404, {"error": "Buch nicht gefunden"})
            try:
                return self._json(200, json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError as e:
                return self._json(400, {"error": f"Buchdatei fehlerhaft: {e}"})
        target = Path(self.translate_path(self.path)).resolve()
        allowed = [(ROOT / d).resolve() for d in ("static", "sounds")]
        if any(target.is_relative_to(d) for d in allowed):
            return super().do_GET()
        return self._json(404, {"error": "Nicht gefunden"})

    def do_POST(self):
        if self.path != "/api/scene":
            return self._json(404, {"error": "Nicht gefunden"})
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
            name = req["name"]
        except (json.JSONDecodeError, KeyError):
            return self._json(400, {"error": "Erwartet: {name, room?, dynamic?}"})
        if self.bridge is None:
            print(f"[Trockenmodus] Szene '{name}' ({req.get('room') or 'ohne Raum'})")
            return self._json(200, {"ok": True, "dry_run": True})
        try:
            sid = self.bridge.recall(name, req.get("room"), bool(req.get("dynamic")))
            return self._json(200, {"ok": True, "scene_id": sid})
        except LookupError as e:
            return self._json(404, {"error": str(e)})
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return self._json(502, {"error": f"Bridge nicht erreichbar: {e}"})


def pair():
    ip = input("IP-Adresse der Bridge (Hue-App > Einstellungen > Bridges): ").strip()
    input("Jetzt den runden Knopf auf der Bridge druecken, dann Enter ...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        f"https://{ip}/api", method="POST",
        data=json.dumps({"devicetype": "vorlese_board#mac",
                         "generateclientkey": True}).encode())
    with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
        result = json.loads(resp.read().decode())[0]
    if "error" in result:
        sys.exit(f"Fehler: {result['error'].get('description')}")
    CONFIG_PATH.write_text(json.dumps(
        {"bridge_ip": ip, "app_key": result["success"]["username"]}, indent=2))
    print(f"Gespeichert in {CONFIG_PATH.name}.")


def main():
    if "--pair" in sys.argv:
        return pair()
    bridge = make_bridge(load_config())
    if "--scenes" in sys.argv:
        if not bridge:
            sys.exit("Keine config.json. Zuerst: python3 server.py --pair")
        for s in sorted(bridge.scenes(), key=lambda s: (s["room"], s["name"])):
            print(f"{s['room']:<20} {s['name']}")
        return
    Handler.bridge = bridge
    mode = "mit Bridge" if bridge else "Trockenmodus (keine config.json)"
    print(f"Vorlese-Board laeuft auf http://localhost:{PORT} ({mode})")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
