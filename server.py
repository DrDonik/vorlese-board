#!/usr/bin/env python3
"""Vorlese-Board: lokaler Server fuer Licht- und Klang-Cues beim Vorlesen.

Nur Python-Standardbibliothek. Start:
    python3 server.py            # Server auf Port 8765
    python3 server.py --pair     # einmalig: App-Key von der Bridge holen
    python3 server.py --scenes   # alle Hue-Szenen mit Raum und mittlerer Helligkeit
    python3 server.py --scenes Mondlicht   # dazu jede Lampe mit Helligkeit und Farbe
    python3 server.py --pin      # PIN zum Bearbeiten von iPad und iPhone setzen

Ohne config.json laeuft der Server im Trockenmodus: Szenenaufrufe werden
nur protokolliert, Sounds funktionieren trotzdem.
"""
import getpass
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import ssl
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from http.cookies import CookieError, SimpleCookie
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
BOOKS_DIR = ROOT / "books"
SOUNDS_DIR = ROOT / "sounds"
PORT = 8765

BOOK_FIELDS = {"title", "room", "sync", "cues"}
# Feste Reihenfolge beim Schreiben; Unbekanntes steht vor den Momenten und faellt so auf.
BOOK_KEY_ORDER = {"title": 0, "room": 1, "sync": 2, "cues": 4}
# In einem Moment steht erst, wann er kommt, dann was er schaltet; Unbekanntes am Ende.
CUE_KEY_ORDER = {"label": 0, "page": 1, "at": 1, "span": 2, "scene": 3, "loop": 4,
                 "oneshot": 5, "triggers": 6}
CUE_FIELDS = {"label", "scene", "loop", "oneshot", "page", "at", "span", "triggers"}
SCENE_FIELDS = {"name", "room", "dynamic"}
SYNC_FIELDS = {"hash"}
MAX_HASH = 64  # so lang ist die Buchkennung in der Vorlese-App hoechstens
# Grenzen fuer «span»: Eine Seite ist hoechstens fuenfmal so lang wie eine normale.
SPAN_MIN, SPAN_MAX = 0.2, 5
SOUND_TYPES = {".mp3", ".m4a", ".wav", ".aac"}
MAX_BODY = 1_000_000
BOOK_LOCK = threading.Lock()  # Vergleichen und Schreiben einer Buchdatei am Stueck

# Bearbeiten ist durch eine PIN geschuetzt (ADR 0006).
PIN_ITERATIONS = 600_000
PIN_MAX_FAILURES = 5
PIN_LOCK_SECONDS = 60
SESSION_COOKIE = "vorlese_session"
EDIT_HEADER = "X-Vorlese-Board"  # fremde Webseiten koennen ihn nicht ohne CORS-Freigabe senden
NO_PIN = ("Bearbeiten geht auf diesem Gerät erst, wenn am Mac eine PIN gesetzt ist: "
          "python3 server.py --pin")
WRONG_HOST = ("Bearbeiten geht nur über den .local-Namen des Macs oder seine IP-Adresse, "
              "nicht über «{host}». Den .local-Namen zeigt der Mac unter "
              "Systemeinstellungen > Allgemein > Freigaben.")


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def update_config(**values):
    """Einzelne Eintraege setzen, die uebrigen (Bridge, PIN) bleiben erhalten."""
    config = load_config()
    config.update(values)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def pin_hash(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, PIN_ITERATIONS)


def trusted_host(host):
    """Host-Header, der sicher dieses Geraet meint: localhost, ein .local-Name oder eine IP.

    Webseiten mit eigener Domain, die per DNS-Rebinding auf den Mac zeigen, fallen damit weg.
    """
    name = urllib.parse.urlsplit("//" + (host or "")).hostname
    if not name:
        return False
    if name == "localhost" or name.endswith(".local"):
        return True
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        return False


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

    def scene_lights(self):
        """Pro Szenen-ID die Lampen der Szene als Paare (Lampenname, Einstellung)."""
        lights = {l["id"]: l["metadata"]["name"]
                  for l in self._request("GET", "/clip/v2/resource/light")["data"]}
        return {s["id"]: sorted(((lights.get(a["target"]["rid"], "?"), a["action"])
                                 for a in s["actions"]), key=lambda pair: pair[0])
                for s in self._request("GET", "/clip/v2/resource/scene")["data"]}

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


