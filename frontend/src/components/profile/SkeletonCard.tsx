export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`glass p-6 ${className}`}>
      <div className="g-inner">
        <div className="h-4 w-24 bg-white/40 rounded animate-pulse mb-4" />
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-8 rounded-lg bg-white/40 animate-pulse" style={{ width: `${60 + i * 12}px` }} />
          ))}
        </div>
      </div>
    </div>
  )
}
