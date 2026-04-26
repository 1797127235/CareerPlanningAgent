import { motion } from 'framer-motion'

interface SealStampProps {
  text?: string
  size?: number
  color?: string
}

export function SealStamp({
  text = '归档',
  size = 72,
  color = 'var(--chestnut)',
}: SealStampProps) {
  return (
    <motion.div
      initial={{ scale: 0, rotate: -15, opacity: 0 }}
      animate={{ scale: 1, rotate: 0, opacity: 1 }}
      transition={{
        type: 'spring',
        stiffness: 400,
        damping: 12,
        delay: 0.3,
      }}
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      {/* 外圆 */}
      <svg width={size} height={size} className="absolute">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size / 2 - 4}
          fill="transparent"
          stroke={color}
          strokeWidth="2"
          strokeDasharray="6 3"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size / 2 - 8}
          fill="transparent"
          stroke={color}
          strokeWidth="1"
        />
      </svg>
      {/* 文字 */}
      <span
        className="font-sans text-[11px] font-bold tracking-[0.3em] uppercase"
        style={{ color }}
      >
        {text}
      </span>
      {/* 微妙阴影 */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          boxShadow: `0 2px 12px ${color}33, inset 0 1px 3px ${color}1a`,
        }}
      />
    </motion.div>
  )
}