def light_brightness(action):
    """Helligkeit einer Lampe in einer Szene in Prozent; aus ist 0, ohne Dimmer 100."""
    if not action.get("on", {}).get("on", True):
        return 0
    return action.get("dimming", {}).get("brightness", 100)


def describe_light(action):
    """Einstellung einer Lampe in einer Szene, z. B. «45 %, 2700 K» oder «aus»."""
    if not action.get("on", {}).get("on", True):
        return "aus"
    parts = [f"{light_brightness(action):.0f} %"]
    mirek = action.get("color_temperature", {}).get("mirek")
    xy = action.get("color", {}).get("xy")
    if mirek:
        parts.append(f"{round(1_000_000 / mirek, -2):.0f} K")
    elif xy:
        parts.append(f"Farbe x={xy['x']:.3f} y={xy['y']:.3f}")
    return ", ".join(parts)


def list_scenes(bridge, name=None):
    """Szenen mit mittlerer Helligkeit auflisten; mit Namen zusaetzlich jede Lampe einzeln."""
    scenes = sorted(bridge.scenes(), key=lambda s: (s["room"], s["name"]))
    if name is not None:
        scenes = find_scenes(scenes, name)
        if not scenes:
            sys.exit(f"Szene «{name}» nicht gefunden")
    lights = bridge.scene_lights()
    for s in scenes:
        actions = [action for _, action in lights.get(s["id"], [])]
        mean = (f"Ø {sum(map(light_brightness, actions)) / len(actions):3.0f} %"
                if actions else "keine Lampen")
        print(f"{s['room']:<20} {s['name']:<28} {mean}")
        if name is not None:
            for light, action in lights.get(s["id"], []):
                print(f"    {light:<28} {describe_light(action)}")


def valid_book_id(book_id):
    return bool(book_id) and book_id.replace("-", "").replace("_", "").isalnum()


def read_book(path):
    """Buchdatei lesen: (Daten, None) oder (None, Grund), wenn sie sich nicht oeffnen laesst."""
    if not valid_book_id(path.stem):
        return None, "Dateiname darf nur Buchstaben, Ziffern, - und _ enthalten"
    return parse_book(path.read_bytes())


def parse_book(raw):
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        return None, f"JSON-Fehler in Zeile {e.lineno}, Spalte {e.colno}: {e.msg}"
    except UnicodeDecodeError:
        return None, "Datei ist nicht als UTF-8 gespeichert"
    error = structure_error(data)
    return (None, error) if error else (data, None)


def structure_error(data):
    """Grund, warum sich ein Buch gar nicht oeffnen liesse, sonst None."""
    if not isinstance(data, dict) or not isinstance(data.get("cues"), list):
        return "Erwartet: ein Objekt mit einer Liste «cues»"
    if not all(isinstance(c, dict) for c in data["cues"]):
        return "Jeder Moment in «cues» muss ein Objekt sein"
    return None


def book_version(raw):
    """Kennung eines Dateistands, damit der Editor nichts Fremdes ueberschreibt."""
    return hashlib.sha256(raw).hexdigest()[:16]


def format_book(data):
    """Buch als JSON mit einem Moment pro Zeile: kurze Diffs, gut von Hand zu bearbeiten."""
    def compact(value):
        return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))
    def ordered(cue):
        return {k: cue[k] for k in sorted(cue, key=lambda k: CUE_KEY_ORDER.get(k, 7))}

    fields = []
    for key, value in sorted(data.items(), key=lambda kv: BOOK_KEY_ORDER.get(kv[0], 3)):
        if key == "cues" and value:
            cues = ",\n".join(f"    {compact(ordered(c))}" for c in value)
            fields.append(f"  {compact(key)}: [\n{cues}\n  ]")
        else:
            fields.append(f"  {compact(key)}: {compact(value)}")
    return "{\n" + ",\n".join(fields) + "\n}\n"


def write_book(path, text):
    """Atomar schreiben: Wer die Datei liest, sieht den alten oder den neuen Stand."""
    tmp = path.with_name(f".{path.stem}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def new_book_id(title):
    """Freier Dateiname aus dem Titel: «Der Grüffelo» -> der-grueffelo."""
    slug = unicodedata.normalize("NFC", title.lower())
    for umlaut, plain in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        slug = slug.replace(umlaut, plain)
    slug = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:60].strip("-") or "buch"
    candidate, n = slug, 2
    while (BOOKS_DIR / f"{candidate}.json").exists():
        candidate, n = f"{slug}-{n}", n + 1
    return candidate


