import { Shirt, Trash2 } from 'lucide-react'

export default function WardrobeGrid({ 
  garments, 
  deleteMode = false, 
  onDelete,
  onSelect,
  selectedId 
}) {
  if (garments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="w-16 h-16 rounded-full bg-[var(--color-warm-gray)]/10 flex items-center justify-center mb-4 animate-float">
          <Shirt className="w-8 h-8 text-[var(--color-warm-gray)]" />
        </div>
        <p className="text-sm text-[var(--color-warm-gray)]">
          No items in this category
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-3">
      {garments.map((garment, index) => (
        <GarmentCard
          key={garment.id}
          garment={garment}
          index={index}
          deleteMode={deleteMode}
          onDelete={onDelete}
          onSelect={onSelect}
          isSelected={selectedId === garment.id}
        />
      ))}
    </div>
  )
}

function GarmentCard({ 
  garment, 
  index, 
  deleteMode, 
  onDelete, 
  onSelect,
  isSelected 
}) {
  const handleClick = () => {
    if (deleteMode && onDelete) {
      onDelete(garment.id)
    } else if (onSelect) {
      onSelect(garment)
    }
  }

  return (
    <button
      onClick={handleClick}
      className={`
        relative aspect-square rounded-2xl overflow-hidden bg-white shadow-sm 
        animate-fade-in transition-all
        ${deleteMode ? 'animate-pulse-soft' : ''}
        ${isSelected ? 'ring-2 ring-[var(--color-terracotta)] ring-offset-2' : ''}
      `}
      style={{ animationDelay: `${(index % 5) * 0.1}s` }}
    >
      <img
        src={garment.url}
        alt={`${garment.category} garment`}
        className="w-full h-full object-contain p-2"
        loading="lazy"
      />
      
      {/* Category badge */}
      <div className="absolute bottom-1 left-1 px-2 py-0.5 bg-[var(--color-charcoal)]/60 rounded-full">
        <span className="text-[10px] text-white capitalize">
          {garment.category}
        </span>
      </div>
      
      {/* Delete overlay */}
      {deleteMode && (
        <div className="absolute inset-0 bg-[var(--color-terracotta)]/80 flex items-center justify-center">
          <Trash2 className="w-8 h-8 text-white" />
        </div>
      )}
    </button>
  )
}





