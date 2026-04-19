/**
 * API client for bundle export/import.
 *
 * exportBundle()  — downloads all gems and documents as a ZIP blob.
 * importBundle()  — POSTs a ZIP file to the import endpoint.
 */
import { getBlob, postFormData } from './client'

/** Summary returned by the backend after a bundle import. */
export interface ImportResult {
  folders_created: number
  documents_imported: number
  /** Map of original doc ID → renamed ID (only populated in Add mode). */
  documents_renamed: Record<string, string>
  gems_imported: number
  /** Map of original gem ID → renamed ID (only populated in Add mode). */
  gems_renamed: Record<string, string>
}

export type ImportMode = 'add' | 'replace'

export const bundleApi = {
  /**
   * Fetch the full bundle ZIP from the server.
   * Returns a Blob; the caller is responsible for triggering the download.
   */
  exportBundle: (): Promise<Blob> =>
    getBlob('/app/admin/bundle/export'),

  /**
   * Upload a bundle ZIP for import.
   *
   * @param file The ZIP file chosen by the admin.
   * @param mode 'add' merges with existing data (renaming on collision);
   *             'replace' wipes existing data first.
   */
  importBundle: async (file: File, mode: ImportMode): Promise<ImportResult> => {
    const form = new FormData()
    form.append('file', file)
    form.append('mode', mode)
    const res = await postFormData('/app/admin/bundle/import', form)
    return res.json()
  },
}
