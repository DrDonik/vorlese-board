# Vorlese-Board (Stufe 1)

Licht- und Klang-Cues zum Vorlesen. Pro Buch eine Abfolge von Momenten;
beim Lesen tippt man nur «weiter».

## Einrichten (einmalig, auf dem Mac)

    python3 server.py --pair     # Bridge-IP eingeben, Knopf auf der Bridge drücken
    python3 server.py --scenes   # zeigt alle Hue-Szenen mit Raum
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
- Licht wählen schaltet die Szene sofort, Sounds werden beim Auswählen angespielt.
- Der «Standardraum» unter dem Titel bestimmt, welcher Raum in der Licht-Auswahl zuerst
  erscheint. Die erste gewählte Szene setzt ihn; in der Auswahl lässt sich mit einem Tipp
  auf alle Räume umschalten.
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
      "cues": [
        { "label": "Im Wald",    "scene": {"name": "Wald", "room": "Wohnzimmer"}, "loop": "wald.mp3" },
        { "label": "Es raschelt", "oneshot": "rascheln.mp3" },
        { "label": "Zauber",     "scene": {"name": "Polarlicht", "room": "Wohnzimmer", "dynamic": true} },
        { "label": "Gute Nacht", "scene": {"name": "Nachtlicht", "room": "Wohnzimmer"}, "loop": null,
          "triggers": ["gute Nacht"] } ] }

- `room`: Standardraum des Buchs. Er filtert nur die Auswahl im Editor; welche Szene ein
  Moment schaltet, steht immer in dessen `scene.room`.
- `scene`: Name exakt wie in der Hue-App (Gross-/Kleinschreibung egal); `room` nötig, wenn der
  Name in mehreren Räumen oder Zonen vorkommt. `dynamic: true` startet die Szene dynamisch.
- `loop`: Dateiname = Klangteppich überblenden, `null` = ausblenden, Feld weglassen = weiterlaufen lassen.
- `oneshot`: Einzeleffekt, einmal abgespielt (nur vorwärts, nicht bei «Zurück»).
- `triggers`: Stichwörter für die spätere Spracherkennung (Stufe 2), derzeit ungenutzt.
- Sounds liegen in `sounds/` (mp3, m4a, wav, aac). Die zwei `demo-*.wav` sind generierte Testtöne.
- Die Szenennamen oben sind Platzhalter; `python3 server.py --scenes` zeigt die eigenen.

Das Regal prüft jedes Buch gegen die Szenen der Bridge und den Ordner `sounds/` und listet
unter dem Titel auf, was nicht stimmt (Tippfehler, fehlende Sounds, unbekannte Felder,
JSON-Fehler mit Zeile). Nach dem Ändern einer Datei genügt es, zum Browser zurückzuwechseln.

## Tests

    python3 -m unittest discover tests
