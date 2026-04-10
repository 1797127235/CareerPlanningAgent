import { useRef, useEffect } from 'react'

/**
 * Canvas background: a soft luminous orb drifting along a Lissajous path.
 */
export function SignatureHero() {
  const wrapRef = useRef<HTMLDivElement>(null)
  const cvRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const wrap = wrapRef.current
    const cv = cvRef.current
    if (!wrap || !cv) return

    const ctx = cv.getContext('2d')
    if (!ctx) return

    let animId = 0
    let t = 0
    let w = 0
    let h = 0

    function resize() {
      const dpr = window.devicePixelRatio || 1
      const rect = wrap!.getBoundingClientRect()
      w = rect.width
      h = rect.height
      cv!.width = w * dpr
      cv!.height = h * dpr
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    resize()

    function draw() {
      t += 0.005
      ctx!.clearRect(0, 0, w, h)

      const cx = w / 2
      const cy = h / 2
      const orbX = cx + Math.sin(t * 0.7) * w * 0.14
      const orbY = cy + Math.cos(t * 0.5) * h * 0.10
      const orbR = Math.min(w, h) * 0.20

      /* Outer glow */
      const g = ctx!.createRadialGradient(orbX, orbY, 0, orbX, orbY, orbR * 1.8)
      g.addColorStop(0, 'rgba(59,130,246,0.28)')
      g.addColorStop(0.35, 'rgba(59,130,246,0.12)')
      g.addColorStop(0.7, 'rgba(59,130,246,0.04)')
      g.addColorStop(1, 'rgba(59,130,246,0)')
      ctx!.fillStyle = g
      ctx!.fillRect(0, 0, w, h)

      /* Inner core */
      const c = ctx!.createRadialGradient(orbX, orbY, 0, orbX, orbY, orbR * 0.7)
      c.addColorStop(0, 'rgba(59,130,246,0.22)')
      c.addColorStop(0.5, 'rgba(59,130,246,0.08)')
      c.addColorStop(1, 'rgba(59,130,246,0)')
      ctx!.fillStyle = c
      ctx!.beginPath()
      ctx!.arc(orbX, orbY, orbR * 0.7, 0, Math.PI * 2)
      ctx!.fill()

      animId = requestAnimationFrame(draw)
    }

    draw()

    const ro = new ResizeObserver(resize)
    ro.observe(wrap)

    return () => {
      cancelAnimationFrame(animId)
      ro.disconnect()
    }
  }, [])

  return (
    <div ref={wrapRef} className="absolute inset-0 overflow-hidden pointer-events-none">
      <canvas ref={cvRef} />
    </div>
  )
}
