import type { ReactNode } from 'react'

export function ConfirmDialog({ open, title, children, confirmLabel = 'OK', cancelLabel = 'キャンセル', onConfirm, onCancel, danger = false }: {
  open: boolean
  title: string
  children?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  onConfirm: () => void
  onCancel: () => void
  danger?: boolean
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="card w-[440px] p-5 shadow-xl">
        <div className="text-[15px] font-bold">{title}</div>
        {children && <div className="mt-3 text-[13px] text-on-surface-variant">{children}</div>}
        <div className="mt-5 flex justify-end gap-2">
          <button className="btn-secondary" onClick={onCancel}>{cancelLabel}</button>
          <button
            className={danger ? 'btn-primary !bg-error hover:!bg-error/90' : 'btn-primary'}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