def sound_exists(name):
    try:
        path = (SOUNDS_DIR / name).resolve()
    except (OSError, ValueError):  # z. B. Nullbyte im Namen
        return False
    return path.is_relative_to(SOUNDS_DIR.resolve()) and path.is_file()


def book_problems(data, scenes=None):
    """Probleme eines lesbaren Buchs. Ohne scenes werden Szenen nicht geprueft.

    Je Problem: cue (Index oder None fuers ganze Buch), field (betroffenes Feld
    oder None), message (fuer die Anzeige am Feld) und text (ganzer Satz fuers Regal).
    """
    problems = []
    cues = data["cues"]

    def book_problem(msg):
        problems.append({"cue": None, "field": None, "message": msg, "text": msg})

    def cue_problem(i, msg, field):
        label = cues[i].get("label")
        where = (f"Moment {i + 1} «{label}»" if isinstance(label, str) and label.strip()
                 else f"Moment {i + 1}")
        problems.append({"cue": i, "field": field, "message": msg, "text": f"{where}: {msg}"})

    for key in sorted(data.keys() - BOOK_FIELDS):
        book_problem(f"unbekanntes Feld «{key}»")
    if "title" in data and not isinstance(data["title"], str):
        book_problem("«title» muss Text sein")
    if "room" in data and not isinstance(data["room"], str):
        book_problem("«room» muss Text sein")
    if "sync" in data:
        add_sync_problems(data["sync"], book_problem)
    add_page_problems(cues, cue_problem)
    for i, cue in enumerate(cues):
        label = cue.get("label")
        has_label = isinstance(label, str) and label.strip()

        def add(msg, field):
            cue_problem(i, msg, field)

        if not has_label:
            add("Bezeichnung «label» fehlt", "label")
        for key in sorted(cue.keys() - CUE_FIELDS):
            add(f"unbekanntes Feld «{key}»", None)
        if "scene" in cue:
            add_scene_problems(cue["scene"], scenes, lambda msg: add(msg, "scene"))
        if "loop" in cue and cue["loop"] is not None:
            add_sound_problem(cue["loop"], "loop", lambda msg: add(msg, "loop"))
        if "oneshot" in cue:
            add_sound_problem(cue["oneshot"], "oneshot", lambda msg: add(msg, "oneshot"))
        triggers = cue.get("triggers", [])
        if not isinstance(triggers, list) or not all(isinstance(t, str) for t in triggers):
            add("«triggers» muss eine Liste von Texten sein", "triggers")
    return problems


def add_sync_problems(sync, add):
    """Verknuepfung mit einem Buch der Vorlese-App (ADR 0008)."""
    if not isinstance(sync, dict):
        return add("«sync» muss ein Objekt mit «hash» sein")
    for key in sorted(sync.keys() - SYNC_FIELDS):
        add(f"unbekanntes Feld «sync.{key}»")
    value = sync.get("hash")
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_HASH:
        add("«sync.hash» muss die Kennung des Buchs in der Vorlese-App sein")


def is_end_cue(cue):
    """Der Schlussmoment: Er kommt, wenn das Buch zugeklappt wird (ADR 0011)."""
    return cue.get("page") == "end"


def has_page_number(cue):
    """Ob der Moment einer Seite der Vorlese-App zugeordnet ist (ADR 0008)."""
    value = cue.get("page")
    return isinstance(value, int) and not isinstance(value, bool)


