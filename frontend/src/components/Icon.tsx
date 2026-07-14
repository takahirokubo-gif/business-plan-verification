export function Icon({ name, className = '', fill = false }: {
  name: string
  className?: string
  fill?: boolean
}) {
  return (
    <span
      className={`material-symbols-outlined select-none leading-none ${fill ? 'icon-fill' : ''} ${className}`}
      aria-hidden
    >
      {name}
    </span>
  )
}
