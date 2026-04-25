/**
 * GemForm — full-page create/edit form for a UserTask (gem).
 *
 * Routes:
 *   /admin/gems/new          — create mode: blank form, calls gemsApi.create()
 *   /admin/gems/:id/edit     — edit mode: loads existing gem, calls gemsApi.update()
 *
 * Admin credentials are passed via React Router location.state as
 * { username, password } (set by AdminPanel when navigating here).
 * If state is missing, shows a lightweight re-auth form.
 *
 * Arguments are derived automatically from `{{ variable_name }}` placeholders in
 * the template. All derived args are free-text StringArgs — no manual editing.
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import CheckboxTree from 'react-checkbox-tree'
import 'react-checkbox-tree/lib/react-checkbox-tree.css'
import {
  Alert, Button, Checkbox, Label, Spinner, Textarea, TextInput,
} from 'flowbite-react'
import {
  gemsApi, GEM_HUES, TOOL_IDS, type TaskArg, type ToolId, type UserTask,
} from '../api/tasks'
import { documentsApi, type Folder, type Document } from '../api/documents'
import { appApi } from '../api/app'
import AdminLogin from '../components/AdminLogin'
import GemIcon from '../components/GemIcon'
import HelpBar from '../components/HelpBar'
import { useLocale, useTranslation } from '../i18n'

/** Blank UserTask used as a starting point for the create form. */
function blankGem(): UserTask {
  return {
    id: '',
    name: '',
    description: '',
    hue: 'indigo',
    template: '',
    args: [],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
    doc_folder_ids: [],
    doc_ids: [],
    tools: [],
  }
}

/**
 * Extract unique variable names from a Jinja2-style template string.
 * Matches `{{ variable_name }}` placeholders (whitespace-tolerant, word chars only).
 * Preserves first-occurrence order and deduplicates.
 */
function extractTemplateVars(template: string): string[] {
  const seen = new Set<string>()
  const vars: string[] = []
  for (const match of template.matchAll(/{{\s*(\w+)\s*}}/g)) {
    if (!seen.has(match[1])) { seen.add(match[1]); vars.push(match[1]) }
  }
  return vars
}

/**
 * Convert a gem name to a URL-safe slug id.
 * Lowercases, replaces whitespace runs with hyphens, strips non-alphanumeric chars.
 */
function nameToSlug(name: string): string {
  return name.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
}

/**
 * Rebuild the args list from the template, keeping free-text StringArgs.
 * Order follows first appearance in the template.
 */
function deriveArgs(template: string): TaskArg[] {
  return extractTemplateVars(template).map(name => ({
    type: 'string' as const,
    name,
    description: '',
    default: '',
  }))
}

