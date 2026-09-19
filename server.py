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
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
BOOKS_DIR = ROOT / "books"
SOUNDS_DIR = ROOT / "sounds"
PORT = 8765

BOOK_FIELDS = {"title", "cues"}
CUE_FIELDS = {"label", "scene", "loop", "oneshot", "triggers"}
SCENE_FIELDS = {"name", "room", "dynamic"}


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
        matches = find_scenes(self.scenes(), name, room)
        if not matches:  # seit dem letzten Abruf angelegt oder umbenannt?
            matches = find_scenes(self.scenes(refresh=True), name, room)
        problem = scene_problem(matches, name, room)
        if problem:
            raise LookupError(problem)
        return matches[0]["id"]

    def recall(self, name, room=None, dynamic=False):
        scene_id = self.resolve(name, room)
        action = "dynamic_palette" if dynamic else "active"
        self._request("PUT", f"/clip/v2/resource/scene/{scene_id}",
                      {"recall": {"action": action}})
        return scene_id


def find_scenes(scenes, name, room=None):
    """Szenen mit diesem Namen (und Raum), ohne Beachtung der Gross-/Kleinschreibung."""
    return [s for s in scenes
            if s["name"].lower() == name.lower()
            and (room is None or s["room"].lower() == room.lower())]


def scene_problem(matches, name, room=None):
    """Fehlermeldung, wenn die Treffer von find_scenes nicht eindeutig sind, sonst None."""
    if len(matches) == 1:
        return None
    if not matches:
        where = f" in «{room}»" if room else ""
        return f"Szene «{name}»{where} nicht gefunden"
    rooms = sorted({m["room"] for m in matches})
    if len(rooms) > 1:
        return (f"Szene «{name}» gibt es in mehreren Räumen oder Zonen "
                f"({', '.join(rooms)}), bitte «room» angeben")
    return f"Szene «{name}» gibt es in «{rooms[0]}» mehrfach, bitte in der Hue-App umbenennen"


def valid_book_id(book_id):
    return bool(book_id) and book_id.replace("-", "").replace("_", "").isalnum()


def read_book(path):
    """Buchdatei lesen: (Daten, None) oder (None, Grund), wenn sie sich nicht oeffnen laesst."""
    if not valid_book_id(path.stem):
        return None, "Dateiname darf nur Buchstaben, Ziffern, - und _ enthalten"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return None, f"JSON-Fehler in Zeile {e.lineno}, Spalte {e.colno}: {e.msg}"
    except UnicodeDecodeError:
        return None, "Datei ist nicht als UTF-8 gespeichert"
    if not isinstance(data, dict) or not isinstance(data.get("cues"), list):
        return None, "Erwartet: ein Objekt mit einer Liste «cues»"
    if not all(isinstance(c, dict) for c in data["cues"]):
        return None, "Jeder Moment in «cues» muss ein Objekt sein"
    return data, None


def sound_exists(name):
    try:
        path = (SOUNDS_DIR / name).resolve()
    except (OSError, ValueError):  # z. B. Nullbyte im Namen
        return False
    return path.is_relative_to(SOUNDS_DIR.resolve()) and path.is_file()


def book_problems(data, scenes=None):
    """Probleme eines lesbaren Buchs, je ein Satz. Ohne scenes werden Szenen nicht geprueft."""
    problems = [f"unbekanntes Feld «{k}»" for k in sorted(data.keys() - BOOK_FIELDS)]
    if "title" in data and not isinstance(data["title"], str):
        problems.append("«title» muss Text sein")
    for i, cue in enumerate(data["cues"], 1):
        label = cue.get("label")
        has_label = isinstance(label, str) and label.strip()
        where = f"Moment {i} «{label}»" if has_label else f"Moment {i}"

        def add(msg):
            problems.append(f"{where}: {msg}")

        if not has_label:
            add("Bezeichnung «label» fehlt")
        for key in sorted(cue.keys() - CUE_FIELDS):
            add(f"unbekanntes Feld «{key}»")
        if "scene" in cue:
            add_scene_problems(cue["scene"], scenes, add)
        if "loop" in cue and cue["loop"] is not None:
            add_sound_problem(cue["loop"], "loop", add)
        if "oneshot" in cue:
            add_sound_problem(cue["oneshot"], "oneshot", add)
        triggers = cue.get("triggers", [])
        if not isinstance(triggers, list) or not all(isinstance(t, str) for t in triggers):
            add("«triggers» muss eine Liste von Texten sein")
    return problems


def add_scene_problems(scene, scenes, add):
    if not isinstance(scene, dict) or not isinstance(scene.get("name"), str) \
            or not scene["name"].strip():
        return add("Szene braucht einen Namen «scene.name»")
    for key in sorted(scene.keys() - SCENE_FIELDS):
        add(f"unbekanntes Feld «scene.{key}»")
    if not isinstance(scene.get("dynamic", False), bool):
        add("«scene.dynamic» muss true oder false sein")
    room = scene.get("room")
    if room is not None and not isinstance(room, str):
        return add("«scene.room» muss Text sein")
    if scenes is not None:
        problem = scene_problem(find_scenes(scenes, scene["name"], room), scene["name"], room)
        if problem:
            add(problem)


def add_sound_problem(name, key, add):
    if not isinstance(name, str) or not name.strip():
        add(f"«{key}» muss ein Dateiname sein" + (" oder null" if key == "loop" else ""))
    elif not sound_exists(name):
        add(f"Sound «{name}» fehlt im Ordner sounds")


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
            return self._books()
        if self.path.startswith("/api/books/"):
            book_id = urllib.parse.unquote(self.path.rsplit("/", 1)[-1])
            f = BOOKS_DIR / f"{book_id}.json"
            if not valid_book_id(book_id) or not f.exists():
                return self._json(404, {"error": "Buch nicht gefunden"})
            data, error = read_book(f)
            if error:
                return self._json(400, {"error": f"Buchdatei fehlerhaft: {error}"})
            return self._json(200, data)
        target = Path(self.translate_path(self.path)).resolve()
        allowed = [(ROOT / d).resolve() for d in ("static", "sounds")]
        if any(target.is_relative_to(d) for d in allowed):
            return super().do_GET()
        return self._json(404, {"error": "Nicht gefunden"})

    def _books(self):
        """Regal: alle Buecher, jeweils mit Problemen gegen Bridge und Sound-Ordner geprueft."""
        scenes, bridge_error = None, None
        if self.bridge is not None:
            try:
                scenes = self.bridge.scenes(refresh=True)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                bridge_error = f"Bridge nicht erreichbar: {e}"
        books = []
        for f in sorted(BOOKS_DIR.glob("*.json")):
            data, error = read_book(f)
            if error:
                books.append({"id": f.stem, "title": f.stem, "error": error})
                continue
            title = data.get("title")
            books.append({"id": f.stem,
                          "title": title if isinstance(title, str) and title.strip() else f.stem,
                          "cues": len(data["cues"]),
                          "problems": book_problems(data, scenes)})
        return self._json(200, {"books": books, "lights": self.bridge is not None,
                                "bridge_error": bridge_error})

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
