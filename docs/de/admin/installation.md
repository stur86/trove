# Installation

Diese Anleitung richtet sich an die Person, die Trove einrichtet. Programmierkenntnisse sind nicht erforderlich.

## Was Sie benötigen

- Ein Computer mit **Linux** (Ubuntu 22.04 oder neuer empfohlen)
- Mindestens **4 GB RAM** (8 GB oder mehr ist besser)
- Mindestens **10 GB freier Festplattenspeicher**
- Eine Internetverbindung *nur während der Installation* — danach läuft Trove vollständig offline

## Schritt 1 — Trove installieren

Öffnen Sie ein Terminal und führen Sie aus:

```bash
curl -LsSf https://raw.githubusercontent.com/stur86/trove/main/install.sh | bash
```

Dadurch wird das Installationsprogramm heruntergeladen, die neueste Trove-Version abgerufen und alles eingerichtet. Dies dauert einige Minuten.

!!! tip "Befehl danach nicht gefunden?"
    Wenn Sie nach dem Abschluss des Installationsprogramms `trove: command not found` sehen, führen Sie den angezeigten Befehl aus (etwa `export PATH="$HOME/.local/bin:$PATH"`), und öffnen Sie dann ein neues Terminalfenster.

## Schritt 2 — Den Einrichtungsassistenten ausführen

Führen Sie den Einrichtungsassistenten **auf demselben Computer aus, auf dem Sie Trove gerade installiert haben**. Die Einrichtungsseite ist nur von diesem Computer aus erreichbar — das ist beabsichtigt.

```bash
trove setup
```

Öffnen Sie dann einen Browser **auf demselben Computer** und rufen Sie auf:

```
http://localhost:7071
```

Der Assistent führt Sie durch sechs Schritte:

1. **Sprache** — wählen Sie die Oberflächensprache
2. **Willkommen** — bestätigt Ihre Hardware und was Trove installieren wird
3. **Ollama installieren** — lädt die KI-Laufzeitumgebung herunter (übersprungen, wenn bereits installiert)
4. **Modell wählen** — wählen Sie ein Gemma 4-Modell; nur Modelle, die Ihre Hardware ausführen kann, werden angezeigt. Dieser Schritt erfordert eine Internetverbindung und kann 10–30 Minuten dauern.
5. **Administratorkonto** — legen Sie einen Benutzernamen und ein Passwort für das Administrationspanel fest
6. **Dienst installieren** — registriert Trove, um beim Start automatisch zu starten

Nach dem Abschluss zeigt das Dashboard die Adresse an, die Sie Ihren Benutzern mitteilen können.

## Schritt 3 — Benutzern eine zuverlässige Adresse geben

Wenn Trove startet, zeigt es eine Adresse wie `http://192.168.1.42:7770` an. Benutzer auf anderen Geräten öffnen diese in einem beliebigen Browser — keine App muss installiert werden.

**Die Adresse kann sich ändern**, jedes Mal wenn der Server neu startet, da Heim- und Büro-Router Adressen automatisch neu vergeben. Wenn sie sich ändert, erhalten Benutzer einen Fehler „Seite nicht erreichbar".

!!! info "Das mit einer statischen IP-Adresse lösen"
    Das Festlegen einer festen („statischen") IP-Adresse für den Server-Computer verhindert, dass sich die Adresse ändert. Sie tun dies nur einmal in den Einstellungen Ihres Routers.

    1. Öffnen Sie die Admin-Seite Ihres Routers — normalerweise `http://192.168.1.1` oder `http://192.168.0.1` (prüfen Sie das Etikett auf Ihrem Router).
    2. Suchen Sie den Bereich **DHCP**, **LAN** oder **IP-Reservierung**.
    3. Suchen Sie den Trove-Server in der Liste der verbundenen Geräte und weisen Sie ihm eine feste Adresse zu.
    4. Speichern Sie und starten Sie den Router neu, wenn Sie dazu aufgefordert werden.

    Wenn Sie dabei Hilfe benötigen, wenden Sie sich an Ihren IT-Support — das ist eine Routineaufgabe.

## Trove starten und stoppen

Wenn Sie den Dienst während der Einrichtung installiert haben, startet Trove automatisch beim Hochfahren. Sie können es auch manuell steuern:

```bash
systemctl --user status trove    # prüfen ob aktiv
systemctl --user restart trove   # neu starten
systemctl --user stop trove      # stoppen
```

Wenn Sie den Dienst übersprungen haben, starten Sie Trove bei Bedarf manuell:

```bash
trove start
```

Drücken Sie `Ctrl + C` zum Stoppen. Um den Dienst auch dann am Laufen zu halten, wenn niemand angemeldet ist (nützlich auf einem Server ohne grafische Oberfläche):

```bash
loginctl enable-linger $USER   # einmalige Einrichtung; kann sudo erfordern
```

## Leitfaden zur Modellauswahl

| Modell | Min. RAM | Audio | Am besten für |
|---|---|---|---|
| Gemma 4 E2B | 4 GB | Ja | Sehr langsame Rechner, schnellste Antworten |
| Gemma 4 E4B | 6 GB | Ja | Ausgewogen — empfohlene Standardwahl |
| Gemma 4 26B | 10 GB | Nein | Bessere Qualität, ähnliche Geschwindigkeit wie E4B |
| Gemma 4 31B | 20 GB | Nein | Höchste Qualität, benötigt einen leistungsstarken Rechner |

## Fehlerbehebung

**„trove: command not found"**
Führen Sie `export PATH="$HOME/.local/bin:$PATH"` aus und versuchen Sie es erneut. Um es dauerhaft zu machen, fügen Sie diese Zeile zu `~/.bashrc` hinzu.

**Die Einrichtungsseite lädt nicht**
Stellen Sie sicher, dass Sie sich auf demselben Computer befinden, auf dem Sie `trove setup` ausgeführt haben, und dass der Befehl noch im Terminal läuft.

**Andere Geräte können Trove nicht erreichen**
Überprüfen Sie, ob `trove start` (oder der Dienst) läuft. Stellen Sie sicher, dass alle Geräte im selben WLAN- oder kabelgebundenen Netzwerk sind. Wenn sich die Adresse ständig ändert, legen Sie eine statische IP an Ihrem Router fest (siehe Schritt 3).

**Der Modell-Download ist sehr langsam**
Der erste Download kann je nach Internetverbindung 10–30 Minuten dauern. Er findet nur einmal statt.
