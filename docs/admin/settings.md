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

## LAN URL

The LAN URL shown in the Settings tab is the address users on your network should open. Use the **Copy** button and share it — for example, put it on a notice board or send it by email.
