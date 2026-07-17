import { createContext, useContext } from 'react'
import type { ReactNode } from 'react'
import { Icon } from './Icon'
import type { Evidence } from '../types'

/** 根拠パネルから参照元ファイルを開くための解決情報。DealDetail が提供する。 */
export const DocumentLinkContext = createContext<{
  dealId: number
  documents: { id: number; filename: string }[]
} | null>(null)

/** evidence.file（「（model_base）」等の注記付きのことがある）から資料URLを解決する。
 *  PDFは②箇所の「p.13」等からページアンカーを付ける。 */
function resolveFileUrl(
  ctx: { dealId: number; documents: { id: number; filename: string }[] } | null,
  file: string,
  location?: string,
): string | null {
  if (!ctx || !file) return null
  const doc = ctx.documents.find((d) => file.includes(d.filename) || d.filename.includes(file))
  if (!doc) return null
  let anchor = ''
  if (doc.filename.toLowerCase().endsWith('.pdf') && location) {
    const m = location.match(/p\.?\s*(\d+)/i)
    if (m) anchor = `#page=${m[1]}`
  }
  return `/api/deals/${ctx.dealId}/documents/${doc.id}/file${anchor}`
}

/** 根拠3点セット（①参照ファイル ②箇所 ③抽出の論理）の表示。
 *  参照ファイルはクリックで実ファイルを開ける（PDF=該当ページ、Excel=ダウンロード）。 */
export function EvidenceBlock({ evidence }: { evidence: Evidence }) {
  const linkCtx = useContext(DocumentLinkContext)
  const url = resolveFileUrl(linkCtx, evidence.file, evidence.location)
  const isPdf = evidence.file.endsWith('.pdf')
  const inner = (
    <>
      <Icon name={isPdf ? 'picture_as_pdf' : 'table_chart'} className="text-[16px] text-primary-container" />
      <span className="break-all font-medium">{evidence.file}</span>
      {url && <Icon name="open_in_new" className="ml-auto shrink-0 text-[14px] text-primary-container" />}
    </>
  )
  return (
    <div className="space-y-3">
      <div>
        <div className="text-[11px] font-medium text-outline">① 参照ファイル</div>
        {url ? (
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            title={isPdf ? '参照元PDFを開く（該当ページ）' : '参照元Excelをダウンロード'}
            className="mt-1 flex items-center gap-1.5 rounded border border-surface-container-high bg-surface-container-low/60 px-2.5 py-1.5 text-[12px] transition-colors hover:border-primary-container hover:bg-primary-fixed/20"
          >
            {inner}
          </a>
        ) : (
          <div className="mt-1 flex items-center gap-1.5 rounded border border-surface-container-high bg-surface-container-low/60 px-2.5 py-1.5 text-[12px]">
            {inner}
          </div>
        )}
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
