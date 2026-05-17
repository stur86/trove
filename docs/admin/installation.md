# Installation

This guide is for the person setting Trove up. You do not need programming experience.

## What you need

- A computer running **Linux** (Ubuntu 22.04 or later recommended)
- At least **4 GB of RAM** (8 GB or more is better)
- At least **10 GB of free disk space**
- An internet connection *during installation only* — after that, Trove runs completely offline

## Step 1 — Install Trove

Open a terminal and run:

```bash
curl -LsSf https://raw.githubusercontent.com/stur86/trove/main/install.sh | bash
```

This downloads the installer, fetches the latest Trove release, and sets everything up. It takes a few minutes.

!!! tip "Command not found afterwards?"
    If you see `trove: command not found` after the installer finishes, run the command it prints (something like `export PATH="$HOME/.local/bin:$PATH"`), then open a new terminal window.

### Using an existing Ollama installation

By default, Trove installs and manages its own copy of Ollama. If Ollama is already installed on your system and you want Trove to use it instead — sharing models, ports, and the system Ollama service — install with the `--global-ollama` flag:

```bash
curl -LsSf https://raw.githubusercontent.com/stur86/trove/main/install.sh | bash -s -- --global-ollama
```

!!! info "Why `bash -s --`?"
    When you pipe a script through bash, you cannot pass arguments directly after `bash`. The `-s` flag tells bash to read from standard input, and `--` separates bash's own options from the script's arguments. Everything after `--` is passed to the install script.

You can also pass the option as an environment variable instead of a flag:

```bash
TROVE_USE_GLOBAL_OLLAMA=1 bash <(curl -LsSf https://raw.githubusercontent.com/stur86/trove/main/install.sh)
```

When this option is active:

- The Ollama install step in the setup wizard is skipped — manage Ollama externally.
- Trove uses whichever `ollama` is on your system `PATH`.
- The automatic service installed during setup carries this setting forward, so Trove always defers to the system Ollama after a reboot.

## Step 2 — Run the setup wizard

Run the setup wizard **on the same computer you just installed Trove on**. The setup page is only reachable from that machine — this is intentional.

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
3. **Install Ollama** — downloads the AI runtime (skipped if already installed)
4. **Choose a model** — pick a Gemma 4 model; only models your hardware can run are shown. This step requires an internet connection and may take 10–30 minutes.
5. **Admin account** — set a username and password for the admin panel
6. **Install service** — registers Trove to start automatically on boot

After finishing, the dashboard shows the address to give your users.

## Step 3 — Give users a reliable address

When Trove starts it shows an address like `http://192.168.1.42:7770`. Users on other devices open this in any browser — no app to install.

**The address can change** each time the server restarts, because home and office routers reassign addresses automatically. If it changes, users will get a "site can't be reached" error.

!!! info "Fixing this with a static IP"
    Setting a fixed ("static") IP address for the server computer stops the address from changing. You only do this once, in your router's settings.

    1. Open your router's admin page — usually `http://192.168.1.1` or `http://192.168.0.1` (check the label on your router).
    2. Find the section called **DHCP**, **LAN**, or **IP Reservation**.
    3. Find the Trove server in the list of connected devices and assign it a fixed address.
    4. Save and restart the router if prompted.

    If you need help with this, ask your IT support contact — it is a routine task.

## Starting and stopping Trove

If you installed the service during setup, Trove starts automatically on boot. You can also control it manually:

```bash
systemctl --user status trove    # check if running
systemctl --user restart trove   # restart
systemctl --user stop trove      # stop
```

If you skipped the service, start Trove manually whenever needed:

```bash
trove start
```

Press `Ctrl + C` to stop it. To keep the service running even when no one is logged in (useful on a headless server):

```bash
loginctl enable-linger $USER   # one-time setup; may require sudo
```

## Model selection guide

| Model | Min RAM | Audio | Best for |
|---|---|---|---|
| Gemma 4 E2B | 4 GB | Yes | Very slow machines, fastest responses |
| Gemma 4 E4B | 6 GB | Yes | Balanced — recommended default |
| Gemma 4 26B | 10 GB | No | Better quality, similar speed to E4B |
| Gemma 4 31B | 20 GB | No | Highest quality, needs a powerful machine |

## Troubleshooting

**"trove: command not found"**
Run `export PATH="$HOME/.local/bin:$PATH"` and try again. To make it permanent, add that line to `~/.bashrc`.

**The setup page won't load**
Make sure you are on the same computer where you ran `trove setup`, and that the command is still running in the terminal.

**Other devices cannot reach Trove**
Check that `trove start` (or the service) is running. Make sure all devices are on the same Wi-Fi or wired network. If the address keeps changing, set a static IP on your router (see Step 3).

**Model download is very slow**
The first download can take 10–30 minutes depending on your internet connection. It only happens once.
