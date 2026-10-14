import { useEffect, useState } from 'react'

/** Delay propagating `value` until it has been stable for `delayMs`. */
export function useDebouncedValue<T>(value: T, delayMs = 100): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delayMs)
    return () => window.clearTimeout(id)
  }, [value, delayMs])

  return debounced
}
