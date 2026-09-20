"""Tests gegen eine simulierte Hue Bridge (HTTP statt HTTPS, gleiche API-Form).

Start: python3 -m unittest discover tests
"""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server  # noqa: E402

KEY = "test-key"
ROOMS = [{"id": "r1", "metadata": {"name": "Wohnzimmer"}},
         {"id": "r2", "metadata": {"name": "Kinderzimmer"}}]
ZONES = [{"id": "z1", "metadata": {"name": "Leseecke"}}]
SCENES = [
    {"id": "s1", "metadata": {"name": "Nachtlicht"}, "group": {"rid": "r1"}},
    {"id": "s2", "metadata": {"name": "Nachtlicht"}, "group": {"rid": "r2"}},
    {"id": "s3", "metadata": {"name": "Entspannen"}, "group": {"rid": "r1"}},
    {"id": "s4", "metadata": {"name": "Lesen"}, "group": {"rid": "z1"}},
]


# Das Repo enthaelt keine Buecher, deshalb legen die Tests sich eins an.
FIXTURE_BOOK = {
    "title": "Beispielbuch",
    "room": "Wohnzimmer",
    "cues": [
        {"label": "Ein ruhiger Abend", "scene": {"name": "Entspannen", "room": "Wohnzimmer"},
         "loop": "demo-rauschen.wav", "triggers": []},
        {"label": "Die Glocke schlägt", "oneshot": "demo-glocke.wav", "triggers": ["Glocke"]},
        {"label": "Es wird Nacht", "scene": {"name": "Nachtlicht", "room": "Wohnzimmer"},
         "loop": None, "triggers": ["Nacht"]},
    ],
}


class MockBridge(BaseHTTPRequestHandler):
    recalls = []

    def log_message(self, *a):
        pass

    def _send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth(self):
        if self.headers.get("hue-application-key") != KEY:
            self._send(403, {"errors": [{"description": "unauthorized"}]})
            return False
        return True

    def do_GET(self):
        if not self._auth():
            return
        data = {"/clip/v2/resource/room": ROOMS, "/clip/v2/resource/zone": ZONES,
                "/clip/v2/resource/scene": SCENES}.get(self.path)
        self._send(200 if data is not None else 404, {"data": data or [], "errors": []})

    def do_PUT(self):
        if not self._auth():
            return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        MockBridge.recalls.append((self.path.rsplit("/", 1)[-1], body))
        self._send(200, {"data": [], "errors": []})


