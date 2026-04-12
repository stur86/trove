# Managing gems

A **Gem** is a reusable AI task with a fixed purpose. Users see gems as cards on the home screen and fill in a short form to run them.

## Creating a gem

1. Open the **Gems** tab in the admin panel.
2. Click **New gem**.
3. Fill in the form:

| Field | What it does |
|---|---|
| **Name** | Shown on the gem card. Keep it short and descriptive. |
| **Description** | Optional. A one-line hint shown below the name. |
| **Hue** | The colour of the gem icon. Use different colours to make gems easy to tell apart at a glance. |
| **Prompt template** | The AI instruction. Use `{{ variable_name }}` placeholders for fields the user fills in. |
| **Capabilities** | Tick *Accepts image input* if the task needs a photo or screenshot. |
| **Output mode** | *Text* for plain output; *Structured (JSON)* for machine-readable output. |
| **Document access** | Which document folders or individual files the AI can read when running this gem. |

4. Click **Create**.

## Writing a good prompt template

The template is the instruction the AI receives. It can include any text, plus placeholders:

```
Summarise the following text in {{ language }}, using no more than 5 bullet points:

{{ text }}
```

This creates two input fields for the user: *language* and *text*.

**Tips:**

- Be specific. Tell the AI exactly what format you want.
- State the language of expected output if it matters.
- Keep instructions short — the model works best with clear, concise prompts.
- Test the gem yourself before sharing it with users.

## Document access

Each gem can be given access to part of the document library:

- **Folder access** — the AI can see every document in the folder, including new ones added later.
- **Individual document access** — the AI can only see the specific files you select.
- **No access** (default) — the AI does not use the document library for this gem.

When a gem has document access, the AI decides for itself whether to look up documents or answer from its own knowledge.

## Editing and deleting

Click **Edit** next to any gem to change its settings. Click **Delete** to remove it permanently. There is no undo.

!!! warning "Deleting a gem"
    Deleted gems cannot be recovered. Users who try to open a deleted gem's URL will see an error.