def add_page_problems(cues, add):
    """Seitenzahlen (ADR 0008), Positionen (ADR 0009), Seitenlaengen (ADR 0010)
    und der Schlussmoment (ADR 0011).

    «page» steigt ueber das Buch hinweg, «at» steigt innerhalb seiner Seite und
    gehoert zu dem Moment, der keine eigene Seite hat. «span» sagt, wie lang die
    Seite gegenueber einer normalen ist, und gehoert deshalb zu «page».
    «page»: «end» gehoert zu keiner Seite und steht als letzter Moment im Buch.
    """
    has_pages = any(has_page_number(cue) for cue in cues)
    page, position = None, None
    for i, cue in enumerate(cues):
        if "page" in cue:
            value, end = cue["page"], is_end_cue(cue)
            if end:
                if i != len(cues) - 1:
                    add(i, "der Schlussmoment «end» ist der letzte Moment des Buchs", "when")
            elif not has_page_number(cue) or value < 0:
                add(i, "«page» muss eine ganze Zahl ab 0 oder «end» sein", "when")
            elif page is not None and value <= page:
                add(i, f"«page» muss aufsteigen, Seite {value} steht hinter Seite {page}", "when")
            else:
                page, position = value, None
            if "at" in cue:
                add(i, "«at» gehört zu einem Moment ohne «page»", "when")
            if "span" in cue:
                if end:
                    add(i, "«span» gehört zu einer Seite, der Schlussmoment ist keine", "when")
                else:
                    add_span_problem(cue["span"], lambda msg: add(i, msg, "when"))
            continue
        if "span" in cue:
            add(i, "«span» gehört zu einem Moment mit «page»", "when")
        if "at" not in cue:
            continue
        value = cue["at"]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value < 1:
            add(i, "«at» muss eine Zahl zwischen 0 und 1 sein", "when")
        elif not has_pages:
            add(i, "«at» wirkt nur in einem Buch mit Seitenzahlen", "when")
        elif page is None:
            add(i, "«at» braucht davor einen Moment mit «page»", "when")
        elif position is not None and value <= position:
            add(i, f"«at» muss innerhalb der Seite aufsteigen, {value} steht hinter {position}", "when")
        else:
            position = value


