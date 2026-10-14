type FullscreenButtonProps = {
  active: boolean
  onToggle: () => void
}

export function FullscreenButton({ active, onToggle }: FullscreenButtonProps) {
  return (
    <button
      type="button"
      className="fullscreen-btn"
      onClick={onToggle}
      title={active ? 'Exit fullscreen (Esc)' : 'Fullscreen'}
      aria-label={active ? 'Exit fullscreen' : 'Enter fullscreen'}
    >
      {active ? (
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
          <path
            fill="currentColor"
            d="M5 1H1v4h1.5V2.5H5V1zm8 0H9v1.5h2.5V5H13V1zM2.5 9H1v4h4v-1.5H2.5V9zM13 9h-1.5v2.5H9V13h4V9z"
          />
        </svg>
      ) : (
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
          <path
            fill="currentColor"
            d="M1 1h4v1.5H2.5V5H1V1zm8 0h4v4h-1.5V2.5H9V1zM1 9h1.5v2.5H5V13H1V9zm11.5 0H13v4H9v-1.5h2.5V9z"
          />
        </svg>
      )}
      <span>{active ? 'Exit' : 'Full'}</span>
    </button>
  )
}
