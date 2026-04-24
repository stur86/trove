# Einstellungen

Der Tab **Einstellungen** steuert das KI-Modell und die Anzeigeeinstellungen für den gesamten Server.

## KI-Modell

| Einstellung | Was sie tut |
|---|---|
| **Basismodell** | Die Gemma 4-Variante, die Trove verwendet. In der Liste erscheinen nur bereits heruntergeladene Modelle. |
| **Kontextfenster (num_ctx)** | Wie viel Text das Modell gleichzeitig im Speicher halten kann, gemessen in Tokens (etwa ¾ eines Wortes pro Token). Größere Werte verarbeiten längere Dokumente, verbrauchen aber mehr RAM. |

Nach dem Ändern des Modells oder des Kontextfensters klicken Sie auf **Speichern und neu erstellen**, um die Änderung anzuwenden. Trove erstellt seine interne Modellkonfiguration neu; dies dauert etwa 30 Sekunden und zeigt den Fortschritt auf der Seite an.

### Ein Modell auswählen

| Modell | Effektive Parameter | Min. RAM | Audio | Am besten für |
|---|---|---|---|---|
| `gemma4:e2b` | 2,3B | ~4 GB | Ja | Sehr langsame Rechner, schnellste Antworten |
| `gemma4:e4b` | 4,5B | ~6 GB | Ja | Ausgewogen — empfohlene Standardwahl |
| `gemma4:26b` | 4B aktiv (MoE) | ~10 GB | Nein | Bessere Qualität, ähnliche Geschwindigkeit wie e4b |
| `gemma4:31b` | 31B dicht | ~20 GB | Nein | Höchste Qualität, benötigt einen leistungsstarken Rechner |

!!! tip "Audio-Gems und Modellwahl"
    Nur `gemma4:e2b` und `gemma4:e4b` unterstützen Audioeingabe. Wenn Sie zu einem Modell ohne Audio-Unterstützung wechseln, werden Gems, die Audioeingabe verwenden, für Benutzer ausgeblendet, bis Sie zurückwechseln.

## Sprache

Der **Sprache**-Selektor ändert die Anzeigesprache für die gesamte Trove-Oberfläche, einschließlich Startbildschirm und Gem-Ausführer auf der Benutzerseite. Derzeit unterstützt: Englisch, Französisch, Deutsch, Spanisch, Portugiesisch, Chinesisch (Vereinfacht), Italienisch.

## Daten

Der Abschnitt **Daten** ermöglicht es Ihnen, die gesamte Trove-Konfiguration zu sichern oder ein früheres Backup wiederherzustellen.

### Ein Bundle exportieren

Klicken Sie auf **Bundle exportieren**, um eine einzelne ZIP-Datei (`trove-bundle.zip`) herunterzuladen, die enthält:

- Alle Gems und ihre Einstellungen.
- Alle Dokumentordner, Dokumentmetadaten und den konvertierten Text jedes Dokuments.

Verwenden Sie dies, um Ihre Konfiguration vor größeren Änderungen zu sichern, oder um eine Einrichtung auf eine andere Trove-Instanz zu kopieren.

### Ein Bundle importieren

Klicken Sie auf **Bundle importieren**, um den Importdialog zu öffnen. Wählen Sie eine `.zip`-Datei aus, die von einer beliebigen Trove-Instanz exportiert wurde, und wählen Sie dann einen Importmodus:

| Modus | Was er tut |
|---|---|
| **Hinzufügen** (Standard) | Fügt das Bundle mit den aktuellen Daten zusammen. Vorhandene Gems und Dokumente werden beibehalten. Wenn ein eingehender Eintrag die gleiche ID wie ein vorhandener hat, wird er unter einer neuen ID importiert (z.B. `policy-2`). |
| **Ersetzen** | Löscht alle aktuellen Gems, Dokumente und Ordner, dann importiert alles aus dem Bundle. |

!!! warning "Der Ersetzen-Modus ist unumkehrbar"
    Der Ersetzen-Modus löscht dauerhaft alle vorhandenen Gems und Dokumente vor dem Import. Exportieren Sie zuerst ein Backup, wenn Sie den aktuellen Stand behalten möchten.

Nach einem erfolgreichen Import zeigt eine Zusammenfassung, wie viele Gems und Dokumente importiert wurden und ob welche aufgrund von ID-Konflikten umbenannt wurden.

## LAN-URL

Die im Tab Einstellungen angezeigte LAN-URL ist die Adresse, die Benutzer in Ihrem Netzwerk öffnen sollten. Verwenden Sie die Schaltfläche **Kopieren** und teilen Sie sie — zum Beispiel auf einem Aushang oder per E-Mail.
