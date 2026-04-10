import { motion } from 'framer-motion'
import { SkeletonCard } from './SkeletonCard'

export function ProfileSkeleton() {
  return (
    <motion.div
      key="skeleton"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
    >
      {/* Top strip skeleton */}
      <div className="glass-static mb-4 px-6 py-5">
        <div className="g-inner flex items-center gap-8">
          <div className="flex flex-col gap-2">
            <div className="h-4 w-32 bg-white/40 rounded animate-pulse" />
            <div className="h-3 w-20 bg-white/40 rounded animate-pulse" />
          </div>
          <div className="flex gap-6">
            <div className="h-3 w-[120px] bg-white/40 rounded animate-pulse" />
            <div className="h-3 w-[120px] bg-white/40 rounded animate-pulse" />
          </div>
          <div className="flex-1 flex gap-4 justify-center">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="w-5 h-5 rounded-full bg-white/40 animate-pulse" />
            ))}
          </div>
        </div>
      </div>
      {/* Bento skeleton */}
      <div className="grid grid-cols-3 gap-4">
        <SkeletonCard className="col-span-2" />
        <SkeletonCard />
        <SkeletonCard className="col-span-2" />
        <SkeletonCard />
      </div>
    </motion.div>
  )
}