def start(handler):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def call(url, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class WithBridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.books = tempfile.TemporaryDirectory()
        cls.books_dir = server.BOOKS_DIR
        server.BOOKS_DIR = Path(cls.books.name)
        server.write_book(server.BOOKS_DIR / "beispiel.json", server.format_book(FIXTURE_BOOK))
        cls.bridge_srv, bridge_url = start(MockBridge)
        server.Handler.bridge = server.Bridge(bridge_url, KEY)
        cls.app_srv, cls.app = start(server.Handler)

    @classmethod
    def tearDownClass(cls):
        cls.app_srv.shutdown()
        cls.bridge_srv.shutdown()
        server.BOOKS_DIR = cls.books_dir
        cls.books.cleanup()

    def setUp(self):
        MockBridge.recalls.clear()

    def test_unique_scene_with_room(self):
        s, b = call(self.app + "/api/scene", "POST", {"name": "Nachtlicht", "room": "Kinderzimmer"})
        self.assertEqual(s, 200, b)
        self.assertEqual(MockBridge.recalls, [("s2", {"recall": {"action": "active"}})])

    def test_case_insensitive_and_zone(self):
        s, _ = call(self.app + "/api/scene", "POST", {"name": "lesen", "room": "leseecke"})
        self.assertEqual(s, 200)
        self.assertEqual(MockBridge.recalls[0][0], "s4")

    def test_dynamic_recall(self):
        call(self.app + "/api/scene", "POST", {"name": "Entspannen", "dynamic": True})
        self.assertEqual(MockBridge.recalls[0][1], {"recall": {"action": "dynamic_palette"}})

    def test_ambiguous_scene_rejected(self):
        s, b = call(self.app + "/api/scene", "POST", {"name": "Nachtlicht"})
        self.assertEqual(s, 404)
        self.assertIn("mehreren Räumen", json.loads(b)["error"])
        self.assertEqual(MockBridge.recalls, [])

    def test_missing_scene(self):
        s, b = call(self.app + "/api/scene", "POST", {"name": "Gibtsnicht"})
        self.assertEqual(s, 404)
        self.assertIn("nicht gefunden", json.loads(b)["error"])

    def test_bad_request(self):
        s, _ = call(self.app + "/api/scene", "POST", {"room": "Wohnzimmer"})
        self.assertEqual(s, 400)

    def test_books_and_example(self):
        s, b = call(self.app + "/api/books")
        j = json.loads(b)
        self.assertTrue(j["lights"])
        self.assertIn("beispiel", [x["id"] for x in j["books"]])
        s, b = call(self.app + "/api/books/beispiel")
        self.assertEqual(s, 200)
        self.assertGreater(len(json.loads(b)["cues"]), 0)

    def test_static_and_sounds(self):
        self.assertEqual(call(self.app + "/")[0], 200)
        self.assertEqual(call(self.app + "/sounds/demo-glocke.wav")[0], 200)

    def test_no_path_traversal(self):
        for p in ("/static/../server.py", "/sounds/../server.py",
                  "/static/%2e%2e/server.py", "/api/books/..%2fserver", "/server.py"):
            s, body = call(self.app + p)
            self.assertNotEqual(s, 200, p)
            self.assertNotIn(b"import", body, p)


class DryRun(unittest.TestCase):
    def test_dry_run_without_bridge(self):
        server.Handler.bridge = None
        srv, url = start(server.Handler)
        try:
            s, b = call(url + "/api/scene", "POST", {"name": "Nachtlicht"})
            self.assertEqual(s, 200)
            self.assertTrue(json.loads(b)["dry_run"])
        finally:
            srv.shutdown()


class Pages(unittest.TestCase):
    """Seitenzahlen (ADR 0008) und Positionen innerhalb einer Seite (ADR 0009)."""

    def problems(self, *cues, **book):
        return [p["text"] for p in server.book_problems({"cues": list(cues), **book})]

    def test_pages_and_positions_accepted(self):
        self.assertEqual(self.problems(
            {"label": "Wald", "page": 3},
            {"label": "Ast", "at": 0.6},
            {"label": "Lichtung", "page": 7}), [])

    def test_pages_must_ascend(self):
        self.assertIn("aufsteigen", self.problems(
            {"label": "a", "page": 7}, {"label": "b", "page": 3})[0])

    def test_positions_must_ascend_within_their_page(self):
        self.assertIn("innerhalb der Seite", self.problems(
            {"label": "a", "page": 1}, {"label": "b", "at": 0.6}, {"label": "c", "at": 0.6})[0])

    def test_position_needs_a_page_before_it(self):
        self.assertIn("braucht davor", self.problems(
            {"label": "a", "at": 0.5}, {"label": "b", "page": 2})[0])

    def test_position_only_in_a_book_with_pages(self):
        self.assertIn("nur in einem Buch mit Seitenzahlen",
                      self.problems({"label": "a", "at": 0.5})[0])

    def test_position_and_page_exclude_each_other(self):
        self.assertIn("ohne «page»", self.problems({"label": "a", "page": 1, "at": 0.5})[0])

    def test_field_types(self):
        self.assertIn("ganze Zahl", self.problems({"label": "a", "page": 1.5})[0])
        self.assertIn("zwischen 0 und 1",
                      self.problems({"label": "a", "page": 1}, {"label": "b", "at": 1})[0])

    def test_sync_hash_is_text(self):
        self.assertEqual(self.problems({"label": "a"}, sync={"hash": "abc"}), [])
        self.assertIn("Vorlese-App", self.problems({"label": "a"}, sync={"hash": 5})[0])
        self.assertIn("sync.raum", self.problems({"label": "a"},
                                                 sync={"hash": "abc", "raum": "x"})[0])

    def test_moment_says_first_when_it_comes(self):
        text = server.format_book({"cues": [{"oneshot": "x.wav", "at": 0.5, "label": "Ast"}],
                                   "sync": {"hash": "abc"}, "title": "T"})
        self.assertIn('{"label": "Ast", "at": 0.5, "oneshot": "x.wav"}', text)
        self.assertLess(text.index('"sync"'), text.index('"cues"'))


if __name__ == "__main__":
    unittest.main()
