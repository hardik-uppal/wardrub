import { useRef, forwardRef, useImperativeHandle } from 'react'

const Camera = forwardRef(function Camera({ onCapture, children }, ref) {
  const inputRef = useRef(null)

  useImperativeHandle(ref, () => ({
    trigger: () => inputRef.current?.click(),
  }))

  const handleChange = (e) => {
    const file = e.target.files?.[0]
    if (file && onCapture) {
      onCapture(file)
    }
    // Reset input for re-capture
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleChange}
        className="hidden"
      />
      {children}
    </>
  )
})

export default Camera





