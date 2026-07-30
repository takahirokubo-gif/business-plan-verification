import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api'
import { Icon } from './Icon'
import type { DocumentPeek, Evidence } from '../types'

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
): { url: string; isPdf: boolean; page?: number; dealId: number; docId: number } | null {
  if (!ctx || !file) return null
  const doc = ctx.documents.find((d) => file.includes(d.filename) || d.filename.includes(file))
  if (!doc) return null
  const isPdf = doc.filename.toLowerCase().endsWith('.pdf')
  let page: number | undefined
  if (isPdf && location) {
    const m = location.match(/p\.?\s*(\d+)/i)
    if (m) page = Number(m[1])
  }
  const base = `/api/deals/${ctx.dealId}/documents/${doc.id}/file`
  return {
    url: page ? `${base}#page=${page}` : base,
    isPdf, page, dealId: ctx.dealId, docId: doc.id,
  }
}

/** Excel根拠のセル周辺抜粋（該当セルを強調した小さな表）。 */
function SheetPeek({ dealId, docId, location }: {
  dealId: number; docId: number; location: string
}) {
  const [peek, setPeek] = useState<DocumentPeek | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let alive = true
    setPeek(null)
    setError('')
    api.documentPeek(dealId, docId, location)
      .then((d) => { if (alive) setPeek(d) })
      .catch((e) => { if (alive) setError((e as Error).message) })
    return () => { alive = false }
  }, [dealId, docId, location])

  if (error) {
    return <div className="p-2 text-[11px] text-outline">該当箇所の抜粋を取得できませんでした（{error}）</div>
  }
  if (!peek) return <div className="p-2 text-[11px] text-outline">抜粋を読み込んでいます…</div>
  return (
    <div className="overflow-x-auto p-1.5">
      <table className="w-full border-collapse text-[11px]">
        <thead>
          <tr className="text-outline">
            <th className="border border-surface-container-high bg-surface-container-low px-1 py-0.5 text-left">
              {peek.sheet}
            </th>
            {peek.columns.map((c) => (
              <th key={c} className="border border-surface-container-high bg-surface-container-low px-1 py-0.5 text-right font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {peek.rows.map((r) => (
            <tr key={r.row}>
              <td className="max-w-[140px] truncate border border-surface-container-high bg-surface-container-low/60 px-1 py-0.5">
                <span className="text-outline">{r.row}</span>
                {r.label && <span className="ml-1">{r.label}</span>}
              </td>
              {r.cells.map((c) => (
                <td
                  key={c.ref}
                  title={c.formula ? `${c.ref}: ${c.formula}` : c.ref}
                  className={`whitespace-nowrap border border-surface-container-high px-1 py-0.5 text-right font-data-tabular ${
                    c.target ? 'bg-amber-100 font-bold text-amber-900' : ''
                  }`}
                >
                  {typeof c.value === 'number' ? c.value.toLocaleString() : (c.value ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-1 px-1 text-[10px] text-outline">
        黄色＝根拠セル（{peek.target}）。セルにカーソルを合わせると数式が見られます。
      </div>
    </div>
  )
}

/** 根拠3点セット（①参照ファイル ②箇所 ③抽出の論理）の表示。
 *  PDFはその場でインラインプレビュー（該当ページ）を開ける。別タブでも開ける。
 *  Excelはダウンロード（ブラウザで表示できないため）。 */
export function EvidenceBlock({ evidence }: { evidence: Evidence }) {
  const linkCtx = useContext(DocumentLinkContext)
  const link = resolveFileUrl(linkCtx, evidence.file, evidence.location)
  const isPdf = link?.isPdf ?? evidence.file.toLowerCase().endsWith('.pdf')
  // Excelは「シート!セル」の抜粋を、PDFは該当ページのプレビューをその場で開ける。
  // Excelは既定で抜粋を開く（ブラウザで開けず中身が見えないため）
  // 「PL!G9」形式と「PLシート C9:E9」形式の両方をセル参照として扱う
  const hasSheetRef = !isPdf
    && /(!\s*\$?[A-Z]{1,2}\$?\d+|シート\s*\$?[A-Z]{1,2}\$?\d+)/.test(evidence.location ?? '')
  const [preview, setPreview] = useState(hasSheetRef)
  return (
    <div className="space-y-3">
      <div>
        <div className="text-[11px] font-medium text-outline">① 参照ファイル</div>
        <div className="mt-1 rounded border border-surface-container-high bg-surface-container-low/60">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 text-[12px]">
            <Icon name={isPdf ? 'picture_as_pdf' : 'table_chart'} className="shrink-0 text-[16px] text-primary-container" />
            <span className="break-all font-medium">{evidence.file}</span>
          </div>
          {link && (
            <div className="flex items-center gap-1.5 border-t border-surface-container-high px-2.5 py-1.5">
              {(isPdf || hasSheetRef) && (
                <button
                  className="flex items-center gap-1 rounded border border-primary-container/40 px-2 py-0.5 text-[11px] font-medium text-primary-container hover:bg-primary-fixed/30"
                  onClick={() => setPreview((v) => !v)}
                >
                  <Icon name={preview ? 'visibility_off' : 'visibility'} className="text-[14px]" />
                  {preview
                    ? '閉じる'
                    : isPdf
                      ? `ここでプレビュー${link.page ? `（p.${link.page}）` : ''}`
                      : '該当セル周辺を見る'}
                </button>
              )}
              <a
                href={link.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 rounded border border-surface-container-high px-2 py-0.5 text-[11px] text-on-surface-variant hover:border-primary-container hover:text-primary-container"
                title={isPdf ? '別タブでPDFを開く' : 'Excelをダウンロード（ブラウザでは開けません）'}
              >
                <Icon name={isPdf ? 'open_in_new' : 'download'} className="text-[14px]" />
                {isPdf ? '別タブで開く' : 'ダウンロード'}
              </a>
            </div>
          )}
          {preview && link && (
            <div className="border-t border-surface-container-high">
              {isPdf ? (
                /* 同一オリジンの /api 経由で埋め込む（別タブが開けない環境でも参照できる） */
                <iframe
                  src={link.url}
                  title={evidence.file}
                  className="m-1.5 h-[420px] w-[calc(100%-12px)] rounded border border-surface-container-high bg-white"
                />
              ) : (
                <SheetPeek dealId={link.dealId} docId={link.docId} location={evidence.location} />
              )}
            </div>
          )}
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

const PANEL_WIDTH_KEY = 'bpv.panelWidth'
const MIN_WIDTH = 360
const MAX_WIDTH = 1100

/** 右側スライドパネルの枠。左端をドラッグして幅を変えられる（幅は保持される）。 */
export function SlidePanel({ title, onClose, children, footer }: {
  title: ReactNode
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}) {
  const [width, setWidth] = useState(() => {
    const saved = Number(localStorage.getItem(PANEL_WIDTH_KEY))
    return saved >= MIN_WIDTH && saved <= MAX_WIDTH ? saved : 460
  })
  const dragging = useRef(false)

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return
      const next = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, window.innerWidth - e.clientX))
      setWidth(next)
    }
    const onUp = () => {
      if (!dragging.current) return
      dragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      setWidth((w) => { localStorage.setItem(PANEL_WIDTH_KEY, String(w)); return w })
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [])

  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div
        className="animate-slide-in absolute right-0 top-0 flex h-full flex-col border-l border-surface-container-high bg-white"
        style={{ width }}
      >
        {/* 幅変更ハンドル（左端をドラッグ） */}
        <div
          onMouseDown={onMouseDown}
          onDoubleClick={() => { setWidth(460); localStorage.setItem(PANEL_WIDTH_KEY, '460') }}
          title="ドラッグで幅を変更（ダブルクリックで既定幅）"
          className="group absolute inset-y-0 left-0 z-10 flex w-1.5 -translate-x-1/2 cursor-col-resize items-center justify-center"
        >
          <span className="h-10 w-1 rounded-full bg-outline-variant/60 group-hover:bg-primary-container" />
        </div>
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
