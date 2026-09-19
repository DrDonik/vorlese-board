# Vorlese-Board (Stufe 1)

Licht- und Klang-Cues zum Vorlesen. Pro Buch eine Abfolge von Momenten;
beim Lesen tippt man nur «weiter».

## Einrichten (einmalig, auf dem Mac)

    python3 server.py --pair     # Bridge-IP eingeben, Knopf auf der Bridge drücken
    python3 server.py --scenes   # zeigt alle Hue-Szenen mit Raum

Ohne `--pair` läuft alles im Trockenmodus: Sounds spielen, Szenen erscheinen nur im Terminal.

## Starten

    python3 server.py

Auf iPad/iPhone im selben WLAN: `http://<Name-des-Macs>.local:8765`
(Safari > Teilen > Zum Home-Bildschirm). Automatische Sperre des Geräts beim Lesen
ausschalten: Die Bildschirmsperre-Unterdrückung des Browsers funktioniert nur über HTTPS.

Bluetooth-Seitenwender (Pedal, Fernbedienung) funktionieren, sofern sie Pfeiltasten senden.

## Buch anlegen

Im Regal «Neues Buch» wählen, oder bei einem Buch «Bearbeiten» (auch aus dem Lesemodus heraus).
Im Editor:

- Enter in einer Bezeichnung legt den nächsten Moment an: erst das Gerüst tippen, dann ausgestalten.
- Licht wählen schaltet die Szene sofort, Sounds werden beim Auswählen angespielt.
- «Ab hier probelesen» springt in den Lesemodus, mit Licht und Klang wie vor diesem Moment.
- Jede Änderung ist sofort gespeichert. Neue Sounds in `sounds/` legen, sie erscheinen gleich in der Auswahl.

Die Bücher liegen als JSON in `books/<name>.json` und lassen sich auch von Hand bearbeiten.
Der Editor schreibt einen Moment pro Zeile und überschreibt keine Datei, die inzwischen
von Hand geändert wurde.

    { "title": "Mein Buch",
      "cues": [
        { "label": "Im Wald",    "scene": {"name": "Wald", "room": "Wohnzimmer"}, "loop": "wald.mp3" },
        { "label": "Es raschelt", "oneshot": "rascheln.mp3" },
        { "label": "Zauber",     "scene": {"name": "Polarlicht", "room": "Wohnzimmer", "dynamic": true} },
        { "label": "Gute Nacht", "scene": {"name": "Nachtlicht", "room": "Wohnzimmer"}, "loop": null,
          "triggers": ["gute Nacht"] } ] }

- `scene`: Name exakt wie in der Hue-App (Gross-/Kleinschreibung egal); `room` nötig, wenn der
  Name in mehreren Räumen oder Zonen vorkommt. `dynamic: true` startet die Szene dynamisch.
- `loop`: Dateiname = Klangteppich überblenden, `null` = ausblenden, Feld weglassen = weiterlaufen lassen.
- `oneshot`: Einzeleffekt, einmal abgespielt (nur vorwärts, nicht bei «Zurück»).
- `triggers`: Stichwörter für die spätere Spracherkennung (Stufe 2), derzeit ungenutzt.
- Sounds liegen in `sounds/` (mp3, m4a, wav, aac). Die zwei `demo-*.wav` sind generierte Testtöne.
- Die Szenennamen im Beispielbuch sind Platzhalter und an die eigenen Szenen anzupassen.

Das Regal prüft jedes Buch gegen die Szenen der Bridge und den Ordner `sounds/` und listet
unter dem Titel auf, was nicht stimmt (Tippfehler, fehlende Sounds, unbekannte Felder,
JSON-Fehler mit Zeile). Nach dem Ändern einer Datei genügt es, zum Browser zurückzuwechseln.

## Tests

    python3 -m unittest discover tests
