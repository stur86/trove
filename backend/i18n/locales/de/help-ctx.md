## Das Kontextfenster

Das Kontextfenster bestimmt, wie viel Text das Modell in einer einzelnen Aufgabe lesen und schreiben kann. Es wird in **Tokens** gemessen — etwa drei Viertel eines Wortes pro Token.

**Richtlinien:**

- **4.096–8.192** — geeignet für kurze Eingaben und knappe Antworten. Am schnellsten und verbraucht den wenigsten Speicher.
- **16.384–32.768** — angemessen, wenn Aufgaben lange Dokumente oder detaillierte Ausgaben umfassen.
- **Höhere Werte** — verbrauchen deutlich mehr Speicher. Auf Maschinen mit wenig RAM kann dies den Server verlangsamen oder dazu führen, dass der Server nicht mehr reagiert.

Eine gute Faustregel: Stellen Sie es auf den kleinsten Wert ein, der Ihre längste erwartete Aufgabe komfortabel bewältigt. Wenn eine Antwort mitten im Satz abgeschnitten erscheint, erhöhen Sie diesen Wert und klicken Sie auf **Einstellungen speichern**, um das Modell neu zu erstellen.
