## The context window

The context window controls how much text the model can read and write in a single task. It is measured in **tokens** — roughly three-quarters of a word each.

**Guidelines:**

- **4,096–8,192** — good for short prompts and brief responses. Fastest and uses the least memory.
- **16,384–32,768** — suitable when tasks involve long documents or detailed outputs.
- **Higher values** — use significantly more memory. On low-RAM machines this can slow the server or cause it to become unresponsive.

A good rule of thumb: set it to the smallest value that handles your longest expected task comfortably. If a response seems cut off mid-sentence, increase this value and click **Save settings** to rebuild.
