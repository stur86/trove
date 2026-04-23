# HelpBar Component — Design Spec

**Date:** 2026-04-23
**Status:** Approved

---

## Overview

A reusable `HelpBar` component that renders a full-width clickable strip inside admin pages. When clicked it opens a Flowbite modal whose body is sourced from the locale file system (file-based i18n values). Intended for non-technical admins who need contextual guidance without leaving the page.

---

## Component

**File:** `frontend/src/components/HelpBar.tsx`

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `prompt` | `string` | required | Clickable label text (pre-resolved via `t()`) |
| `title` | `string` | required | Modal header title (pre-resolved via `t()`) |
| `content` | `string` | required | Modal body content (pre-resolved via `t()`, may be Markdown) |
| `markdown` | `boolean` | `true` | Render `content` with ReactMarkdown |

Callers resolve all strings via the existing `useTranslation` hook before passing them. `HelpBar` has no i18n coupling.

### Visual design

- Full-width rounded strip: `bg-blue-50 border border-blue-200 rounded-lg`
- Layout: `HiInformationCircle` icon (left) · prompt text (flex-1, `text-blue-700 font-medium text-sm`) · "Read more →" (right, muted)
- Hover: `hover:bg-blue-100`
- Icon: `HiInformationCircle` from `react-icons/hi` — **requires adding `react-icons` to frontend deps**
- Modal: Flowbite `Modal` (size `lg`), `ModalHeader` shows `title`, `ModalBody` shows `content` via `ReactMarkdown` when `markdown={true}`, plain `<p>` otherwise

---

## Locale structure

Each placement requires three keys in the locale JSON. Content keys use the file-based path mechanism introduced previously.

```json
"help.model.prompt":   "How do I choose a model?",
"help.model.title":    "Choosing an AI model",
"help.model.content":  { "path": "help-model.md" }
```

Markdown files live in `locales/en/`. Italian stubs (`locales/it/`) copy the English content initially; proper translations are a future i18n task.

---

## Placements — 6 bars

### AdminPanel — Settings tab

| Key prefix | Prompt | Placement |
|---|---|---|
| `help.model` | "How do I choose a model?" | Below the model `<Select>` |
| `help.ctx` | "What is the context window?" | Below the `RangeSlider` |
| `help.bundle` | "What are bundles?" | Below the "Data" section heading |

### GemForm

| Key prefix | Prompt | Placement |
|---|---|---|
| `help.gem.intro` | "What's a Gem?" | Top of the form, below the page header |
| `help.gem.template` | "How do I write a good prompt?" | Below the template `<Textarea>` — **replaces** the existing `InfoButton` on the template label |
| `help.gem.documents` | "How does document access work?" | Above the document checkbox tree |

---

## Content files (English)

Six Markdown files, all in `locales/en/`:

| File | Covers |
|---|---|
| `help-model.md` | Model variants (E2B/E4B/26B/31B), RAM requirements, when to pick each |
| `help-ctx.md` | What context window means, memory tradeoff, when to raise/lower it |
| `help-bundle.md` | What a bundle contains (gems + documents), export for backup, import to migrate |
| `help-gem-intro.md` | What a Gem is (task = template + inputs + output), no free chat |
| `help-gem-template.md` | Jinja `{{ variable }}` syntax, tips for a clear prompt — migrates the existing `InfoButton` tooltip content into a proper help file |
| `help-gem-documents.md` | Three-tier access (always-visible / on-request / no-access), how the model uses them |

Italian stubs in `locales/it/` are identical to English files at first.

---

## Changes summary

| File | Change |
|---|---|
| `frontend/package.json` | Add `react-icons` |
| `frontend/src/components/HelpBar.tsx` | New component |
| `locales/en.json` | +18 keys (3 per bar) |
| `locales/it.json` | +18 keys (3 per bar, same strings as en for now) |
| `locales/en/*.md` | 6 new content files |
| `locales/it/*.md` | 6 stub content files (copy of en) |
| `frontend/src/pages/AdminPanel.tsx` | 3 `<HelpBar>` insertions in Settings tab |
| `frontend/src/pages/GemForm.tsx` | 3 `<HelpBar>` insertions; remove `InfoButton` from template label |

---

## Out of scope

- Translating Italian content (stub files only for now)
- HelpBar in non-admin pages (GemRunner, SetupWizard)
- Animated transitions on the modal
