import { useCallback, useEffect, useState } from 'react'

/** In-app panel fullscreen (CSS overlay). Esc exits; fires resize for R3F canvases. */
export function usePanelFullscreen() {
  const [active, setActive] = useState(false)

  const exit = useCallback(() => setActive(false), [])
  const toggle = useCallback(() => setActive((v) => !v), [])

  useEffect(() => {
    if (!active) return

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') exit()
    }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    // Let flex layouts / R3F Canvas pick up the new size
    requestAnimationFrame(() => window.dispatchEvent(new Event('resize')))

    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
      requestAnimationFrame(() => window.dispatchEvent(new Event('resize')))
    }
  }, [active, exit])

  return { active, toggle, exit }
}
