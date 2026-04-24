# Gems verwalten

Ein **Gem** ist eine wiederverwendbare KI-Aufgabe mit einem festen Zweck. Benutzer sehen Gems als Karten auf dem Startbildschirm und füllen ein kurzes Formular aus, um sie auszuführen.

## Ein Gem erstellen

1. Öffnen Sie den Tab **Gems** im Administrationspanel.
2. Klicken Sie auf **Neues Gem**.
3. Füllen Sie das Formular aus:

| Feld | Was es tut |
|---|---|
| **Name** | Wird auf der Gem-Karte angezeigt. Halten Sie es kurz und beschreibend. |
| **Beschreibung** | Optional. Ein einzeiliger Hinweis, der unter dem Namen angezeigt wird. |
| **Farbe** | Die Farbe des Gem-Symbols. Verwenden Sie verschiedene Farben, um Gems auf einen Blick leicht unterscheiden zu können. |
| **Prompt-Vorlage** | Die KI-Anweisung. Verwenden Sie `{{ variable_name }}`-Platzhalter für Felder, die der Benutzer ausfüllt. |
| **Fähigkeiten** | Aktivieren Sie *Akzeptiert Bildeingabe*, wenn die Aufgabe ein Foto oder einen Screenshot benötigt. |
| **Ausgabemodus** | *Text* für normale Ausgabe; *Strukturiert (JSON)* für maschinenlesbare Ausgabe. |
| **Dokumentenzugriff** | Welche Dokumentordner oder einzelne Dateien die KI beim Ausführen dieses Gems lesen kann. |

4. Klicken Sie auf **Erstellen**.

## Eine gute Prompt-Vorlage schreiben

Die Vorlage ist die Anweisung, die die KI erhält. Sie kann beliebigen Text sowie Platzhalter enthalten:

```
Fassen Sie den folgenden Text auf {{ language }} zusammen, und verwenden Sie dabei maximal 5 Aufzählungspunkte:

{{ text }}
```

Dadurch werden zwei Eingabefelder für den Benutzer erstellt: *language* und *text*.

**Tipps:**

- Seien Sie präzise. Sagen Sie der KI genau, welches Format Sie möchten.
- Geben Sie die erwartete Ausgabesprache an, wenn das wichtig ist.
- Halten Sie Anweisungen kurz — das Modell arbeitet am besten mit klaren, prägnanten Prompts.
- Testen Sie das Gem selbst, bevor Sie es mit Benutzern teilen.

## Dokumentenzugriff

Jedes Gem kann über den Ordner- und Dokumentenbaum im Gem-Formular Zugriff auf einen Teil der Dokumentenbibliothek erhalten:

- **Ordnerzugriff** — aktivieren Sie das Kontrollkästchen neben einem Ordnernamen. Die KI kann jedes Dokument in diesem Ordner sehen, einschließlich später hinzugefügter. Das Aktivieren eines Ordners aktiviert automatisch alle Dokumente darin.
- **Einzelner Dokumentenzugriff** — klappen Sie einen Ordner auf und aktivieren Sie nur die gewünschten spezifischen Dokumente. Ein Ordner, bei dem einige, aber nicht alle Dokumente aktiviert sind, zeigt einen Teilindikator (−) an.
- **Kein Zugriff** (Standard) — lassen Sie alle Kästchen deaktiviert. Die KI verwendet die Dokumentenbibliothek für dieses Gem nicht.

Wenn ein Gem Dokumentenzugriff hat, entscheidet die KI selbst, ob sie Dokumente nachschlagen oder aus ihrem eigenen Wissen antworten soll.

## Bearbeiten und Löschen

Klicken Sie auf **Bearbeiten** neben einem Gem, um dessen Einstellungen zu ändern. Klicken Sie auf **Löschen**, um es dauerhaft zu entfernen. Es gibt kein Rückgängig.

!!! warning "Ein Gem löschen"
    Gelöschte Gems können nicht wiederhergestellt werden. Benutzer, die versuchen, die URL eines gelöschten Gems zu öffnen, erhalten eine Fehlermeldung.
