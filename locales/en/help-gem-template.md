## Writing a good prompt template

The template is the instruction you give the AI. Use `{{ variable_name }}` anywhere in the text to create a field that the user fills in before running the Gem.

**Example:**

```
Summarise the following text in {{ language }}, using no more than {{ max_points }} bullet points:

{{ text }}
```

This creates three input fields: *language*, *max_points*, and *text*.

**Tips for a great prompt:**

- **Be specific** — tell the model exactly what you want it to produce.
- **State the format** — bullet list, short paragraph, numbered steps, table…
- **Give an example** — if the task is tricky, show what a good answer looks like.
- **Keep it short** — the model works best with clear, concise instructions.
- **Name variables clearly** — `{{ patient_name }}` is better than `{{ name }}`.
