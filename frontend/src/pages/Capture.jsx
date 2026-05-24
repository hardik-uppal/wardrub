import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Camera, X, Check, RotateCcw, Plus, Sparkles, Upload, Image } from 'lucide-react'
import { useWardrobe } from '../context/WardrobeContext'
import LoadingOverlay from '../components/LoadingOverlay'
import BottomNav from '../components/BottomNav'

const categories = [
  { id: 'top', label: 'Top', icon: '👕' },
  { id: 'bottom', label: 'Bottom', icon: '👖' },
  { id: 'dress', label: 'Dress', icon: '👗' },
  { id: 'outerwear', label: 'Outer', icon: '🧥' },
]

// Input mode - 'select' (choose method), 'upload' (from gallery), 'capture' (take photo)
const INPUT_MODES = {
  SELECT: 'select',
  UPLOAD: 'upload',
  CAPTURE: 'capture',
}

// SVG guide paths for each garment category
const GuideGraphics = {
  top: (
    <svg width="140" height="160" viewBox="0 0 200 220" className="text-white/40">
      <path
        d="M50 50 L50 20 Q50 10 60 10 L80 10 Q90 15 100 15 Q110 15 120 10 L140 10 Q150 10 150 20 L150 50 L130 50 L130 210 L70 210 L70 50 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeDasharray="8 4"
      />
      <path d="M80 10 Q100 30 120 10" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="8 4" />
      <path d="M50 20 L20 60 L30 70 L50 50" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="8 4" />
      <path d="M150 20 L180 60 L170 70 L150 50" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="8 4" />
    </svg>
  ),
  bottom: (
    <svg width="140" height="180" viewBox="0 0 200 240" className="text-white/40">
      <path
        d="M50 10 L50 100 L30 230 L70 230 L100 120 L130 230 L170 230 L150 100 L150 10 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeDasharray="8 4"
      />
      <path d="M50 10 L150 10" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="8 4" />
    </svg>
  ),
  dress: (
    <svg width="140" height="180" viewBox="0 0 200 240" className="text-white/40">
      <path
        d="M70 10 Q100 25 130 10 L130 20 L150 20 L150 50 L135 50 L160 230 L40 230 L65 50 L50 50 L50 20 L70 20 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeDasharray="8 4"
      />
    </svg>
  ),
  outerwear: (
    <svg width="140" height="180" viewBox="0 0 200 240" className="text-white/40">
      <path
        d="M60 10 L60 20 Q60 30 70 30 L80 30 Q90 15 100 15 Q110 15 120 30 L130 30 Q140 30 140 20 L140 10"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeDasharray="8 4"
      />
      <path
        d="M60 20 L40 40 L40 80 L60 60 L60 220 L95 220 L95 100 L105 100 L105 220 L140 220 L140 60 L160 80 L160 40 L140 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeDasharray="8 4"
      />
    </svg>
  ),
}

const categoryLabels = {
  top: 'top/shirt',
  bottom: 'pants/shorts',
  dress: 'dress/skirt',
  outerwear: 'jacket/coat',
}

