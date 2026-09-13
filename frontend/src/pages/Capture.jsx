import { useNavigate, useSearchParams } from 'react-router-dom'
import { PageHeader } from '../components/AppChrome'
import BottomNav from '../components/BottomNav'
import GalleryUpload from '../components/GalleryUpload'

export default function Capture() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const returnTo = params.get('from') === 'today' ? '/' : '/wardrobe'
  return (
    <div className="quiet-page capture-page">
      <PageHeader title="Add clothes" back={returnTo} />
      <p className="muted">
        One photo is enough. Worn, hanging or laid flat—we’ll find and label the
        clothes.
      </p>
      <GalleryUpload onDone={() => navigate(returnTo)} />
      <BottomNav />
    </div>
  )
}
