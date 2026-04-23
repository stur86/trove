/**
 * HelpBar — a full-width clickable info strip that opens a help modal.
 *
 * Usage:
 *   <HelpBar
 *     prompt={t('help.model.prompt')}
 *     title={t('help.model.title')}
 *     content={t('help.model.content')}
 *   />
 *
 * All strings are pre-resolved by the caller via useTranslation.
 * Content is rendered as Markdown by default (markdown prop).
 */
import { useState } from 'react'
import { HiInformationCircle } from 'react-icons/hi'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Modal, ModalBody, ModalHeader } from 'flowbite-react'

interface HelpBarProps {
  /** Clickable label shown on the strip (pre-translated). */
  prompt: string
  /** Modal header title (pre-translated). */
  title: string
  /** Modal body content (pre-translated, typically Markdown from a locale file). */
  content: string
  /** Render content as Markdown. Defaults to true. */
  markdown?: boolean
}

/**
 * Renders a blue info strip; clicking it opens a modal with the provided content.
 * Designed to sit between form sections in the admin panel.
 */
export default function HelpBar({ prompt, title, content, markdown = true }: HelpBarProps) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-sm text-blue-700 hover:bg-blue-100 transition-colors"
      >
        <HiInformationCircle className="w-4 h-4 shrink-0" />
        <span className="flex-1 text-left font-medium">{prompt}</span>
        <span className="text-blue-400 text-xs">Read more →</span>
      </button>

      <Modal show={open} onClose={() => setOpen(false)} size="lg" dismissible>
        <ModalHeader>{title}</ModalHeader>
        <ModalBody>
          {markdown ? (
            <div className="text-sm text-gray-700 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mb-2 [&_h3]:text-sm [&_h3]:font-semibold [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:mb-1 [&_p]:mb-3 [&_table]:w-full [&_table]:text-xs [&_th]:text-left [&_th]:pb-1 [&_td]:pr-4 [&_td]:pb-1 [&_strong]:font-semibold [&_code]:bg-gray-100 [&_code]:px-1 [&_code]:rounded [&_code]:font-mono [&_pre]:bg-gray-100 [&_pre]:p-3 [&_pre]:rounded [&_pre]:text-xs [&_pre]:overflow-x-auto [&_pre_code]:bg-transparent [&_pre_code]:p-0">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-gray-700">{content}</p>
          )}
        </ModalBody>
      </Modal>
    </>
  )
}
