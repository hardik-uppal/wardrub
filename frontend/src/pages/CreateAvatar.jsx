import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Camera, User, X, Sparkles, Upload, Image } from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import LoadingOverlay from '../components/LoadingOverlay'
import BottomNav from '../components/BottomNav'

export default function CreateAvatar() {
  const navigate = useNavigate()
  const { avatarUrl, createAvatar, isLoading, loadingMessage, error, clearError } = useWardrobe()
  
  const [mode, setMode] = useState(null) // 'upload' or 'selfie'
  const [image, setImage] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const uploadInputRef = useRef(null)
  const selfieInputRef = useRef(null)

  const handleImageSelect = (e, selectedMode) => {
    const file = e.target.files?.[0]
    if (file) {
      setMode(selectedMode)
      setImage(file)
      
      const reader = new FileReader()
      reader.onload = (event) => {
        setPreviewUrl(event.target?.result)
      }
      reader.readAsDataURL(file)
    }
    // Reset inputs
    if (uploadInputRef.current) uploadInputRef.current.value = ''
    if (selfieInputRef.current) selfieInputRef.current.value = ''
  }

  const handleRemoveImage = () => {
    setMode(null)
    setImage(null)
    setPreviewUrl(null)
  }

  const handleCreate = async () => {
    if (!image) return

    try {
      // Pass mode to backend so it knows how to process
      await createAvatar([image], mode)
      navigate('/')
    } catch (err) {
      console.error('Failed to create avatar:', err)
    }
  }

  const triggerUpload = () => {
    uploadInputRef.current?.click()
  }
  
  const triggerSelfie = () => {
    selfieInputRef.current?.click()
  }

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-cream)] safe-top safe-bottom overflow-y-auto">
      {isLoading && <LoadingOverlay message={loadingMessage} />}

      {/* Hidden file inputs */}
      <input
        ref={uploadInputRef}
        type="file"
        accept="image/*"
        onChange={(e) => handleImageSelect(e, 'upload')}
        className="hidden"
      />
      <input
        ref={selfieInputRef}
        type="file"
        accept="image/*"
        capture="user"
        onChange={(e) => handleImageSelect(e, 'selfie')}
        className="hidden"
      />

      <div className="flex-1 flex flex-col page-container">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3">
          <button
            onClick={() => navigate('/')}
            className="w-9 h-9 rounded-full bg-[var(--color-charcoal)]/5 flex items-center justify-center"
          >
            <ArrowLeft className="w-4 h-4 text-[var(--color-charcoal)]" />
          </button>
          
          <h1 className="text-base font-semibold text-[var(--color-charcoal)]">
            Create Avatar
          </h1>
          
          <div className="w-9" />
        </header>

        {/* Error Toast */}
        {error && (
          <div 
            className="mx-4 mb-3 bg-[var(--color-terracotta)] text-white px-3 py-2 rounded-xl animate-fade-in"
            onClick={clearError}
          >
            <p className="text-sm">{error}</p>
          </div>
        )}

        <div className="flex-1 px-5 overflow-y-auto">
          {/* Current Avatar Preview */}
          {avatarUrl && (
            <div className="mb-6">
              <p className="text-sm text-[var(--color-warm-gray)] mb-3 text-center">Current Avatar</p>
              <div className="w-28 h-40 mx-auto rounded-xl overflow-hidden bg-white shadow-lg">
                <img
                  src={avatarUrl}
                  alt="Current avatar"
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          )}

          {/* Instructions */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-terracotta)]/10 flex items-center justify-center">
              <User className="w-8 h-8 text-[var(--color-terracotta)]" />
            </div>
            <h2 className="text-xl font-semibold text-[var(--color-charcoal)] mb-2">
              {avatarUrl ? 'Update Your Avatar' : 'Create Your Avatar'}
            </h2>
            <p className="text-sm text-[var(--color-warm-gray)] max-w-[300px] mx-auto">
              Upload a full-body photo for best results, or take a selfie for quick setup
            </p>
          </div>

          {/* Image Preview or Selection */}
          {previewUrl ? (
            <div className="flex flex-col items-center mb-8">
              <div className="relative w-52 rounded-2xl overflow-hidden bg-white shadow-lg animate-fade-in">
                <img
                  src={previewUrl}
                  alt="Your photo"
                  className="w-full h-auto object-contain"
                />
                <button
                  onClick={handleRemoveImage}
                  className="absolute top-3 right-3 w-10 h-10 rounded-full bg-[var(--color-charcoal)]/80 flex items-center justify-center"
                >
                  <X className="w-5 h-5 text-white" />
                </button>
              </div>
              <p className="mt-3 text-sm text-[var(--color-warm-gray)]">
                {mode === 'upload' ? '📷 Full body photo' : '🤳 Selfie (will use default body)'}
              </p>
            </div>
          ) : (
            <div className="flex gap-4 justify-center mb-8">
              {/* Upload Full Body Option */}
              <button
                onClick={triggerUpload}
                className="w-40 h-48 rounded-2xl border-2 border-dashed border-[var(--color-terracotta)]/30 flex flex-col items-center justify-center gap-3 transition-all hover:border-[var(--color-terracotta)] hover:bg-[var(--color-terracotta)]/5"
              >
                <div className="w-14 h-14 rounded-full bg-[var(--color-terracotta)]/10 flex items-center justify-center">
                  <Upload className="w-7 h-7 text-[var(--color-terracotta)]" />
                </div>
                <span className="text-base text-[var(--color-charcoal)] font-medium">
                  Upload Photo
                </span>
                <span className="text-xs text-[var(--color-warm-gray)] text-center px-3">
                  Full body visible
                </span>
              </button>
              
              {/* Take Selfie Option */}
              <button
                onClick={triggerSelfie}
                className="w-40 h-48 rounded-2xl border-2 border-dashed border-[var(--color-warm-gray)]/30 flex flex-col items-center justify-center gap-3 transition-all hover:border-[var(--color-charcoal)] hover:bg-[var(--color-charcoal)]/5"
              >
                <div className="w-14 h-14 rounded-full bg-[var(--color-warm-gray)]/10 flex items-center justify-center">
                  <Camera className="w-7 h-7 text-[var(--color-warm-gray)]" />
                </div>
                <span className="text-base text-[var(--color-charcoal)] font-medium">
                  Take Selfie
                </span>
                <span className="text-xs text-[var(--color-warm-gray)] text-center px-3">
                  Quick setup
                </span>
              </button>
            </div>
          )}

          {/* Tips */}
          <div className="bg-[var(--color-sage)]/10 rounded-xl p-4 mb-6">
            <h3 className="text-sm font-semibold text-[var(--color-charcoal)] mb-2">
              {mode === 'selfie' ? 'Selfie tips' : 'Photo tips'}
            </h3>
            <ul className="space-y-1.5 text-xs text-[var(--color-warm-gray)]">
              {mode === 'selfie' ? (
                <>
                  <li>• Face the camera with good lighting</li>
                  <li>• Your face will be applied to a default body</li>
                </>
              ) : (
                <>
                  <li>• Show full body from head to toe</li>
                  <li>• Stand straight, facing the camera</li>
                  <li>• Plain background works best</li>
                  <li>• Good lighting, clear photo</li>
                </>
              )}
            </ul>
          </div>
        </div>

        {/* Create Button */}
        <div className="px-5 nav-bottom-spacing">
          <button
            onClick={handleCreate}
            disabled={!image || isLoading}
            className="w-full flex items-center justify-center gap-2 py-4 bg-[var(--color-terracotta)] text-white rounded-xl font-medium transition-all active:scale-98 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Sparkles className="w-5 h-5" />
            {mode === 'selfie' ? 'Create with Selfie' : 'Create Avatar'}
          </button>
          
          {image && (
            <p className="text-center text-xs text-[var(--color-warm-gray)] mt-3">
              {mode === 'selfie' ? 'Will apply your face to default avatar' : 'Processing your photo'}
            </p>
          )}
        </div>
      </div>
      
      {/* Bottom Navigation */}
      <BottomNav />
    </div>
  )
}

