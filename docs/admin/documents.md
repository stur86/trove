# Managing documents

The document library lets you give the AI access to your institution's files — policies, handbooks, reference sheets — without embedding them in individual gem prompts.

## Uploading a document

1. Open the **Documents** tab in the admin panel.
2. Select a destination folder (or create a new one).
3. Click **Upload** and choose a file.

Supported formats include PDF, Word (`.docx`), plain text, and most common office formats. Trove converts uploaded files to plain text internally using [Markitdown](https://github.com/microsoft/markitdown). The original file is kept alongside the converted version.

After upload, the AI automatically generates a one-line description of the document. This description is shown in the admin panel and used when the AI decides which documents to look up.

## Folders

Documents are organised into folders. Folders are the unit of access control: when you create a gem, you grant access to entire folders or to individual documents within them.

To create a folder, type a name in the **New folder** field and press Enter (or the add button).

To rename a folder or document, click its name in the admin panel.

## How the AI uses documents

When a gem has document access, Trove gives the AI a summary of all accessible documents before it starts. The AI can then request the full text of any document it judges relevant. There is no vector search — the AI reasons from the summaries and fetches full content on demand.

This means:
- **Short, well-named documents with good descriptions** are easier for the AI to find and use.
- **Very large documents** may be truncated to fit within the model's context window.
- The AI will not always use documents — it uses them only when they seem relevant to the user's request.

## Removing a document

Click the **Delete** button next to a document in the admin panel. The file and its metadata are permanently deleted.
