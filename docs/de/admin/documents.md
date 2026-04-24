# Dokumente verwalten

Die Dokumentenbibliothek ermöglicht es Ihnen, der KI Zugang zu den Dateien Ihrer Einrichtung zu geben — Richtlinien, Handbücher, Referenzblätter — ohne sie in die Prompts einzelner Gems einzubetten.

## Ein Dokument hochladen

1. Öffnen Sie den Tab **Dokumente** im Administrationspanel.
2. Wählen Sie einen Zielordner (oder erstellen Sie einen neuen).
3. Klicken Sie auf **Hochladen** und wählen Sie eine Datei.

Unterstützte Formate sind PDF, Word (`.docx`), Klartext und die meisten gängigen Office-Formate. Trove konvertiert hochgeladene Dateien intern mit [Markitdown](https://github.com/microsoft/markitdown) in Klartext. Die Originaldatei wird neben der konvertierten Version aufbewahrt.

Nach dem Hochladen generiert die KI automatisch eine einzeilige Beschreibung des Dokuments. Diese Beschreibung wird im Administrationspanel angezeigt und verwendet, wenn die KI entscheidet, welche Dokumente nachzuschlagen sind.

## Ordner

Dokumente werden in Ordnern organisiert. Ordner sind die Einheit der Zugriffskontrolle: Wenn Sie ein Gem erstellen, gewähren Sie Zugriff auf ganze Ordner oder auf einzelne Dokumente darin.

Um einen Ordner zu erstellen, geben Sie einen Namen in das Feld **Neuer Ordner** ein und drücken Sie Enter (oder den Hinzufügen-Knopf).

Um einen Ordner oder ein Dokument umzubenennen, klicken Sie auf seinen Namen im Administrationspanel.

## Wie die KI Dokumente verwendet

Wenn ein Gem Dokumentenzugriff hat, gibt Trove der KI vor dem Start eine Zusammenfassung aller zugänglichen Dokumente. Die KI kann dann den vollständigen Text jedes Dokuments anfordern, das sie für relevant hält. Es gibt keine Vektorsuche — die KI schlussfolgert aus den Zusammenfassungen und ruft auf Anfrage vollständige Inhalte ab.

Das bedeutet:
- **Kurze, gut benannte Dokumente mit guten Beschreibungen** sind für die KI leichter zu finden und zu verwenden.
- **Sehr große Dokumente** können abgeschnitten werden, um in das Kontextfenster des Modells zu passen.
- Die KI wird Dokumente nicht immer verwenden — sie nutzt sie nur, wenn sie für die Anfrage des Benutzers relevant erscheinen.

## Dokumente herunterladen

Sie können einzelne Dokumente oder ganze Ordner direkt vom Tab Dokumente herunterladen.

- **Ordner** — klicken Sie auf das Download-Symbol (↓) neben einem Ordnernamen, um ein ZIP-Archiv mit der konvertierten Markdown-Version jedes Dokuments in diesem Ordner zu erhalten.
- **Dokument** — klicken Sie auf das Download-Symbol neben einem Dokumentnamen, um seine konvertierte Markdown-Datei (`.md`) zu erhalten.

Diese Downloads enthalten die Klartextversion jeder Datei, wie Trove sie sieht, nicht die ursprünglich hochgeladene Datei.

## Ein Dokument entfernen

Klicken Sie auf die Schaltfläche **Löschen** neben einem Dokument im Administrationspanel. Die Datei und ihre Metadaten werden dauerhaft gelöscht.
