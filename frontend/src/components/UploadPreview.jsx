import { useState } from 'react'

function Preview({ src, alt, className }) {
  const [failed, setFailed] = useState(false)
  if (failed) return <p className="p-4 text-sm" role="status">Preview unavailable in this browser. You can still upload this photo; supported formats are checked on the server.</p>
  return <img src={src} alt={alt} className={className} onError={() => setFailed(true)} />
}

export default function UploadPreview(props) {
  return <Preview key={props.src} {...props} />
}