export default function Capture() {
  const navigate = useNavigate()
  const { processGarment, processUploadedClothes, isLoading, loadingMessage, error, clearError } = useWardrobe()
  
  const [inputMode, setInputMode] = useState(INPUT_MODES.SELECT) // 'select', 'upload', 'capture'
  const [frontImage, setFrontImage] = useState(null)
  const [frontFile, setFrontFile] = useState(null)
  const [backImage, setBackImage] = useState(null)
  const [backFile, setBackFile] = useState(null)
  const [uploadedImage, setUploadedImage] = useState(null)
  const [uploadedFile, setUploadedFile] = useState(null)
  const [selectedCategory, setSelectedCategory] = useState('top')
  const [captureMode, setCaptureMode] = useState('front') // 'front', 'back', 'preview'
  const [useGhostMannequin, setUseGhostMannequin] = useState(true)
  
  const fileInputRef = useRef(null)
  const uploadInputRef = useRef(null)

  // Webcam capture states/refs
  const [showWebcam, setShowWebcam] = useState(false)
  const videoRef = useRef(null)
  const streamRef = useRef(null)

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  const startWebcam = async () => {
    setShowWebcam(true)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: 1280, height: 720 }
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
      }
    } catch (err) {
      console.error('Failed to get webcam stream:', err)
      setShowWebcam(false)
      // Fallback to standard input click
      fileInputRef.current?.click()
    }
  }

  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    setShowWebcam(false)
  }

  const capturePhoto = () => {
    if (videoRef.current) {
      const canvas = document.createElement('canvas')
      canvas.width = videoRef.current.videoWidth || 1280
      canvas.height = videoRef.current.videoHeight || 720
      const ctx = canvas.getContext('2d')
      if (ctx) {
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height)
        
        canvas.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], 'captured_garment.jpg', { type: 'image/jpeg' })
            const dataUrl = canvas.toDataURL('image/jpeg')
            
            if (captureMode === 'front') {
              setFrontImage(dataUrl)
              setFrontFile(file)
              setCaptureMode('preview')
            } else if (captureMode === 'back') {
              setBackImage(dataUrl)
              setBackFile(file)
              setCaptureMode('preview')
            }
            stopWebcam()
          }
        }, 'image/jpeg', 0.95)
      }
    }
  }

  const handleCapture = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (event) => {
        if (captureMode === 'front') {
          setFrontImage(event.target?.result)
          setFrontFile(file)
          setCaptureMode('preview')
        } else if (captureMode === 'back') {
          setBackImage(event.target?.result)
          setBackFile(file)
          setCaptureMode('preview')
        }
      }
      reader.readAsDataURL(file)
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleUploadSelect = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (event) => {
        setUploadedImage(event.target?.result)
        setUploadedFile(file)
      }
      reader.readAsDataURL(file)
    }
    // Reset input
    if (uploadInputRef.current) {
      uploadInputRef.current.value = ''
    }
  }

  const handleUploadProcess = async () => {
    if (!uploadedFile) return
    
    try {
      await processUploadedClothes(uploadedFile)
      navigate('/')
    } catch (err) {
      console.error('Failed to process upload:', err)
    }
  }

  const handleResetUpload = () => {
    setUploadedImage(null)
    setUploadedFile(null)
  }

  const handleRetakeFront = () => {
    setFrontImage(null)
    setFrontFile(null)
    setCaptureMode('front')
  }

  const handleRetakeBack = () => {
    setBackImage(null)
    setBackFile(null)
    setCaptureMode('back')
  }

  const handleAddBack = () => {
    setCaptureMode('back')
    setTimeout(() => fileInputRef.current?.click(), 100)
  }

  const handleSkipBack = () => {
    setCaptureMode('preview')
  }

  const handleConfirm = async () => {
    if (!frontFile || !selectedCategory) return

    try {
      await processGarment(frontFile, backFile, selectedCategory, useGhostMannequin)
      navigate('/')
    } catch (err) {
      console.error('Failed to process:', err)
    }
  }

  const triggerCapture = () => {
    startWebcam()
  }
  
  const triggerUpload = () => {
    uploadInputRef.current?.click()
  }
  
  const startCaptureMode = () => {
    setInputMode(INPUT_MODES.CAPTURE)
    setCaptureMode('front')
  }
  
  const startUploadMode = () => {
    setInputMode(INPUT_MODES.UPLOAD)
  }
  
  const goBackToSelect = () => {
    setInputMode(INPUT_MODES.SELECT)
    // Reset states
    setFrontImage(null)
    setFrontFile(null)
    setBackImage(null)
    setBackFile(null)
    setUploadedImage(null)
    setUploadedFile(null)
    setCaptureMode('front')
  }

  // Mode selection screen
  const renderModeSelect = () => (
    <div className="flex-1 flex flex-col items-center justify-center px-6">
      <div className="text-center mb-10">
        <h2 className="text-xl font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>How would you like to add clothes?</h2>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Choose the best option for your situation</p>
      </div>
      
      <div className="flex flex-col sm:flex-row gap-5">
        {/* Upload from Gallery */}
        <button
          onClick={startUploadMode}
          className="w-40 h-52 rounded-2xl flex flex-col items-center justify-center gap-4 shadow-lg transition-transform hover:scale-[1.03] active:scale-95"
          style={{ background: 'var(--accent)', color: 'white' }}
        >
          <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.1)' }}>
            <Upload className="w-8 h-8 text-white" />
          </div>
          <span className="text-base font-medium">Upload Photo</span>
          <span className="text-xs text-white/70 text-center px-4">
            AI detects clothes in image
          </span>
        </button>
        
        {/* Take Photo */}
        <button
          onClick={startCaptureMode}
          className="w-40 h-52 rounded-2xl flex flex-col items-center justify-center gap-4 transition-transform hover:scale-[1.03] active:scale-95"
          style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', color: 'var(--text-primary)' }}
        >
          <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: 'var(--bg-secondary)' }}>
            <Camera className="w-8 h-8" style={{ color: 'var(--accent)' }} />
          </div>
          <span className="text-base font-medium">Take Photo</span>
          <span className="text-xs text-center px-4" style={{ color: 'var(--text-secondary)' }}>
            Select category & capture
          </span>
        </button>
      </div>
    </div>
  )
  
  // Upload mode view
  const renderUploadView = () => (
    <div className="flex-1 flex flex-col px-5 py-4">
      {uploadedImage ? (
        <div className="flex-1 flex flex-col">
          {/* Image preview */}
          <div className="flex-1 relative rounded-2xl overflow-hidden bg-black/50">
            <img
              src={uploadedImage}
              alt="Uploaded clothes"
              className="w-full h-full object-contain"
            />
            <button
              onClick={handleResetUpload}
              className="absolute top-4 right-4 w-10 h-10 rounded-full bg-black/60 flex items-center justify-center"
            >
              <X className="w-5 h-5 text-white" />
            </button>
          </div>
          
          {/* Info */}
          <div className="mt-4 rounded-xl p-4" style={{ background: 'rgba(17,17,17,0.05)' }}>
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 mt-0.5" style={{ color: 'var(--accent)' }} />
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>AI Detection</p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                  Gemini will analyze this image, detect all clothing items, and create ghost mannequin versions for each.
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <button
            onClick={triggerUpload}
            className="w-52 h-60 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center gap-4 transition-colors hover:bg-gray-50"
            style={{ borderColor: 'var(--glass-border)' }}
          >
            <div className="w-18 h-18 rounded-full flex items-center justify-center" style={{ background: 'var(--bg-secondary)' }}>
              <Image className="w-10 h-10" style={{ color: 'var(--text-tertiary)' }} />
            </div>
            <span className="text-base font-medium" style={{ color: 'var(--text-primary)' }}>Select from Gallery</span>
            <span className="text-xs text-center px-5" style={{ color: 'var(--text-secondary)' }}>
              Works best with photos of clothes worn or laid flat
            </span>
          </button>
        </div>
      )}
    </div>
  )

  const renderCaptureView = () => {
    if (captureMode === 'preview' && frontImage) {
      return (
        <div className="flex-1 flex flex-col">
          {/* Preview images */}
          <div className="flex-1 flex gap-3 p-3">
            {/* Front preview */}
            <div className="flex-1 relative rounded-xl overflow-hidden bg-[var(--bg-primary)]">
              <img
                src={frontImage}
                alt="Front view"
                className="w-full h-full object-contain"
              />
              <div className="absolute top-2 left-2 px-2 py-1 bg-black/60 rounded-lg">
                <span className="text-[10px] text-white font-medium">FRONT</span>
              </div>
              <button
                onClick={handleRetakeFront}
                className="absolute bottom-2 right-2 p-1.5 bg-[var(--glass-bg)]/90 rounded-full"
              >
                <RotateCcw className="w-3 h-3 text-[var(--text-primary)]" />
              </button>
            </div>
            
            {/* Back preview or add button */}
            {backImage ? (
              <div className="flex-1 relative rounded-xl overflow-hidden bg-[var(--bg-primary)]">
                <img
                  src={backImage}
                  alt="Back view"
                  className="w-full h-full object-contain"
                />
                <div className="absolute top-2 left-2 px-2 py-1 bg-black/60 rounded-lg">
                  <span className="text-[10px] text-white font-medium">BACK</span>
                </div>
                <button
                  onClick={handleRetakeBack}
                  className="absolute bottom-2 right-2 p-1.5 bg-[var(--glass-bg)]/90 rounded-full"
                >
                  <RotateCcw className="w-3 h-3 text-[var(--text-primary)]" />
                </button>
              </div>
            ) : (
              <button
                onClick={handleAddBack}
                className="flex-1 rounded-xl border-2 border-dashed border-white/30 flex flex-col items-center justify-center gap-2 hover:border-white/50 transition-colors"
              >
                <Plus className="w-8 h-8 text-white/50" />
                <span className="text-xs text-white/50">Add Back</span>
                <span className="text-[10px] text-white/30">(Optional)</span>
              </button>
            )}
          </div>
          
          {/* Ghost mannequin toggle */}
          <div className="px-4 py-2">
            <button
              onClick={() => setUseGhostMannequin(!useGhostMannequin)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl transition-colors ${
                useGhostMannequin ? 'bg-[var(--accent)]/20' : 'bg-[var(--glass-bg)]/10'
              }`}
            >
              <div className="flex items-center gap-2">
                <Sparkles className={`w-4 h-4 ${useGhostMannequin ? 'text-[var(--accent)]' : 'text-white/50'}`} />
                <span className="text-xs text-white">AI Ghost Mannequin</span>
              </div>
              <div className={`w-8 h-5 rounded-full transition-colors ${useGhostMannequin ? 'bg-[var(--accent)]' : 'bg-[var(--glass-bg)]/30'}`}>
                <div className={`w-4 h-4 rounded-full bg-[var(--glass-bg)] mt-0.5 transition-transform ${useGhostMannequin ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
              </div>
            </button>
            {useGhostMannequin && (
              <p className="text-[10px] text-white/40 mt-1 text-center">
                AI will create a 3D mannequin effect using Gemini
              </p>
            )}
          </div>
        </div>
      )
    }
    
    // Camera capture view
    return (
      <div className="flex-1 relative rounded-2xl overflow-hidden bg-black mx-4 my-2 max-h-[70vh]">
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="relative transition-all duration-300">
            {GuideGraphics[selectedCategory]}
            <p className="text-white/60 text-xs text-center mt-3">
              {captureMode === 'back' ? 'Now capture the BACK view' : `Position your ${categoryLabels[selectedCategory]}`}
            </p>
          </div>
          
          <button
            onClick={triggerCapture}
            className="absolute inset-0 flex items-end justify-center pb-6"
          >
            <span className="text-white/80 text-xs animate-pulse">
              Tap to take {captureMode === 'back' ? 'back' : 'front'} photo
            </span>
          </button>
        </div>
        
        {/* Mode indicator */}
        <div className="absolute top-3 left-3 px-2 py-1 bg-[var(--accent)] rounded-lg">
          <span className="text-[10px] text-white font-medium uppercase">{captureMode}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col safe-top safe-bottom overflow-y-auto" style={{ background: 'var(--bg-primary)' }}>
      {isLoading && <LoadingOverlay message={loadingMessage} />}

      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleCapture}
        className="hidden"
      />
      <input
        ref={uploadInputRef}
        type="file"
        accept="image/*"
        onChange={handleUploadSelect}
        className="hidden"
      />

      <div className="flex-1 flex flex-col max-w-xl mx-auto w-full">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3">
          <button
            onClick={inputMode === INPUT_MODES.SELECT ? () => navigate('/') : goBackToSelect}
            className="w-9 h-9 rounded-full flex items-center justify-center"
            style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          
          <h1 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            {inputMode === INPUT_MODES.SELECT ? 'Add to Wardrobe' : 
             inputMode === INPUT_MODES.UPLOAD ? 'Upload Clothes' : 'Capture Clothes'}
          </h1>
          
          <div className="w-9" />
        </header>

        {/* Error Toast */}
        {error && (
          <div 
            className="mx-4 mb-3 bg-[var(--accent)] text-white px-3 py-2 rounded-xl animate-fade-in"
            onClick={clearError}
          >
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Mode Selection / Camera / Upload View */}
        {inputMode === INPUT_MODES.SELECT && renderModeSelect()}
        {inputMode === INPUT_MODES.UPLOAD && renderUploadView()}
        {inputMode === INPUT_MODES.CAPTURE && renderCaptureView()}

        {/* Category Selection - only for capture mode */}
        {inputMode === INPUT_MODES.CAPTURE && (
          <div className="px-5 py-4">
            <p className="text-sm mb-3 text-center" style={{ color: 'var(--text-secondary)' }}>
              What type of clothing is this?
            </p>
            <div className="flex justify-center gap-3">
              {categories.map(cat => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className="flex flex-col items-center gap-1 px-4 py-2.5 rounded-xl transition-all"
                  style={{
                    background: selectedCategory === cat.id ? 'var(--accent)' : 'var(--glass-bg)',
                    color: selectedCategory === cat.id ? 'white' : 'var(--text-secondary)',
                    border: selectedCategory === cat.id ? '1px solid var(--accent)' : '1px solid var(--glass-border)'
                  }}
                >
                  <span className="text-xl">{cat.icon}</span>
                  <span className="text-xs font-medium">{cat.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="px-5 nav-bottom-spacing">
          {/* Upload mode buttons */}
          {inputMode === INPUT_MODES.UPLOAD && uploadedImage && (
            <div className="flex gap-2">
              <button
                onClick={handleResetUpload}
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-[var(--glass-bg)]/10 text-white rounded-xl font-medium text-sm"
              >
                <RotateCcw className="w-4 h-4" />
                Change
              </button>
              <button
                onClick={handleUploadProcess}
                disabled={isLoading}
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-[var(--accent)] text-white rounded-xl font-medium text-sm disabled:opacity-50"
              >
                <Sparkles className="w-4 h-4" />
                Detect & Add
              </button>
            </div>
          )}
          
          {/* Capture mode buttons */}
          {inputMode === INPUT_MODES.CAPTURE && (
            <>
              {captureMode === 'preview' && frontImage ? (
                <div className="flex gap-2">
                  <button
                    onClick={handleRetakeFront}
                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-[var(--glass-bg)]/10 text-white rounded-xl font-medium text-sm"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Start Over
                  </button>
                  <button
                    onClick={handleConfirm}
                    disabled={isLoading}
                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-[var(--accent)] text-white rounded-xl font-medium text-sm disabled:opacity-50"
                  >
                    <Check className="w-4 h-4" />
                    Process
                  </button>
                </div>
              ) : captureMode === 'back' ? (
                <div className="flex gap-2">
                  <button
                    onClick={handleSkipBack}
                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-[var(--glass-bg)]/10 text-white rounded-xl font-medium text-sm"
                  >
                    Skip Back
                  </button>
                  <button
                    onClick={triggerCapture}
                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-[var(--accent)] text-white rounded-xl font-medium text-sm"
                  >
                    <Camera className="w-4 h-4" />
                    Capture Back
                  </button>
                </div>
              ) : (
                <button
                  onClick={triggerCapture}
                  className="w-full flex items-center justify-center gap-2 py-3 bg-[var(--accent)] text-white rounded-xl font-medium text-sm transition-all active:scale-98"
                >
                  <Camera className="w-4 h-4" />
                  Take Front Photo
                </button>
              )}
            </>
          )}
        </div>
      </div>
      
      {showWebcam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-fade-in">
          <div className="bg-[var(--bg-primary)] border border-[var(--glass-border)] rounded-3xl max-w-sm w-full overflow-hidden shadow-2xl p-6 flex flex-col items-center">
            <div className="flex justify-between items-center w-full mb-5">
              <h3 className="text-base font-bold text-[var(--text-primary)]">
                {captureMode === 'front' ? 'Capture Front Photo' : 'Capture Back Photo'}
              </h3>
              <button 
                onClick={stopWebcam} 
                className="w-8 h-8 rounded-full border border-[var(--glass-border)] flex items-center justify-center hover:bg-[var(--bg-secondary)] text-[var(--text-primary)] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            {/* Webcam Video (smaller window) */}
            <div className="relative w-56 h-56 rounded-2xl overflow-hidden border-2 border-[var(--accent)] bg-black mb-6 shadow-inner">
              <video 
                ref={videoRef} 
                className="w-full h-full object-cover"
                playsInline 
                muted 
              />
              {/* Optional silhouette overlay for guidance */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-40">
                {GuideGraphics[selectedCategory]}
              </div>
            </div>

            <button
              onClick={capturePhoto}
              className="btn-primary w-full py-3 rounded-xl font-medium text-sm flex items-center justify-center gap-2"
              style={{ background: 'var(--accent)' }}
            >
              <Camera className="w-4 h-4" />
              Capture Photo
            </button>
          </div>
        </div>
      )}
      
      {/* Bottom Navigation */}
      <BottomNav />
    </div>
  )
}
