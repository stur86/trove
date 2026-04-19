# trove

![](banner.png)

A local AI platform for non-technical users, built for schools, care homes, libraries, and similar institutions. Staff run pre-defined tasks — summarising a document, drafting a letter, answering a form — without internet access, cloud accounts, or any AI knowledge. Everything runs on one computer inside your building. No data leaves your network.

---

## For administrators: installing Trove

This section is written for the person setting Trove up. You do not need programming experience.

### What you need

- A computer running **Linux** (Ubuntu 22.04 or later recommended)
- At least **4 GB of RAM** (8 GB or more is better)
- At least **10 GB of free disk space**
- An internet connection *during installation only* — after that, Trove runs completely offline

### Step 1 — Install Trove

Open a terminal and run this single command:

```bash
curl -LsSf https://raw.githubusercontent.com/stur86/trove/main/install.sh | bash
```

This fetches the installer, downloads the latest Trove release, and installs everything. It takes a few minutes.

> If you see `trove: command not found` afterwards, the installer will have printed a command to fix this. Run that command, then open a new terminal window.

### Step 2 — Run the setup wizard

Run setup **on the same computer you just installed Trove on**. The setup page is only accessible from that machine — other devices on your network cannot reach it. This is intentional.

```bash
trove setup
```

Then open a browser **on that same computer** and go to:

```
http://localhost:7071
```

The wizard walks you through six steps:

1. **Language** — choose the interface language
2. **Welcome** — confirms your hardware and what Trove will install
3. **Install Ollama** — downloads the AI runtime (skipped automatically if already installed)
4. **Choose a model** — pick a Gemma 4 model to download; only models your hardware can run are shown. If in doubt, pick the default. This step requires an internet connection and may take 10–30 minutes.
5. **Admin account** — set a username and password for the admin panel
6. **Install service** — registers Trove to start automatically when the computer turns on

After finishing, you will see the **management dashboard**, which shows the address to give your users.

### Step 3 — Give users a reliable address

When Trove starts, it shows an address like `http://192.168.1.42:7770`. Users on other devices open this address in any browser — no app to install.

**The address may change.** The numbers after `http://` (the IP address) can be reassigned by your router each time the server computer restarts. If the address changes, users will get a "site can't be reached" error.

> **Fixing this requires one change in your router settings.** This is sometimes called setting a "static IP" or "IP reservation". You only need to do it once.
>
> 1. Open your router's admin page. This is usually at `http://192.168.1.1` or `http://192.168.0.1` — check the label on your router if you are unsure.
> 2. Find the section called **DHCP**, **LAN**, or **IP Reservation** (the name varies by router brand).
> 3. Find the computer running Trove in the list of connected devices and assign it a fixed address.
> 4. Save and restart the router if prompted.
>
> After this, the Trove URL stays the same permanently. You can add it as a browser bookmark on staff devices or set it as the browser homepage.
>
> If you need help with this step, ask your IT support contact — it is a routine network task.

### Starting and stopping Trove

If you installed the service during setup, Trove starts automatically when the computer turns on. You can also control it manually:

```bash
systemctl --user status trove    # check if it is running
systemctl --user restart trove   # restart it
systemctl --user stop trove      # stop it
```

If you skipped the service installation, start Trove manually whenever needed:

```bash
trove start
```

Press `Ctrl + C` in the terminal to stop it.

To keep the service running even when you are not logged in (useful on a headless server):

```bash
loginctl enable-linger $USER   # one-time; requires sudo
```

### Accessing the admin panel

The admin panel — where you manage tasks, documents, and settings — is available **only from the computer running Trove**. While Trove is running, open a browser on that computer and go to:

```
http://localhost:7770/admin
```

Log in with the username and password you set during setup. You can return to the setup wizard at any time to change settings, add models, or update Ollama:

```bash
trove setup
```

Steps that are already complete are skipped automatically.

### Minimum hardware by model

| Model | Min RAM | Notes |
|---|---|---|
| Gemma 4 E2B | 4 GB | Fastest; supports audio input |
| Gemma 4 E4B | 6 GB | Better quality; supports audio input |
| Gemma 4 26B | 10 GB | High quality; no audio |
| Gemma 4 31B | 20 GB | Best quality; no audio |

### Troubleshooting

**"trove: command not found"**
Run `export PATH="$HOME/.local/bin:$PATH"` and try again. To make this permanent, add that line to `~/.bashrc`.

**The setup page won't load**
Make sure you are on the same computer where you ran `trove setup`, and that the command is still running in the terminal.

**Other devices cannot reach Trove**
Make sure `trove start` (or the service) is running. Check that the other device is on the same Wi-Fi network as the server. If the address keeps changing, set a static IP on your router (see Step 3 above).

**Model download is very slow**
The first download can take 10–30 minutes depending on your internet connection. This only happens once — after that, everything works offline.

