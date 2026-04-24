# Administrationsübersicht

Das Administrationsfeld ist nur vom Rechner aus zugänglich, auf dem Trove läuft. Öffnen Sie `http://localhost:7770/admin` in einem Browser auf dieser Maschine und melden Sie sich mit den während der Einrichtung festgelegten Anmeldedaten an.

!!! warning "Admin-Zugriff ist auf localhost beschränkt"
    Die Admin-Anmeldung ist absichtlich vor allen anderen Geräten im Netzwerk verborgen. Dies ist eine Sicherheitsmaßnahme. Um Trove zu verwalten, müssen Sie physisch am Server anwesend sein oder einen SSH-Tunnel verwenden.

## Die vier Tabs

| Tab | Was Sie tun können |
|---|---|
| **Einstellungen** | KI-Modell auswählen, Kontextfenstergröße festlegen, Anzeigesprache ändern |
| **Dokumente** | Dateien hochladen, in Ordnern organisieren, KI-generierte Zusammenfassungen anzeigen |
| **Gems** | Gems erstellen, bearbeiten und löschen |
| **Protokolle** | Die letzten 1.000 Zeilen des Serverprotokolls anzeigen, alle 5 Sekunden automatisch aktualisiert |

## LAN-URL

Der Tab Einstellungen zeigt die **LAN-URL** — die Adresse, die andere Geräte verwenden sollten, um auf Trove zuzugreifen. Kopieren Sie sie und teilen Sie sie mit Ihren Benutzern.

## Nächste Schritte

- [Installation](installation.md)
- [Gems verwalten](gems.md)
- [Dokumente verwalten](documents.md)
- [Einstellungsreferenz](settings.md)
