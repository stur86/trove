/**
 * InfoButton — a small (i) icon that opens a Flowbite modal with contextual help.
 *
 * Usage:
 *   <InfoButton title="Template tips">
 *     <p>Use &#123;&#123; variable &#125;&#125; for user inputs...</p>
 *   </InfoButton>
 *
 * The button is inline so it can sit next to a Label without breaking layout.
 */
import { useState } from 'react'
import { Modal, ModalBody, ModalHeader } from 'flowbite-react'

interface InfoButtonProps {
  /** Title shown in the modal header. */
  title: string
  /** Body content — any React nodes. */
  children: React.ReactNode
}

/**
 * Renders a small circular ⓘ button that opens a modal with the provided content.
 * Designed to be placed inline next to form labels.
 */
export default function InfoButton({ title, children }: InfoButtonProps) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title={title}
        className="inline-flex items-center justify-center w-4 h-4 ml-1 text-xs font-bold text-gray-400 border border-gray-300 rounded-full hover:text-blue-600 hover:border-blue-400 transition-colors align-middle"
        aria-label={`Info: ${title}`}
      >
        i
      </button>

      <Modal show={open} onClose={() => setOpen(false)} size="md" dismissible>
        <ModalHeader>{title}</ModalHeader>
        <ModalBody>
          <div className="text-sm text-gray-700 flex flex-col gap-3">
            {children}
          </div>
        </ModalBody>
      </Modal>
    </>
  )
}
