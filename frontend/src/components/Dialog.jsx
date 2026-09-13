import { useEffect, useRef } from 'react'
export default function Dialog({ title, onClose, children }) {
  const ref = useRef(null)
  useEffect(() => {
    const dialog = ref.current
    dialog.showModal()
    return () => dialog.close()
  }, [])
  return (
    <dialog
      ref={ref}
      onCancel={onClose}
      aria-label={title}
      className="quiet-dialog"
    >
      <div className="context-row">
        <h2>{title}</h2>
        <button className="icon-control" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>
      {children}
    </dialog>
  )
}
