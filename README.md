# Vorlese-Board (Stufe 1)

Licht- und Klang-Cues zum Vorlesen. Pro Buch eine Abfolge von Momenten;
beim Lesen tippt man nur «weiter».

## Einrichten (einmalig, auf dem Mac)

    python3 server.py --pair     # Bridge-IP eingeben, Knopf auf der Bridge drücken
    python3 server.py --scenes   # zeigt alle Hue-Szenen mit Raum und mittlerer Helligkeit
    python3 server.py --scenes Mondlicht   # dazu jede Lampe der Szene mit Helligkeit und Farbe
    python3 server.py --pin      # PIN (6 Ziffern) zum Bearbeiten auf iPad und iPhone

Ohne `--pair` läuft alles im Trockenmodus: Sounds spielen, Szenen erscheinen nur im Terminal.

## Starten

    python3 server.py

Auf iPad/iPhone im selben WLAN: `http://<Name-des-Macs>.local:8765`. Den Namen zeigt
Systemeinstellungen > Allgemein > Freigaben > Lokaler Hostname. Über andere Namen, etwa
vom Router vergebene, lässt sich vorlesen, aber nicht bearbeiten; die IP-Adresse geht auch.
(Safari > Teilen > Zum Home-Bildschirm). Automatische Sperre des Geräts beim Lesen
ausschalten: Die Bildschirmsperre-Unterdrückung des Browsers funktioniert nur über HTTPS.

Bluetooth-Seitenwender (Pedal, Fernbedienung) funktionieren, sofern sie Pfeiltasten senden.

## Buch anlegen

Im Regal «Neues Buch» wählen, oder bei einem Buch «Bearbeiten» (auch aus dem Lesemodus heraus).
Im Editor:

- Enter in einer Bezeichnung legt den nächsten Moment an: erst das Gerüst tippen, dann ausgestalten.
- Licht wählen schaltet die Szene sofort, ein Blitz blitzt samt Rückkehr, Sounds werden beim Auswählen angespielt.
- Der «Standardraum» unter dem Titel bestimmt, welcher Raum in der Licht-Auswahl zuerst
  erscheint. Die erste gewählte Szene setzt ihn; in der Auswahl lässt sich mit einem Tipp
  auf alle Räume umschalten.
- Spielen alle Momente im selben Raum, nimmt ein neuer Standardraum sie auf einen Tipp mit:
  Die Auswahl sagt, wie viele der Szenen es im neuen Raum schon gibt, und lässt sich
  rückgängig machen. Die Szenennamen bleiben, nur `scene.room` und `flash.room` werden
  neu geschrieben.
- «Ab hier probelesen» springt in den Lesemodus, mit Licht und Klang wie vor diesem Moment.
- Jede Änderung ist sofort gespeichert. Neue Sounds in `sounds/` legen, sie erscheinen gleich in der Auswahl.

Am Mac (`http://localhost:8765`) geht das ohne PIN, auf iPad und iPhone erst mit PIN.
Nach einem Neustart des Servers fragt die App einmal neu nach der PIN; zum Vorlesen braucht es nie eine.

Die Bücher liegen als JSON in `books/<name>.json` und lassen sich auch von Hand bearbeiten.
Der Editor schreibt einen Moment pro Zeile und überschreibt keine Datei, die inzwischen
von Hand geändert wurde. Bücher und eigene Sounds bleiben lokal, im Repo liegen nur die
`demo-*.wav`; ein frisch geklontes Regal ist leer und füllt sich über «Neues Buch».

    { "title": "Mein Buch",
      "room": "Wohnzimmer",
      "sync": {"hash": "5f2c…"},
      "cues": [
        { "label": "Im Wald",    "page": 7, "span": 1.8, "scene": {"name": "Wald", "room": "Wohnzimmer"}, "loop": "wald.mp3" },
        { "label": "Es raschelt", "at": 0.6, "oneshot": "rascheln.mp3" },
        { "label": "Zauber",     "scene": {"name": "Polarlicht", "room": "Wohnzimmer", "dynamic": true} },
        { "label": "Ein Schrei", "flash": {"name": "Blutrot", "room": "Wohnzimmer", "seconds": 2} },
        { "label": "Gute Nacht", "page": 9, "scene": {"name": "Nachtlicht", "room": "Wohnzimmer"}, "loop": null,
          "triggers": ["gute Nacht"] } ] }

- `room`: Standardraum des Buchs. Er filtert nur die Auswahl im Editor und kann die Momente
  auf Wunsch mitnehmen; welche Szene ein Moment schaltet, steht immer in dessen `scene.room`.
- `page`, `at`, `span`, `sync`: nur für das Mitlesen mit der Vorlese-App, siehe unten.
- `scene`: Name exakt wie in der Hue-App (Gross-/Kleinschreibung egal); `room` nötig, wenn der
  Name in mehreren Räumen oder Zonen vorkommt. `dynamic: true` startet die Szene dynamisch.
