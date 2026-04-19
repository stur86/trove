# Settings

The **Settings** tab controls the AI model and display preferences for the whole server.

## AI model

| Setting | What it does |
|---|---|
| **Base model** | The Gemma 4 variant Trove uses. Only models you have already downloaded appear in the list. |
| **Context window (num_ctx)** | How much text the model can hold in memory at once, measured in tokens (roughly ¾ of a word each). Larger values handle longer documents but use more RAM. |

After changing the model or context window, click **Save & rebuild** to apply the change. Trove rebuilds its internal model configuration; this takes about 30 seconds and streams progress to the page.

### Choosing a model

| Model | Effective params | Min RAM | Audio | Best for |
|---|---|---|---|---|
| `gemma4:e2b` | 2.3B | ~4 GB | Yes | Very slow machines, fastest responses |
| `gemma4:e4b` | 4.5B | ~6 GB | Yes | Balanced — recommended default |
| `gemma4:26b` | 4B active (MoE) | ~10 GB | No | Better quality, similar speed to e4b |
| `gemma4:31b` | 31B dense | ~20 GB | No | Highest quality, needs a powerful machine |

!!! tip "Audio gems and model choice"
    Only `gemma4:e2b` and `gemma4:e4b` support audio input. If you switch to a model without audio support, gems that use audio input will be hidden from users until you switch back.

## Language

The **Language** selector changes the display language for the entire Trove interface, including the user-facing home screen and gem runner. Currently supported: English, Italian.

## Data

The **Data** section lets you back up the entire Trove configuration or restore a previous backup.

### Exporting a bundle

Click **Export bundle** to download a single ZIP file (`trove-bundle.zip`) containing:

- All gems and their settings.
- All document folders, document metadata, and the converted text of every document.

Use this to back up your configuration before making large changes, or to copy a setup to another Trove instance.

### Importing a bundle

Click **Import bundle** to open the import dialog. Choose a `.zip` file exported from any Trove instance, then select an import mode:

| Mode | What it does |
|---|---|
| **Add** (default) | Merges the bundle into the current data. Existing gems and documents are kept. If an incoming item has the same ID as an existing one, it is imported under a new ID (e.g. `policy-2`). |
| **Replace** | Deletes all current gems, documents, and folders, then imports everything from the bundle. |

!!! warning "Replace mode is irreversible"
    Replace mode permanently deletes all existing gems and documents before importing. Export a backup first if you want to keep the current state.

After a successful import, a summary shows how many gems and documents were imported and whether any were renamed due to ID conflicts.

## LAN URL

The LAN URL shown in the Settings tab is the address users on your network should open. Use the **Copy** button and share it — for example, put it on a notice board or send it by email.