def add_span_problem(value, add):
    """Laenge einer Seite gegenueber einer normalen Seite des Buchs (ADR 0010)."""
    if not isinstance(value, (int, float)) or isinstance(value, bool) \
            or not SPAN_MIN <= value <= SPAN_MAX:
        add(f"«span» muss eine Zahl zwischen {SPAN_MIN} und {SPAN_MAX} sein")


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
    pin = None     # {salt, hash} aus config.json, wird in main() gesetzt

    # Zustand der PIN-Pruefung, gemeinsam fuer alle Anfragen bis zum Neustart
    sessions = set()
    pin_failures = 0
    pin_locked_until = 0.0
    pin_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        if "/api/" in (self.path or ""):
            super().log_message(fmt, *args)

    def _json(self, status, payload, headers=()):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _edit_access(self):
        """ok: darf bearbeiten; pin: PIN noetig; no_pin: noch keine PIN gesetzt;
        wrong_host: ueber diesen Namen aufgerufen, geht Bearbeiten nie (siehe trusted_host).

        Am Mac selbst (localhost) braucht es keine PIN; dort liegen die Dateien ohnehin offen.
        """
        if not trusted_host(self.headers.get("Host")):
            return "wrong_host"
        if self.client_address[0] in ("127.0.0.1", "::1"):
            return "ok"
        try:
            cookie = SimpleCookie(self.headers.get("Cookie") or "").get(SESSION_COOKIE)
        except CookieError:
            cookie = None
        if cookie and cookie.value in self.sessions:
            return "ok"
        return "pin" if self.pin else "no_pin"

    def _guard(self, need_session=True):
        """Fehlerantwort senden und True liefern, wenn die Anfrage nicht bearbeiten darf."""
        if self.headers.get(EDIT_HEADER) != "1":
            self._json(403, {"error": "Anfrage abgelehnt"})
            return True
        access = self._edit_access()
        if access == "wrong_host":
            host = urllib.parse.urlsplit("//" + (self.headers.get("Host") or "")).hostname or ""
            self._json(403, {"error": WRONG_HOST.format(host=host)})
        elif need_session and access == "pin":
            self._json(401, {"error": "PIN nötig", "pin": True})
        elif need_session and access == "no_pin":
            self._json(403, {"error": NO_PIN})
        else:
            return False
        return True

    def _check_pin(self):
        """PIN pruefen; nach zu vielen Fehlversuchen kurz sperren. Erfolg setzt das Sitzungs-Cookie."""
        if self._guard(need_session=False):
            return
        if not self.pin:
            return self._json(403, {"error": NO_PIN})
        req = self._read_json()
        pin = req.get("pin") if isinstance(req, dict) else None
        cls = Handler
        with cls.pin_lock:  # auch die Hash-Berechnung, damit Versuche nacheinander laufen
            wait = cls.pin_locked_until - time.monotonic()
            if wait > 0:
                return self._json(429, {"error": f"Zu viele Versuche. In {int(wait) + 1} Sekunden wieder möglich."})
            if isinstance(pin, str) and hmac.compare_digest(
                    pin_hash(pin, bytes.fromhex(self.pin["salt"])).hex(), self.pin["hash"]):
                cls.pin_failures = 0
                token = secrets.token_urlsafe(32)
                cls.sessions.add(token)
            else:
                cls.pin_failures += 1
                if cls.pin_failures >= PIN_MAX_FAILURES:
                    cls.pin_failures = 0
                    cls.pin_locked_until = time.monotonic() + PIN_LOCK_SECONDS
                    return self._json(429, {"error": f"Zu viele Versuche. In {PIN_LOCK_SECONDS} Sekunden wieder möglich."})
                left = PIN_MAX_FAILURES - cls.pin_failures
                return self._json(403, {"error": f"Falsche PIN, noch {left} Versuch{'e' if left > 1 else ''}"})
        # Gueltig bis zum Neustart des Servers; Max-Age haelt das Cookie so lange im Browser.
        cookie = f"{SESSION_COOKIE}={token}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Strict"
        return self._json(200, {"ok": True}, [("Set-Cookie", cookie)])

    def _read_json(self):
        """Anfragekoerper als JSON, oder None, wenn er fehlt, zu gross oder kein JSON ist."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= MAX_BODY:
                return None
            return json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            return None

    def _book_path(self):
        """(Buch-ID, Zusatz) fuer /api/books/<id>[/<zusatz>], sonst (None, None)."""
        parts = self.path.split("/")
        if len(parts) not in (4, 5) or parts[:3] != ["", "api", "books"]:
            return None, None
        book_id = urllib.parse.unquote(parts[3])
        if not valid_book_id(book_id):
            return None, None
        return book_id, (parts[4] if len(parts) == 5 else None)

    def _scenes(self, refresh):
        """(Szenenliste oder None, Fehlermeldung oder None) fuer Pruefung und Auswahl."""
        if self.bridge is None:
            return None, None
        try:
            return self.bridge.scenes(refresh=refresh), None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return None, f"Bridge nicht erreichbar: {e}"

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/static/index.html"
        if self.path == "/api/books":
            return self._books()
        if self.path == "/api/scenes":
            scenes, error = self._scenes(refresh=True)
            listed = sorted(({"name": s["name"], "room": s["room"]} for s in scenes or []),
                            key=lambda s: (s["room"].casefold(), s["name"].casefold()))
            return self._json(200, {"scenes": listed, "lights": self.bridge is not None,
                                    "error": error})
        if self.path == "/api/sounds":
            sounds = sorted((f.name for f in SOUNDS_DIR.iterdir()
                             if f.is_file() and f.suffix.lower() in SOUND_TYPES),
                            key=str.casefold)
            return self._json(200, {"sounds": sounds})
        if self.path.startswith("/api/"):
            book_id, extra = self._book_path()
            if book_id is None or extra not in (None, "edit"):
                return self._json(404, {"error": "Nicht gefunden"})
            if extra == "edit" and self._guard():
                return
            f = BOOKS_DIR / f"{book_id}.json"
            if not f.exists():
                return self._json(404, {"error": "Buch nicht gefunden"})
            raw = f.read_bytes()
            data, error = parse_book(raw)
            if error:
                return self._json(400, {"error": f"Buchdatei fehlerhaft: {error}"})
            if extra is None:
                return self._json(200, data)
            scenes, _ = self._scenes(refresh=False)
            return self._json(200, {"book": data, "version": book_version(raw),
                                    "problems": book_problems(data, scenes)})
        target = Path(self.translate_path(self.path)).resolve()
        allowed = [(ROOT / d).resolve() for d in ("static", "sounds")]
        if any(target.is_relative_to(d) for d in allowed):
            return super().do_GET()
        return self._json(404, {"error": "Nicht gefunden"})

    def _books(self):
        """Regal: alle Buecher, jeweils mit Problemen gegen Bridge und Sound-Ordner geprueft."""
        scenes, bridge_error = self._scenes(refresh=True)
        books = []
        for f in sorted(BOOKS_DIR.glob("*.json")):
            data, error = read_book(f)
            if error:
                books.append({"id": f.stem, "title": f.stem, "error": error})
                continue
            title = data.get("title")
            sync = data.get("sync")
            book_hash = sync.get("hash") if isinstance(sync, dict) else None
            books.append({"id": f.stem,
                          "title": title if isinstance(title, str) and title.strip() else f.stem,
                          "cues": len(data["cues"]),
                          # Kennung des Buchs in der Vorlese-App: Damit findet ein
                          # Lese-Code das Buch im Regal wieder (ADR 0008).
                          "hash": book_hash if isinstance(book_hash, str) else None,
                          # Nur echte Seitenzahlen: Der Schlussmoment allein
                          # laesst ein Buch der Vorlese-App noch nicht folgen.
                          "pages": any(has_page_number(c) for c in data["cues"]),
                          "problems": [p["text"] for p in book_problems(data, scenes)]})
        return self._json(200, {"books": books, "lights": self.bridge is not None,
                                "bridge_error": bridge_error, "edit": self._edit_access()})

    def do_PUT(self):
        """Buch speichern: {version, book}. Die Version muss dem Stand auf der Platte entsprechen."""
        book_id, extra = self._book_path()
        if book_id is None or extra is not None:
            return self._json(404, {"error": "Nicht gefunden"})
        if self._guard():
            return
        req = self._read_json()
        if not isinstance(req, dict) or not isinstance(req.get("version"), str):
            return self._json(400, {"error": "Erwartet: {version, book}"})
        error = structure_error(req.get("book"))
        if error:
            return self._json(400, {"error": error})
        text = format_book(req["book"])
        f = BOOKS_DIR / f"{book_id}.json"
        with BOOK_LOCK:
            if not f.exists():
                return self._json(404, {"error": "Die Buchdatei gibt es nicht mehr"})
            if book_version(f.read_bytes()) != req["version"]:
                return self._json(409, {"error": "Die Datei wurde ausserhalb geändert"})
            write_book(f, text)
        scenes, _ = self._scenes(refresh=False)
        return self._json(200, {"version": book_version(text.encode()),
                                "problems": book_problems(req["book"], scenes)})

    def do_POST(self):
        if self.path == "/api/books":
            return self._create_book()
        if self.path == "/api/pin":
            return self._check_pin()
        if self.path != "/api/scene":
            return self._json(404, {"error": "Nicht gefunden"})
        req = self._read_json()
        if not isinstance(req, dict) or not isinstance(req.get("name"), str):
            return self._json(400, {"error": "Erwartet: {name, room?, dynamic?}"})
        name = req["name"]
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

    def _create_book(self):
        """Neues Buch mit einem leeren Moment; der Dateiname folgt aus dem Titel."""
        if self._guard():
            return
        req = self._read_json()
        title = req.get("title") if isinstance(req, dict) else None
        if not isinstance(title, str) or not title.strip():
            return self._json(400, {"error": "Titel eingeben"})
        with BOOK_LOCK:
            book_id = new_book_id(title)
            write_book(BOOKS_DIR / f"{book_id}.json",
                       format_book({"title": title.strip(), "cues": [{"label": ""}]}))
        return self._json(201, {"id": book_id})


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
    update_config(bridge_ip=ip, app_key=result["success"]["username"])
    print(f"Gespeichert in {CONFIG_PATH.name}.")


def set_pin():
    pin = getpass.getpass("Neue PIN zum Bearbeiten (6 Ziffern): ")
    if not re.fullmatch(r"[0-9]{6}", pin):
        sys.exit("Die PIN muss aus genau 6 Ziffern bestehen.")
    if getpass.getpass("PIN wiederholen: ") != pin:
        sys.exit("Die beiden Eingaben stimmen nicht überein.")
    salt = secrets.token_bytes(16)
    update_config(pin={"salt": salt.hex(), "hash": pin_hash(pin, salt).hex()})
    print(f"PIN gespeichert in {CONFIG_PATH.name}. Einen laufenden Server neu starten.")


def main():
    if "--pair" in sys.argv:
        return pair()
    if "--pin" in sys.argv:
        return set_pin()
    config = load_config()
    bridge = make_bridge(config)
    if "--scenes" in sys.argv:
        if not bridge:
            sys.exit("Keine config.json. Zuerst: python3 server.py --pair")
        rest = sys.argv[sys.argv.index("--scenes") + 1:]
        return list_scenes(bridge, rest[0] if rest else None)
    BOOKS_DIR.mkdir(exist_ok=True)
    SOUNDS_DIR.mkdir(exist_ok=True)
    Handler.bridge = bridge
    Handler.pin = config.get("pin")
    mode = "mit Bridge" if bridge else "Trockenmodus (keine config.json)"
    editing = "mit PIN" if Handler.pin else "nur am Mac, keine PIN gesetzt"
    print(f"Vorlese-Board laeuft auf http://localhost:{PORT} ({mode}; Bearbeiten {editing})")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