- `flash`: Blitz, eine Szene für kurze Zeit. Er schaltet hart ein und kehrt nach `seconds`
  (1 bis 10, ohne Angabe 2) weich zum Licht des Moments zurück. Er gehört wie `oneshot`
  nicht zum Zustand: «Voriger Moment» und «Ab hier probelesen» spielen ihn nicht (ADR 0015).
  Licht erzählt die Geschichte, Stimmung tragen Ton und Blitz (ADR 0014).
- `loop`: Dateiname = Klangteppich überblenden, `null` = ausblenden, Feld weglassen = weiterlaufen lassen.
- `oneshot`: Einzeleffekt, einmal abgespielt (nur vorwärts, nicht bei «Voriger Moment»).
- `triggers`: Stichwörter für die spätere Spracherkennung (Stufe 2), derzeit ungenutzt.
- Sounds liegen in `sounds/` (mp3, m4a, wav, aac). Die zwei `demo-*.wav` sind generierte Testtöne.
- Die Szenennamen oben sind Platzhalter; `python3 server.py --scenes` zeigt die eigenen.

Das Regal prüft jedes Buch gegen die Szenen der Bridge und den Ordner `sounds/` und listet
unter dem Titel auf, was nicht stimmt (Tippfehler, fehlende Sounds, unbekannte Felder,
JSON-Fehler mit Zeile). Nach dem Ändern einer Datei genügt es, zum Browser zurückzuwechseln.

## Mit der Super Vorlese-App mitlesen

Wird dasselbe Buch in der [Super Vorlese-App](https://drdonik.github.io/super-vorlese-app)
gelesen, folgt das Board dem Umblättern: beim Vorlesen über die Distanz schaltet es das
Licht im Kinderzimmer, ohne dass dort jemand tippt (ADR 0008, 0009). Stellt die App das Buch
ins Regal, erkennt das Board das Ende und folgt nicht zurück auf Seite 1 (ADR 0011).

1. Im Regal «Gemeinsam lesen» wählen und den sechsstelligen Lese-Code eingeben.
   Beim ersten Mal fragt das Board, welches Buch im Regal gemeint ist, und merkt sich das
   in `sync.hash`. Danach findet derselbe Code das Buch von selbst.
2. Im Editor bekommt jeder Moment die Frage «Wann». Dazu in der Vorlese-App auf die Seite
   blättern und im Board «Seite N» antippen — Seitenzahlen muss man sich nicht merken.
   Unter der Seite steht ihre Länge; sie bleibt unangetastet, bis auf einer Seite ein
   Effekt zu früh kommt.

- `page`: Der Moment gehört zum Anfang dieser Seite. Umblättern stellt Licht und Klangteppich
  so her, wie sie dort wären; übersprungene Einzeleffekte bleiben stumm. Die Zahlen steigen
  über das Buch hinweg an.
- `at`: Position zwischen 0 und 1 auf der zuletzt genannten Seite. Der Moment kommt beim
  Tippen oder zu seiner geschätzten Zeit, was zuerst eintritt; ein Umblättern überschreibt
  beides. Die Zeit schätzt das Board aus dem Lesetempo des Abends, ein Balken zeigt sie an.
- `span`: Wie lang diese Seite gegenüber einer normalen Seite des Buchs ist, zwischen 0.2
  und 5; ohne Angabe gilt 1. Nur die Seiten zueinander zählen, ein gemeinsamer Faktor ändert
  nichts. Bei einem Bilderbuch, dessen Seiten sich in der Textmenge stark unterscheiden,
  träfen die Positionen sonst auf jeder Seite daneben (ADR 0010).
- `page: "end"`: der Schlussmoment, zum Beispiel ein Nachtlicht und `"loop": null`. Er kommt,
  wenn die Vorlese-App das Buch zuklappt und ins Regal stellt, und ebenso beim Weitertippen
  hinter dem letzten Moment. Er steht als letzter Moment im Buch, gehört zu keiner Seite und
  trägt deshalb kein `span` (ADR 0011). Ohne Schlussmoment lässt das Zuklappen Licht und Ton,
  wie sie sind.
- `sync.hash`: Kennung des Buchs in der Vorlese-App. Setzt das Board beim Verbinden selbst.

Das Board liest nur mit und schreibt nie in den Raum. Der Lese-Code bleibt pro Buch auf
dem Gerät gemerkt; ein Raum verfällt 45 Tage nach dem letzten Umblättern, dann braucht es
einen neuen Code. Dieses Gerät braucht dafür Internet; ohne Verbindung bleibt alles wie zuvor.

## Tests

    python3 -m unittest discover tests
