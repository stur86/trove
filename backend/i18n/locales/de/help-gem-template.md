## Eine gute Prompt-Vorlage schreiben

Die Vorlage ist die Anweisung, die Sie der KI geben. Verwenden Sie `{{ variablenname }}` an beliebiger Stelle im Text, um ein Feld zu erstellen, das der Benutzer vor dem Ausführen des Gems ausfüllt.

**Beispiel:**

```
Fassen Sie den folgenden Text auf {{ sprache }} zusammen und verwenden Sie dabei maximal {{ max_punkte }} Aufzählungspunkte:

{{ text }}
```

Dadurch werden drei Eingabefelder erstellt: *sprache*, *max_punkte* und *text*.

**Tipps für eine gute Eingabeaufforderung:**

- **Seien Sie präzise** — sagen Sie dem Modell genau, was es produzieren soll.
- **Geben Sie das Format an** — Aufzählungsliste, kurzer Absatz, nummerierte Schritte, Tabelle…
- **Geben Sie ein Beispiel** — wenn die Aufgabe schwierig ist, zeigen Sie, wie eine gute Antwort aussieht.
- **Halten Sie es kurz** — das Modell arbeitet am besten mit klaren, prägnanten Anweisungen.
- **Benennen Sie Variablen eindeutig** — `{{ patientenname }}` ist besser als `{{ name }}`.