export default function GemForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const { t } = useTranslation(useLocale())

  // Admin cookie state — check whether admin cookie is present
  const [authReady, setAuthReady] = useState(false)

  const [gem, setGem] = useState<UserTask>(blankGem())
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Document access
  const [allFolders, setAllFolders] = useState<Folder[]>([])
  const [allDocuments, setAllDocuments] = useState<Document[]>([])
  const [expanded, setExpanded] = useState<string[]>([])
  // const [capabilities, setCapabilities] = useState<{ audio: boolean }>({ audio: false })

  // In edit mode, load the existing gem
  useEffect(() => {
    if (!isEdit || !id) return
    gemsApi.get(id)
      .then(g => {
        setGem(g)
        setLoading(false)
      })
      .catch(() => { setError(t('admin.gem.error.not_found')); setLoading(false) })
  }, [id, isEdit])

  // Load all folders and documents for the access tree
  useEffect(() => {
    documentsApi.listFolders().then(setAllFolders)
    documentsApi.listDocuments().then(setAllDocuments)
  }, [])

  // Expand all folders by default when folder list loads
  useEffect(() => {
    setExpanded(allFolders.map(f => `folder:${f.id}`))
  }, [allFolders])

  useEffect(() => {
    appApi.checkAdminValid()
      .then(res => { if (res.valid) setAuthReady(true) })
      .catch(() => {})
  }, [])

  // This is part of the audio support work that is currently disabled, 
  // but leaving it here for when we re-enable it. It checks whether the backend supports audio input and updates the UI accordingly.
  // useEffect(() => {
  //   appApi.capabilities()
  //     .then(caps => setCapabilities(caps))
  //     .catch(() => {})  // safe default: treat audio as unsupported if fetch fails
  // }, [])

  async function handleSave() {
    setError(null)
    setSaving(true)
    // Args are always freshly derived from the template at save time
    const cleanGem: UserTask = {
      ...gem,
      args: deriveArgs(gem.template),
      // doc_folder_ids and doc_ids are kept current in gem state by handleCheckedChange
    }
    try {
      if (isEdit && id) {
        await gemsApi.update(id, cleanGem)
      } else {
        await gemsApi.create(cleanGem)
      }
      navigate('/admin', { state: { tab: 'gems' } })
    } catch {
      setError(t('admin.gem.error.save_failed'))
    } finally {
      setSaving(false)
    }
  }

  /**
   * Derive node values from gem state for the tree's controlled checked prop.
   * Folder values use 'folder:<id>' prefix; doc values use 'doc:<id>' prefix.
   */
  const checkedValues: string[] = [
    ...gem.doc_folder_ids.map(id => `folder:${id}`),
    ...gem.doc_ids.map(id => `doc:${id}`),
  ]

  /**
   * Handle checkbox changes from react-checkbox-tree.
   * Maps prefixed values back to doc_folder_ids and doc_ids in gem state.
   * When a folder is checked, its children are covered by the folder grant
   * and should not also appear as individual doc_ids.
   */
  function handleCheckedChange(newChecked: string[], _targetNode: unknown) {
    const newFolderIds = newChecked
      .filter(v => v.startsWith('folder:'))
      .map(v => v.slice(7))
    const checkedFolderSet = new Set(newFolderIds)
    const newDocIds = newChecked
      .filter(v => v.startsWith('doc:'))
      .map(v => v.slice(4))
      .filter(docId => {
        const doc = allDocuments.find(d => d.id === docId)
        return doc ? !checkedFolderSet.has(doc.folder_id) : true
      })
    setGem(g => ({ ...g, doc_folder_ids: newFolderIds, doc_ids: newDocIds }))
  }

  /** Build the node tree for react-checkbox-tree. */
  const treeNodes = allFolders.map(folder => ({
    value: `folder:${folder.id}`,
    label: folder.name,
    children: allDocuments
      .filter(d => d.folder_id === folder.id)
      .map(doc => ({
        value: `doc:${doc.id}`,
        label: doc.name,
        title: doc.description || undefined,
      })),
  }))

  /** Minimal inline SVG icons — avoids pulling in Font Awesome. */
  const TREE_ICONS = {
    check: (
      <svg className="w-4 h-4 text-blue-600 inline" viewBox="0 0 20 20" fill="currentColor">
        <rect x="2" y="2" width="16" height="16" rx="3" fill="currentColor" opacity="0.15" />
        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
      </svg>
    ),
    uncheck: (
      <svg className="w-4 h-4 text-gray-300 inline" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="2.75" y="2.75" width="14.5" height="14.5" rx="2.25" />
      </svg>
    ),
    halfCheck: (
      <svg className="w-4 h-4 text-blue-400 inline" viewBox="0 0 20 20" fill="currentColor">
        <rect x="2" y="2" width="16" height="16" rx="3" fill="currentColor" opacity="0.15" />
        <path d="M5 10h10" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
    expandClose: <span className="text-gray-400 text-xs select-none">›</span>,
    expandOpen: <span className="text-gray-400 text-xs select-none">⌄</span>,
    expandAll: <span />,
    collapseAll: <span />,
    parentClose: <span />,
    parentOpen: <span />,
    leaf: <span />,
  }

  // Re-auth screen if admin cookie is not present
  if (!authReady) {
    return (
      <AdminLogin
        onSubmit={async (u, p) => {
          try {
            await appApi.login(u, p)
            setAuthReady(true)
          } catch {
            setError(t('admin.gem.error.login_failed'))
          }
        }}
        loginError={false}
        title="Admin login required"
      />
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto flex flex-col gap-6">

        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/admin')}
            className="text-gray-400 hover:text-gray-600 text-sm"
          >
            {t('admin.gem.back')}
          </button>
          <h1 className="text-xl font-bold text-gray-900">
            {isEdit ? t('admin.gem.title.edit') : t('admin.gem.title.new')}
          </h1>
        </div>

        {error && <Alert color="failure">{error}</Alert>}

        <HelpBar
          prompt={t('help.gem.intro.prompt')}
          title={t('help.gem.intro.title')}
          content={t('help.gem.intro.content')}
        />

        {/* Name — in create mode, also derives the id slug automatically */}
        <div>
          <div className="mb-1"><Label htmlFor="gem-name">Name</Label></div>
          <TextInput
            id="gem-name"
            value={gem.name}
            onChange={e => {
              const name = e.target.value
              setGem(g => ({
                ...g,
                name,
                // Only auto-derive the id in create mode; in edit mode the id is fixed
                ...(isEdit ? {} : { id: nameToSlug(name) }),
              }))
            }}
            placeholder="e.g. Summarise Text"
          />
          {/* Show the derived slug in create mode so admins know what id will be used */}
          {!isEdit && gem.id && (
            <p className="mt-1 text-xs text-gray-400">ID: <span className="font-mono">{gem.id}</span></p>
          )}
        </div>

        {/* Description */}
        <div>
          <div className="mb-1"><Label htmlFor="gem-description">Description</Label></div>
          <TextInput
            id="gem-description"
            value={gem.description}
            onChange={e => setGem(g => ({ ...g, description: e.target.value }))}
            placeholder="Short description shown on the gem card"
          />
        </div>

        {/* Hue picker */}
        <div>
          <div className="mb-2"><Label>Hue</Label></div>
          <div className="flex flex-wrap gap-2">
            {GEM_HUES.map(hue => (
              <button
                key={hue}
                onClick={() => setGem(g => ({ ...g, hue }))}
                title={hue}
                className={`rounded p-1 border-2 transition-colors ${
                  gem.hue === hue
                    ? 'border-gray-800'
                    : 'border-transparent hover:border-gray-300'
                }`}
              >
                <GemIcon hue={hue} size={28} />
              </button>
            ))}
          </div>
        </div>

        {/* Template */}
        <div>
          <div className="mb-1">
            <Label htmlFor="gem-template">Prompt template</Label>
          </div>
          <Textarea
            id="gem-template"
            value={gem.template}
            onChange={e => setGem(g => ({ ...g, template: e.target.value }))}
            placeholder="e.g. Summarise the following in {{ language }}: {{ text }}"
            rows={6}
            className="font-mono text-sm"
          />
          <div className="mt-2">
            <HelpBar
              prompt={t('help.gem.template.prompt')}
              title={t('help.gem.template.title')}
              content={t('help.gem.template.content')}
            />
          </div>
        </div>

        {/* Detected variables — read-only, derived from template */}
        {extractTemplateVars(gem.template).length > 0 && (
          <div>
            <div className="mb-2"><Label>Detected inputs</Label></div>
            <div className="flex flex-wrap gap-2">
              {extractTemplateVars(gem.template).map(v => (
                <span
                  key={v}
                  className="inline-block bg-gray-100 text-gray-700 text-xs font-mono px-2 py-1 rounded"
                >
                  {v}
                </span>
              ))}
            </div>
            <p className="mt-1 text-xs text-gray-400">
              Each placeholder becomes a free-text field for the user.
            </p>
          </div>
        )}

        {/* Capability flags */}
        <div className="flex flex-col gap-2">
          <Label>Capabilities</Label>
          <div className="flex items-center gap-2">
            <Checkbox
              id="has-image"
              checked={gem.has_image}
              onChange={e => setGem(g => ({ ...g, has_image: e.target.checked }))}
            />
            <Label htmlFor="has-image">Accepts image input</Label>
          </div>
          <div className="flex items-start gap-2">
          { /*
            Audio input is currently unsupported, so this checkbox is disabled and hidden behind a feature flag.
            <Checkbox
              id="has-audio"
              checked={gem.has_audio}
              disabled={!capabilities.audio}
              onChange={e => setGem(g => ({ ...g, has_audio: e.target.checked }))}
              className={!capabilities.audio ? 'opacity-50' : ''}
            />
            <div>
              <Label
                htmlFor="has-audio"
                className={!capabilities.audio ? 'text-gray-400' : ''}
              >
                Accepts audio input
              </Label>
              {!capabilities.audio && (
                <p className="text-xs text-gray-400 mt-0.5">
                  {t('admin.gem.audio_not_supported')}
                </p>
              )}
            </div>
            */}
          </div>
        </div>

        {/* Tools */}
        <div className="flex flex-col gap-2">
          <Label>{t('gem.tools.section_title')}</Label>
          <HelpBar
            prompt={t('help.gem.tools.prompt')}
            title={t('help.gem.tools.title')}
            content={t('help.gem.tools.content')}
          />
          <p className="text-xs text-gray-500">{t('gem.tools.section_hint')}</p>
          <div className="flex flex-col gap-2">
            {TOOL_IDS.map(({ id, labelKey, descKey }: { id: ToolId; labelKey: string; descKey: string }) => (
              <div key={id} className="flex items-start gap-2">
                <Checkbox
                  id={`tool-${id}`}
                  checked={gem.tools.includes(id)}
                  onChange={e => setGem(g => ({
                    ...g,
                    tools: e.target.checked
                      ? [...g.tools, id]
                      : g.tools.filter(tid => tid !== id),
                  }))}
                />
                <div>
                  <Label htmlFor={`tool-${id}`}>{t(labelKey)}</Label>
                  <p className="text-xs text-gray-400 mt-0.5">{t(descKey)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Document access */}
        <div className="flex flex-col gap-2">
          <Label>{t('gem.documents.section_title')}</Label>
          <HelpBar
            prompt={t('help.gem.documents.prompt')}
            title={t('help.gem.documents.title')}
            content={t('help.gem.documents.content')}
          />
          <p className="text-xs text-gray-500">{t('gem.documents.section_hint')}</p>
          {allFolders.length === 0 ? (
            <p className="text-xs text-gray-400 italic">{t('gem.documents.no_folders')}</p>
          ) : (
            <div className="border border-gray-200 rounded-lg p-3">
              <CheckboxTree
                nodes={treeNodes}
                checked={checkedValues}
                expanded={expanded}
                onCheck={handleCheckedChange}
                onExpand={setExpanded}
                icons={TREE_ICONS}
              />
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3 pb-8">
          <Button color="blue" disabled={saving} onClick={handleSave}>
            {saving ? <Spinner size="sm" /> : (isEdit ? t('admin.gem.save') : t('admin.gem.create'))}
          </Button>
          <Button color="light" onClick={() => navigate('/admin')}>
            {t('admin.gem.cancel')}
          </Button>
        </div>

      </div>
    </div>
  )
}
