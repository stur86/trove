/**
 * Typed API client for the document library domain.
 *
 * Exports documentsApi — switches to the mock implementation when
 * VITE_MOCK_API=1 is set in the environment.
 */
import { del, get, patch, post } from './client'

// ── Types ────────────────────────────────────────────────────────────────────

/** A folder grouping related documents in the library. */
export interface Folder {
  id: string
  name: string
}

/** A processed document stored in the library. */
export interface Document {
  id: string
  folder_id: string
  name: string
  description: string
  mime_type: string
  created_at: string
}

/**
 * Result of an upload request.
 * status='ok'                → document is ready; `document` is set.
 * status='needs_description' → document is too long for AI summary;
 *                              `word_count` and `num_ctx` are set.
 */
export type UploadResult =
  | { status: 'ok'; document: Document }
  | { status: 'needs_description'; word_count: number; num_ctx: number }

// ── Real API implementation ───────────────────────────────────────────────────

const _realDocumentsApi = {
  /** List all folders. */
  listFolders: (): Promise<Folder[]> =>
    get<Folder[]>('/app/admin/folders'),

  /** Create a folder from a human-readable name. Returns the created Folder. */
  createFolder: (name: string): Promise<Folder> =>
    post('/app/admin/folders', { name }).then(r => r.json()),

  /** Delete a folder and all its documents. */
  deleteFolder: (id: string): Promise<void> =>
    del(`/app/admin/folders/${id}`),

  /** List documents, optionally filtered by folder_id. */
  listDocuments: (folder_id?: string): Promise<Document[]> =>
    get<Document[]>(
      folder_id
        ? `/app/admin/documents?folder_id=${encodeURIComponent(folder_id)}`
        : '/app/admin/documents'
    ),

  /**
   * Upload a file to the document library.
   * Uses multipart/form-data. An optional description bypasses AI summary.
   */
  uploadFile: async (
    file: File,
    folder_id: string,
    description: string = '',
    name: string = '',
  ): Promise<UploadResult> => {
    const form = new FormData()
    form.append('file', file)
    form.append('folder_id', folder_id)
    if (name) form.append('name', name)
    if (description) form.append('description', description)
    const res = await fetch('/api/app/admin/documents/upload', {
      method: 'POST',
      body: form,
      credentials: 'include',
    })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },

  /**
   * Fetch a URL and add it to the document library.
   * An optional description bypasses AI summary.
   */
  uploadUrl: async (
    url: string,
    folder_id: string,
    name: string,
    description: string = '',
  ): Promise<UploadResult> => {
    const res = await post('/app/admin/documents/from-url', {
      url,
      folder_id,
      name,
      description,
    })
    return res.json()
  },

  /** Rename a folder. Returns the updated Folder. */
  renameFolder: (id: string, name: string): Promise<Folder> =>
    patch<Folder>(`/app/admin/folders/${id}`, { name }),

  /**
   * Update a document's name, description, or folder (move).
   * Pass only the fields you want to change.
   */
  updateDocument: (
    id: string,
    updates: Partial<{ name: string; description: string; folder_id: string }>,
  ): Promise<Document> =>
    patch<Document>(`/app/admin/documents/${id}`, updates),

  /** Delete a document and its markdown file. */
  deleteDocument: (id: string): Promise<void> =>
    del(`/app/admin/documents/${id}`),
}

// ── Mock selector ─────────────────────────────────────────────────────────────

import { documentsApi as _mockDocumentsApi } from './mock/documents'
export const documentsApi =
  import.meta.env.VITE_MOCK_API ? _mockDocumentsApi : _realDocumentsApi
