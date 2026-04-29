import { useState, useRef } from 'react'
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
    fileInputRef.current?.click()
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
        <h2 className="text-xl font-semibold text-white mb-3">How would you like to add clothes?</h2>
        <p className="text-sm text-white/60">Choose the best option for your situation</p>
      </div>
      
      <div className="flex gap-5">
        {/* Upload from Gallery */}
        <button
          onClick={startUploadMode}
          className="w-40 h-52 rounded-2xl bg-gradient-to-br from-[var(--color-terracotta)] to-[var(--color-terracotta)]/80 flex flex-col items-center justify-center gap-4 shadow-lg"
        >
          <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center">
            <Upload className="w-8 h-8 text-white" />
          </div>
          <span className="text-base text-white font-medium">Upload Photo</span>
          <span className="text-xs text-white/70 text-center px-4">
            AI detects clothes in image
          </span>
        </button>
        
        {/* Take Photo */}
        <button
          onClick={startCaptureMode}
          className="w-40 h-52 rounded-2xl bg-gradient-to-br from-white/20 to-white/10 border border-white/20 flex flex-col items-center justify-center gap-4"
        >
          <div className="w-16 h-16 rounded-full bg-white/10 flex items-center justify-center">
            <Camera className="w-8 h-8 text-white" />
          </div>
          <span className="text-base text-white font-medium">Take Photo</span>
          <span className="text-xs text-white/70 text-center px-4">
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
          <div className="mt-4 bg-[var(--color-sage)]/20 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-[var(--color-sage)] mt-0.5" />
              <div>
                <p className="text-sm text-white font-medium">AI Detection</p>
                <p className="text-xs text-white/60 mt-1">
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
            className="w-52 h-60 rounded-2xl border-2 border-dashed border-white/30 flex flex-col items-center justify-center gap-4 hover:border-white/50 transition-colors"
          >
            <div className="w-18 h-18 rounded-full bg-white/10 flex items-center justify-center">
              <Image className="w-10 h-10 text-white/60" />
            </div>
            <span className="text-base text-white/70 font-medium">Select from Gallery</span>
            <span className="text-xs text-white/40 text-center px-5">
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
            <div className="flex-1 relative rounded-xl overflow-hidden bg-[var(--color-cream)]">
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
                className="absolute bottom-2 right-2 p-1.5 bg-white/90 rounded-full"
              >
                <RotateCcw className="w-3 h-3 text-[var(--color-charcoal)]" />
              </button>
            </div>
            
            {/* Back preview or add button */}
            {backImage ? (
              <div className="flex-1 relative rounded-xl overflow-hidden bg-[var(--color-cream)]">
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
                  className="absolute bottom-2 right-2 p-1.5 bg-white/90 rounded-full"
                >
                  <RotateCcw className="w-3 h-3 text-[var(--color-charcoal)]" />
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
                useGhostMannequin ? 'bg-[var(--color-terracotta)]/20' : 'bg-white/10'
              }`}
            >
              <div className="flex items-center gap-2">
                <Sparkles className={`w-4 h-4 ${useGhostMannequin ? 'text-[var(--color-terracotta)]' : 'text-white/50'}`} />
                <span className="text-xs text-white">AI Ghost Mannequin</span>
              </div>
              <div className={`w-8 h-5 rounded-full transition-colors ${useGhostMannequin ? 'bg-[var(--color-terracotta)]' : 'bg-white/30'}`}>
                <div className={`w-4 h-4 rounded-full bg-white mt-0.5 transition-transform ${useGhostMannequin ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
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
      <div className="flex-1 relative rounded-2xl overflow-hidden bg-black mx-4 my-2">
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
        <div className="absolute top-3 left-3 px-2 py-1 bg-[var(--color-terracotta)] rounded-lg">
          <span className="text-[10px] text-white font-medium uppercase">{captureMode}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-charcoal)] safe-top safe-bottom overflow-y-auto">
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

      <div className="flex-1 flex flex-col page-container">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3">
          <button
            onClick={inputMode === INPUT_MODES.SELECT ? () => navigate('/') : goBackToSelect}
            className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center text-white"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          
          <h1 className="text-base font-semibold text-white">
            {inputMode === INPUT_MODES.SELECT ? 'Add to Wardrobe' : 
             inputMode === INPUT_MODES.UPLOAD ? 'Upload Clothes' : 'Capture Clothes'}
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

        {/* Mode Selection / Camera / Upload View */}
        {inputMode === INPUT_MODES.SELECT && renderModeSelect()}
        {inputMode === INPUT_MODES.UPLOAD && renderUploadView()}
        {inputMode === INPUT_MODES.CAPTURE && renderCaptureView()}

        {/* Category Selection - only for capture mode */}
        {inputMode === INPUT_MODES.CAPTURE && (
          <div className="px-5 py-4">
            <p className="text-white/60 text-sm mb-3 text-center">
              What type of clothing is this?
            </p>
            <div className="flex justify-center gap-3">
              {categories.map(cat => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`flex flex-col items-center gap-1 px-4 py-2.5 rounded-xl transition-all ${
                    selectedCategory === cat.id
                      ? 'bg-[var(--color-terracotta)] text-white'
                      : 'bg-white/10 text-white/70 hover:bg-white/20'
                  }`}
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
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-white/10 text-white rounded-xl font-medium text-sm"
              >
                <RotateCcw className="w-4 h-4" />
                Change
              </button>
              <button
                onClick={handleUploadProcess}
                disabled={isLoading}
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-[var(--color-terracotta)] text-white rounded-xl font-medium text-sm disabled:opacity-50"
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
                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-white/10 text-white rounded-xl font-medium text-sm"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Start Over
                  </button>
                  <button
                    onClick={handleConfirm}
                    disabled={isLoading}
                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-[var(--color-terracotta)] text-white rounded-xl font-medium text-sm disabled:opacity-50"
                  >
                    <Check className="w-4 h-4" />
                    Process
                  </button>
                </div>
              ) : captureMode === 'back' ? (
                <div className="flex gap-2">
                  <button
                    onClick={handleSkipBack}
                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-white/10 text-white rounded-xl font-medium text-sm"
                  >
                    Skip Back
                  </button>
                  <button
                    onClick={triggerCapture}
                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-[var(--color-terracotta)] text-white rounded-xl font-medium text-sm"
                  >
                    <Camera className="w-4 h-4" />
                    Capture Back
                  </button>
                </div>
              ) : (
                <button
                  onClick={triggerCapture}
                  className="w-full flex items-center justify-center gap-2 py-3 bg-[var(--color-terracotta)] text-white rounded-xl font-medium text-sm transition-all active:scale-98"
                >
                  <Camera className="w-4 h-4" />
                  Take Front Photo
                </button>
              )}
            </>
          )}
        </div>
      </div>
      
      {/* Bottom Navigation */}
      <BottomNav />
    </div>
  )
}
