/**
 * Mock implementation of the document library API.
 * Used when VITE_MOCK_API=1. Returns sample data after a short delay.
 */
import type { Document, Folder, UploadResult } from '../documents'

const delay = (ms = 300) => new Promise(r => setTimeout(r, ms))

const FOLDERS: Folder[] = [
  { id: 'hr-policies', name: 'HR Policies' },
  { id: 'general-reference', name: 'General Reference' },
]

const DOCUMENTS: Document[] = [
  {
    id: 'leave-policy-2024',
    folder_id: 'hr-policies',
    name: 'leave-policy-2024.pdf',
    description: 'Sets out employee leave entitlements and procedures.',
    mime_type: 'application/pdf',
    created_at: '2024-09-01T09:00:00Z',
  },
  {
    id: 'health-safety-guide',
    folder_id: 'hr-policies',
    name: 'health-safety-guide.docx',
    description: 'Covers on-site safety rules and emergency contacts.',
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    created_at: '2024-10-15T14:30:00Z',
  },
  {
    id: 'staff-handbook',
    folder_id: 'general-reference',
    name: 'staff-handbook.pdf',
    description: 'Complete onboarding guide for new staff members.',
    mime_type: 'application/pdf',
    created_at: '2024-07-20T10:00:00Z',
  },
  {
    id: 'it-acceptable-use',
    folder_id: 'general-reference',
    name: 'it-acceptable-use.txt',
    description: 'Acceptable use policy for IT equipment and internet access.',
    mime_type: 'text/plain',
    created_at: '2024-11-05T08:45:00Z',
  },
]

// In-memory mutable copies so create/delete work during a session
let folders = [...FOLDERS]
let documents = [...DOCUMENTS]

export const documentsApi = {
  listFolders: async (): Promise<Folder[]> => {
    await delay()
    return [...folders]
  },

  createFolder: async (name: string): Promise<Folder> => {
    await delay(500)
    const id = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
    const folder: Folder = { id, name }
    folders.push(folder)
    return folder
  },

  deleteFolder: async (id: string): Promise<void> => {
    await delay()
    folders = folders.filter(f => f.id !== id)
    documents = documents.filter(d => d.folder_id !== id)
  },

  listDocuments: async (folder_id?: string): Promise<Document[]> => {
    await delay()
    return folder_id ? documents.filter(d => d.folder_id === folder_id) : [...documents]
  },

  uploadFile: async (
    file: File,
    folder_id: string,
    description: string = '',
    name: string = '',
  ): Promise<UploadResult> => {
    await delay(800) // Simulate markitdown + AI summary
    const displayName = name || file.name
    const id = displayName
      .replace(/\.[^.]+$/, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
    const doc: Document = {
      id,
      folder_id,
      name: displayName,
      description: description || `Mock summary for ${displayName}.`,
      mime_type: file.type,
      created_at: new Date().toISOString(),
    }
    documents.push(doc)
    return { status: 'ok', document: doc }
  },

  uploadUrl: async (
    _url: string,
    folder_id: string,
    name: string,
    description: string = '',
  ): Promise<UploadResult> => {
    await delay(800)
    const id = name.toLowerCase().replace(/[^a-z0-9]+/g, '-')
    const doc: Document = {
      id,
      folder_id,
      name,
      description: description || `Mock summary for ${name}.`,
      mime_type: 'text/html',
      created_at: new Date().toISOString(),
    }
    documents.push(doc)
    return { status: 'ok', document: doc }
  },

  renameFolder: async (id: string, name: string): Promise<Folder> => {
    await delay()
    const folder = folders.find(f => f.id === id)
    if (!folder) throw new Error(`Folder ${id} not found`)
    const updated = { ...folder, name }
    folders = folders.map(f => f.id === id ? updated : f)
    return updated
  },

  updateDocument: async (
    id: string,
    updates: Partial<{ name: string; description: string; folder_id: string }>,
  ): Promise<Document> => {
    await delay()
    const doc = documents.find(d => d.id === id)
    if (!doc) throw new Error(`Document ${id} not found`)
    const updated = { ...doc, ...updates }
    documents = documents.map(d => d.id === id ? updated : d)
    return updated
  },

  deleteDocument: async (id: string): Promise<void> => {
    await delay()
    documents = documents.filter(d => d.id !== id)
  },
}
