# Admin overview

The admin panel is accessible only from the machine running Trove. Open `http://localhost:7770/admin` in a browser on that machine and log in with the credentials you set during setup.

!!! warning "Admin access is localhost-only"
    The admin login is intentionally hidden from every other device on the network. This is a security measure. To manage Trove you must be physically at the server, or use an SSH tunnel.

## The four tabs

| Tab | What you can do |
|---|---|
| **Settings** | Choose the AI model, set the context window size, change the display language |
| **Documents** | Upload files, organise them into folders, view AI-generated summaries |
| **Gems** | Create, edit, and delete gems |
| **Logs** | View the last 1 000 lines of the server log, auto-refreshed every 5 seconds |

## LAN URL

The Settings tab shows the **LAN URL** — the address other devices should use to access Trove. Copy it and share it with your users.

## Next steps

- [Managing gems](gems.md)
- [Managing documents](documents.md)
- [Settings reference](settings.md)
