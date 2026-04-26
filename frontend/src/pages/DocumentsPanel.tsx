/**
 * DocumentsPanel — admin UI for the document library.
 *
 * Three-column layout: folders (left, 192px), document list (centre, flex-1),
 * properties card (right, 288px). Folder rename is inline (click pencil icon).
 * Documents show name only; clicking selects the document and populates the
 * properties card. Name and description auto-save on blur. Folder selector shows
 * a Move button when the selection changes; Move switches the active folder and
 * keeps the document selected. Upload File and Add from URL open separate modals.
 */
import { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Button,
  FileInput,
  Label,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  Select,
  Spinner,
  Textarea,
  TextInput,
} from 'flowbite-react'
import { documentsApi, type Document, type Folder } from '../api/documents'
import { useTranslation } from '../i18n'

export default function DocumentsPanel() {
  const { t } = useTranslation()

  // ── Folder panel ──────────────────────────────────────────────────────────
  const [folders, setFolders] = useState<Folder[]>([])
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null)
  const [loadingFolders, setLoadingFolders] = useState(true)
  const [newFolderName, setNewFolderName] = useState('')
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [renamingFolderId, setRenamingFolderId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [folderToDelete, setFolderToDelete] = useState<Folder | null>(null)
  const [folderError, setFolderError] = useState<string | null>(null)

  // ── Document list ─────────────────────────────────────────────────────────
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [pendingSelectDocId, setPendingSelectDocId] = useState<string | null>(null)
  const [docError, setDocError] = useState<string | null>(null)

  // ── Properties card ───────────────────────────────────────────────────────
  const [propName, setPropName] = useState('')
  const [propDescription, setPropDescription] = useState('')
  const [propFolderId, setPropFolderId] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [propSaving, setPropSaving] = useState(false)
  // Move button shows when folder selector differs from the document's current folder
  const movePending = selectedDoc !== null && propFolderId !== selectedDoc.folder_id

  // ── Upload file modal ─────────────────────────────────────────────────────
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadName, setUploadName] = useState('')
  const [uploadDescription, setUploadDescription] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadNeedsDesc, setUploadNeedsDesc] = useState<{
    wordCount: number
    numCtx: number
  } | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Add from URL modal ────────────────────────────────────────────────────
  const [urlModalOpen, setUrlModalOpen] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const [urlName, setUrlName] = useState('')
  const [urlDescription, setUrlDescription] = useState('')
  const [urlUploading, setUrlUploading] = useState(false)
  const [urlNeedsDesc, setUrlNeedsDesc] = useState<{
    wordCount: number
    numCtx: number
  } | null>(null)
  const [urlError, setUrlError] = useState<string | null>(null)

  // ── Load folders on mount ─────────────────────────────────────────────────
  useEffect(() => {
    documentsApi.listFolders().then(setFolders).finally(() => setLoadingFolders(false))
  }, [])

  // ── Load documents when selected folder changes ───────────────────────────
  useEffect(() => {
    if (!selectedFolder) {
      setDocuments([])
      setSelectedDoc(null)
      return
    }
    setLoadingDocs(true)
    documentsApi
      .listDocuments(selectedFolder.id)
      .then(docs => {
        setDocuments(docs)
        // After a move, auto-select the moved document in the new folder
        if (pendingSelectDocId) {
          const doc = docs.find(d => d.id === pendingSelectDocId)
          if (doc) setSelectedDoc(doc)
          setPendingSelectDocId(null)
        }
      })
      .finally(() => setLoadingDocs(false))
  }, [selectedFolder]) // pendingSelectDocId intentionally omitted — read synchronously

  // ── Sync properties card fields when a different document is selected ─────
  useEffect(() => {
    if (!selectedDoc) return
    setPropName(selectedDoc.name)
    setPropDescription(selectedDoc.description)
    setPropFolderId(selectedDoc.folder_id)
    setDeleteConfirm(false)
    setDocError(null)
  }, [selectedDoc])

  // ── Folder handlers ───────────────────────────────────────────────────────

  async function handleCreateFolder() {
    if (!newFolderName.trim()) return
    setCreatingFolder(true)
    setFolderError(null)
    try {
      const folder = await documentsApi.createFolder(newFolderName.trim())
      setFolders(prev => [...prev, folder].sort((a, b) => a.name.localeCompare(b.name)))
      setNewFolderName('')
    } catch (e) {
      setFolderError(String(e))
    } finally {
      setCreatingFolder(false)
    }
  }

  function startRename(folder: Folder) {
    setRenamingFolderId(folder.id)
    setRenameValue(folder.name)
  }

  async function commitRename(folderId: string) {
    const trimmed = renameValue.trim()
    setRenamingFolderId(null)
    if (!trimmed) return
    try {
      const updated = await documentsApi.renameFolder(folderId, trimmed)
      setFolders(prev =>
        prev.map(f => f.id === folderId ? updated : f).sort((a, b) => a.name.localeCompare(b.name))
      )
      if (selectedFolder?.id === folderId) setSelectedFolder(updated)
    } catch (e) {
      setFolderError(String(e))
    }
  }

  async function handleDeleteFolder(folder: Folder) {
    setFolderToDelete(null)
    setFolderError(null)
    try {
      await documentsApi.deleteFolder(folder.id)
      setFolders(prev => prev.filter(f => f.id !== folder.id))
      if (selectedFolder?.id === folder.id) setSelectedFolder(null)
    } catch (e) {
      setFolderError(String(e))
    }
  }

  // ── Download handlers ─────────────────────────────────────────────────────

  async function handleDownloadFolder(folder: Folder) {
    try {
      await documentsApi.downloadFolder(folder.id)
    } catch (e) {
      setFolderError(String(e))
    }
  }

  async function handleDownloadDocument(doc: Document) {
    try {
      await documentsApi.downloadDocument(doc.id)
    } catch (e) {
      setDocError(String(e))
    }
  }

  // ── Properties card handlers ──────────────────────────────────────────────

  async function handlePropNameBlur() {
    if (!selectedDoc || propName.trim() === selectedDoc.name) return
    setPropSaving(true)
    try {
      const updated = await documentsApi.updateDocument(selectedDoc.id, { name: propName.trim() })
      setDocuments(prev => prev.map(d => d.id === updated.id ? updated : d))
      setSelectedDoc(updated)
    } catch (e) {
      setPropName(selectedDoc.name)
      setDocError(String(e))
    } finally {
      setPropSaving(false)
    }
  }

  async function handlePropDescriptionBlur() {
    if (!selectedDoc || propDescription === selectedDoc.description) return
    setPropSaving(true)
    try {
      const updated = await documentsApi.updateDocument(selectedDoc.id, {
        description: propDescription,
      })
      setDocuments(prev => prev.map(d => d.id === updated.id ? updated : d))
      setSelectedDoc(updated)
    } catch (e) {
      setPropDescription(selectedDoc.description)
      setDocError(String(e))
    } finally {
      setPropSaving(false)
    }
  }

  async function handleMove() {
    if (!selectedDoc || !movePending) return
    setDocError(null)
    try {
      const updated = await documentsApi.updateDocument(selectedDoc.id, {
        folder_id: propFolderId,
      })
      const destFolder = folders.find(f => f.id === propFolderId)
      if (destFolder) {
        setPendingSelectDocId(updated.id)
        setSelectedFolder(destFolder)
      }
    } catch (e) {
      setPropFolderId(selectedDoc.folder_id)
      setDocError(String(e))
    }
  }

  async function handleDeleteDocument() {
    if (!selectedDoc) return
    if (!deleteConfirm) {
      setDeleteConfirm(true)
      return
    }
    try {
      await documentsApi.deleteDocument(selectedDoc.id)
      setDocuments(prev => prev.filter(d => d.id !== selectedDoc.id))
      setSelectedDoc(null)
    } catch (e) {
      setDocError(String(e))
    }
  }

  // ── Upload file modal handlers ────────────────────────────────────────────

  function closeUploadModal() {
    setUploadModalOpen(false)
    setUploadFile(null)
    setUploadName('')
    setUploadDescription('')
    setUploading(false)
    setUploadNeedsDesc(null)
    setUploadError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function handleUpload() {
    if (!uploadFile || !selectedFolder) return
    setUploading(true)
    setUploadError(null)
    const name = uploadName.trim() || uploadFile.name
    try {
      const result = await documentsApi.uploadFile(
        uploadFile,
        selectedFolder.id,
        uploadDescription.trim(),
        name,
      )
      if (result.status === 'ok') {
        setDocuments(prev =>
          [...prev, result.document].sort((a, b) => a.name.localeCompare(b.name))
        )
        closeUploadModal()
      } else {
        setUploadNeedsDesc({ wordCount: result.word_count, numCtx: result.num_ctx })
      }
    } catch (e) {
      setUploadError(String(e))
    } finally {
      setUploading(false)
    }
  }

  // ── Add from URL modal handlers ───────────────────────────────────────────

  function closeUrlModal() {
    setUrlModalOpen(false)
    setUrlInput('')
    setUrlName('')
    setUrlDescription('')
    setUrlUploading(false)
    setUrlNeedsDesc(null)
    setUrlError(null)
  }

  async function handleUrlUpload() {
    if (!urlInput.trim() || !selectedFolder) return
    setUrlUploading(true)
    setUrlError(null)
    const url = urlInput.trim()
    const name = urlName.trim() || url.split('/').filter(Boolean).pop() || url
    try {
      const result = await documentsApi.uploadUrl(
        url,
        selectedFolder.id,
        name,
        urlDescription.trim(),
      )
      if (result.status === 'ok') {
        setDocuments(prev =>
          [...prev, result.document].sort((a, b) => a.name.localeCompare(b.name))
        )
        closeUrlModal()
      } else {
        setUrlNeedsDesc({ wordCount: result.word_count, numCtx: result.num_ctx })
      }
    } catch (e) {
      setUrlError(String(e))
    } finally {
      setUrlUploading(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="pt-4 flex flex-col gap-4">

      {/* ── Top row: folders + document list ─────────────────────────────── */}
      <div className="flex gap-4 h-64">

        {/* Folder column — fixed width, scrollable */}
        <div className="w-44 flex-shrink-0 flex flex-col gap-2">
          {folderError && (
            <Alert color="failure" className="text-xs p-2">{folderError}</Alert>
          )}

          {/* New folder input */}
          <div className="flex gap-1">
            <TextInput
              sizing="sm"
              placeholder={t('admin.documents.folder_name_placeholder')}
              value={newFolderName}
              onChange={e => setNewFolderName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreateFolder()}
              className="flex-1"
            />
            <Button
              size="sm"
              onClick={handleCreateFolder}
              disabled={creatingFolder || !newFolderName.trim()}
            >
              {creatingFolder ? <Spinner size="sm" /> : '+'}
            </Button>
          </div>

          {/* Scrollable folder list */}
          {loadingFolders ? (
            <Spinner />
          ) : (
            <div className="flex-1 overflow-y-auto flex flex-col gap-0.5">
              {folders.map(folder => (
                <div
                  key={folder.id}
                  className={`group flex items-center gap-1 px-2 py-1.5 rounded cursor-pointer text-sm ${
                    selectedFolder?.id === folder.id
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'hover:bg-gray-100 text-gray-700'
                  }`}
                  onClick={() => renamingFolderId !== folder.id && setSelectedFolder(folder)}
                >
                  {renamingFolderId === folder.id ? (
                    <TextInput
                      sizing="sm"
                      autoFocus
                      value={renameValue}
                      placeholder={t('admin.documents.folder_rename_placeholder')}
                      onChange={e => setRenameValue(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') commitRename(folder.id)
                        if (e.key === 'Escape') setRenamingFolderId(null)
                      }}
                      onBlur={() => commitRename(folder.id)}
                      onClick={e => e.stopPropagation()}
                      className="flex-1"
                    />
                  ) : (
                    <>
                      <span className="flex-1 truncate">{folder.name}</span>
                      <button
                        className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-500 transition-opacity text-base leading-none"
                        onClick={e => { e.stopPropagation(); startRename(folder) }}
                        title="Rename"
                      >
                        ✎
                      </button>
                      <button
                        onClick={e => { e.stopPropagation(); handleDownloadFolder(folder) }}
                        title="Download folder as ZIP"
                        className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-600 transition-opacity p-1"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </button>
                      <button
                        className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity text-lg leading-none"
                        onClick={e => { e.stopPropagation(); setFolderToDelete(folder) }}
                        title={t('admin.documents.delete_folder')}
                      >
                        ×
                      </button>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Document list column — flex-1, scrollable */}
        <div className="flex-1 flex flex-col gap-2 min-w-0">
          {/* Upload controls */}
          <div className="flex gap-2 flex-shrink-0">
            <Button
              size="sm"
              disabled={!selectedFolder}
              onClick={() => setUploadModalOpen(true)}
            >
              {t('admin.documents.upload_file')}
            </Button>
            <Button
              size="sm"
              color="light"
              disabled={!selectedFolder}
              onClick={() => setUrlModalOpen(true)}
            >
              {t('admin.documents.add_from_url')}
            </Button>
          </div>

          {!selectedFolder ? (
            <p className="text-gray-500 text-sm">{t('admin.documents.no_folder_selected')}</p>
          ) : loadingDocs ? (
            <Spinner />
          ) : documents.length === 0 ? (
            <p className="text-gray-500 text-sm">{t('admin.documents.no_documents')}</p>
          ) : (
            <div className="flex-1 overflow-y-auto flex flex-col gap-0.5">
              {documents.map(doc => (
                <div
                  key={doc.id}
                  className={`group flex items-center gap-1 px-3 py-2 rounded cursor-pointer text-sm ${
                    selectedDoc?.id === doc.id
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'hover:bg-gray-100 text-gray-700'
                  }`}
                  onClick={() => { setSelectedDoc(doc); setDeleteConfirm(false) }}
                >
                  <span className="flex-1 truncate">{doc.name}</span>
                  <button
                    onClick={e => { e.stopPropagation(); handleDownloadDocument(doc) }}
                    title="Download as markdown"
                    className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-600 transition-opacity p-1 shrink-0"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Properties strip — full width, shown when a document is selected  */}
      {selectedDoc && (
        <div className="border-t border-gray-200 pt-4 flex flex-col gap-3">
          {docError && (
            <Alert color="failure" className="text-xs p-2">{docError}</Alert>
          )}
          <div className="flex gap-4 items-start">
            {/* Name */}
            <div className="w-48 flex-shrink-0">
              <Label className="text-xs text-gray-500 mb-1 block">
                {t('admin.documents.name_label')}
              </Label>
              <TextInput
                sizing="sm"
                value={propName}
                onChange={e => setPropName(e.target.value)}
                onBlur={handlePropNameBlur}
                disabled={propSaving}
              />
            </div>

            {/* Description */}
            <div className="flex-1">
              <Label className="text-xs text-gray-500 mb-1 block">
                {t('admin.documents.description_label')}
              </Label>
              <Textarea
                rows={3}
                value={propDescription}
                onChange={e => setPropDescription(e.target.value)}
                onBlur={handlePropDescriptionBlur}
                disabled={propSaving}
                className="text-sm"
              />
            </div>

            {/* Move + Delete */}
            <div className="w-48 flex-shrink-0 flex flex-col gap-2">
              <div>
                <Label className="text-xs text-gray-500 mb-1 block">
                  {t('admin.documents.move_to_folder')}
                </Label>
                <div className="flex gap-2 items-center">
                  <Select
                    sizing="sm"
                    className="flex-1"
                    value={propFolderId}
                    onChange={e => setPropFolderId(e.target.value)}
                  >
                    {folders.map(f => (
                      <option key={f.id} value={f.id}>{f.name}</option>
                    ))}
                  </Select>
                  <Button size="sm" onClick={handleMove} disabled={!movePending}>
                    {t('admin.documents.move_button')}
                  </Button>
                </div>
              </div>
              <div>
                <Button size="sm" color="failure" onClick={handleDeleteDocument}>
                  {deleteConfirm
                    ? t('admin.documents.delete_confirm')
                    : t('admin.documents.delete_document')}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}


      {/* ── Upload File modal ─────────────────────────────────────────────── */}
      <Modal show={uploadModalOpen} onClose={closeUploadModal} size="md">
        <ModalHeader>{t('admin.documents.upload_file_modal_title')}</ModalHeader>
        <ModalBody>
          <div className="flex flex-col gap-4">
            {uploadError && <Alert color="failure">{uploadError}</Alert>}

            {uploadNeedsDesc ? (
              /* Too-long flow — description required before retrying */
              <Alert color="warning">
                <p className="font-semibold">{t('admin.documents.too_long_title')}</p>
                <p className="text-sm mt-1">
                  {t('admin.documents.too_long_body')
                    .replace('{{words}}', uploadNeedsDesc.wordCount.toLocaleString())
                    .replace('{{tokens}}', (uploadNeedsDesc.wordCount * 2).toLocaleString())
                    .replace('{{ctx}}', uploadNeedsDesc.numCtx.toLocaleString())}
                </p>
                <div className="mt-2">
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.description_placeholder')}
                    value={uploadDescription}
                    onChange={e => setUploadDescription(e.target.value)}
                  />
                </div>
              </Alert>
            ) : (
              <>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.upload_file')}</Label>
                  <FileInput
                    ref={fileInputRef}
                    accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.html,.htm"
                    onChange={e => setUploadFile(e.target.files?.[0] ?? null)}
                  />
                </div>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.name_label')}</Label>
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.name_placeholder_file')}
                    value={uploadName}
                    onChange={e => setUploadName(e.target.value)}
                  />
                </div>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.description_label')}</Label>
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.description_hint')}
                    value={uploadDescription}
                    onChange={e => setUploadDescription(e.target.value)}
                  />
                </div>
              </>
            )}
          </div>
        </ModalBody>
        <ModalFooter>
          <Button
            onClick={handleUpload}
            disabled={
              !uploadFile ||
              uploading ||
              (uploadNeedsDesc !== null && !uploadDescription.trim())
            }
          >
            {uploading ? (
              <Spinner size="sm" />
            ) : uploadNeedsDesc ? (
              t('admin.documents.submit_with_description')
            ) : (
              t('admin.documents.upload_button')
            )}
          </Button>
          <Button color="gray" onClick={closeUploadModal}>
            {t('admin.documents.cancel')}
          </Button>
        </ModalFooter>
      </Modal>

      {/* ── Add from URL modal ────────────────────────────────────────────── */}
      <Modal show={urlModalOpen} onClose={closeUrlModal} size="md">
        <ModalHeader>{t('admin.documents.from_url_modal_title')}</ModalHeader>
        <ModalBody>
          <div className="flex flex-col gap-4">
            {urlError && <Alert color="failure">{urlError}</Alert>}

            {urlNeedsDesc ? (
              <Alert color="warning">
                <p className="font-semibold">{t('admin.documents.too_long_title')}</p>
                <p className="text-sm mt-1">
                  {t('admin.documents.too_long_body')
                    .replace('{{words}}', urlNeedsDesc.wordCount.toLocaleString())
                    .replace('{{tokens}}', (urlNeedsDesc.wordCount * 2).toLocaleString())
                    .replace('{{ctx}}', urlNeedsDesc.numCtx.toLocaleString())}
                </p>
                <div className="mt-2">
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.description_placeholder')}
                    value={urlDescription}
                    onChange={e => setUrlDescription(e.target.value)}
                  />
                </div>
              </Alert>
            ) : (
              <>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.url_label')}</Label>
                  <TextInput
                    sizing="sm"
                    placeholder="https://..."
                    value={urlInput}
                    onChange={e => setUrlInput(e.target.value)}
                  />
                </div>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.name_label')}</Label>
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.name_placeholder_url')}
                    value={urlName}
                    onChange={e => setUrlName(e.target.value)}
                  />
                </div>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.description_label')}</Label>
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.description_hint')}
                    value={urlDescription}
                    onChange={e => setUrlDescription(e.target.value)}
                  />
                </div>
              </>
            )}
          </div>
        </ModalBody>
        <ModalFooter>
          <Button
            onClick={handleUrlUpload}
            disabled={
              !urlInput.trim() ||
              urlUploading ||
              (urlNeedsDesc !== null && !urlDescription.trim())
            }
          >
            {urlUploading ? (
              <Spinner size="sm" />
            ) : urlNeedsDesc ? (
              t('admin.documents.submit_with_description')
            ) : (
              t('admin.documents.add_button')
            )}
          </Button>
          <Button color="gray" onClick={closeUrlModal}>
            {t('admin.documents.cancel')}
          </Button>
        </ModalFooter>
      </Modal>

      {/* ── Delete folder confirmation modal ──────────────────────────────── */}
      <Modal show={!!folderToDelete} onClose={() => setFolderToDelete(null)} size="sm">
        <ModalHeader>{t('admin.documents.delete_folder')}</ModalHeader>
        <ModalBody>
          <p>{t('admin.documents.delete_folder_confirm')}</p>
        </ModalBody>
        <ModalFooter>
          <Button
            color="failure"
            onClick={() => folderToDelete && handleDeleteFolder(folderToDelete)}
          >
            {t('admin.documents.delete_folder')}
          </Button>
          <Button color="gray" onClick={() => setFolderToDelete(null)}>
            {t('admin.documents.cancel')}
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  )
}
