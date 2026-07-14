import type { ReactNode } from 'react'
import { Icon } from './Icon'
import type { Evidence } from '../types'

/** 根拠3点セット（①参照ファイル ②箇所 ③抽出の論理）の表示。 */
export function EvidenceBlock({ evidence }: { evidence: Evidence }) {
  return (
    <div className="space-y-3">
      <div>
        <div className="text-[11px] font-medium text-outline">① 参照ファイル</div>
        <div className="mt-1 flex items-center gap-1.5 rounded border border-surface-container-high bg-surface-container-low/60 px-2.5 py-1.5 text-[12px]">
          <Icon name={evidence.file.endsWith('.pdf') ? 'picture_as_pdf' : 'table_chart'} className="text-[16px] text-primary-container" />
          <span className="break-all font-medium">{evidence.file}</span>
        </div>
      </div>
      <div>
        <div className="text-[11px] font-medium text-outline">② 箇所</div>
        <div className="mt-1 text-[12px] font-medium">{evidence.location}</div>
        {evidence.quote && (
          <blockquote className="mt-1.5 rounded border-l-2 border-primary-container bg-surface-container-low/60 px-3 py-2 text-[12px] leading-relaxed text-on-surface-variant">
            「{evidence.quote}」
          </blockquote>
        )}
      </div>
      <div>
        <div className="text-[11px] font-medium text-outline">③ 抽出の論理</div>
        <p className="mt-1 text-[12px] leading-relaxed text-on-surface-variant">{evidence.logic}</p>
      </div>
    </div>
  )
}

/** 右側スライドパネルの枠。 */
export function SlidePanel({ title, onClose, children, footer }: {
  title: ReactNode
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="animate-slide-in absolute right-0 top-0 flex h-full w-[420px] flex-col border-l border-surface-container-high bg-white">
        <div className="flex items-center justify-between border-b border-surface-container-high px-4 py-3">
          <div className="text-[14px] font-bold">{title}</div>
          <button onClick={onClose} className="rounded p-1 hover:bg-surface-container-low">
            <Icon name="close" className="text-[20px] text-outline" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
        {footer && <div className="border-t border-surface-container-high p-3">{footer}</div>}
      </div>
    </div>
  )
}
