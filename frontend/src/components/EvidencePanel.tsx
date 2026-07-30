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
  if (!peek.rows?.length) {
    return (
      <div className="p-2 text-[11px] text-outline">
        該当セル（{peek.sheet}!{peek.target}）の周辺に値が見つかりませんでした。
      </div>
    )
  }
  return (
    <div className="overflow-x-auto p-1.5">
      <table className="w-full border-collapse text-[11px]">
        <thead>
          <tr className="text-outline">
            <th className="border border-surface-container-high bg-surface-container-low px-1 py-0.5 text-left">
              {peek.sheet}
            </th>
            {(peek.columns ?? []).map((c) => (
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
              {(r.cells ?? []).map((c) => (
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
  // パネルは開いたまま選択対象だけが変わる（再マウントされない）ため、
  // 対象が変わったら開閉状態を作り直す（前の対象の状態が残ると閉じられなくなる）
  useEffect(() => { setPreview(hasSheetRef) }, [evidence.file, evidence.location, hasSheetRef])
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
  /** 画面幅に収まる範囲へ丸める（保存値が現在の画面より広い場合の救済も兼ねる） */
  const clamp = (w: number) =>
    Math.min(Math.max(MIN_WIDTH, w), Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, window.innerWidth - 80)))

  const [width, setWidth] = useState(() => {
    const saved = Number(localStorage.getItem(PANEL_WIDTH_KEY))
    return clamp(saved > 0 ? saved : 460)
  })
  const widthRef = useRef(width)
  const dragging = useRef(false)

  const endDrag = useCallback(() => {
    if (!dragging.current) return
    dragging.current = false
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    localStorage.setItem(PANEL_WIDTH_KEY, String(widthRef.current))
  }, [])

  // ポインタイベント＋setPointerCapture で、iframe上や画面外で離しても
  // ドラッグ状態が残らないようにする（残るとテキスト選択不能になる）
  const onPointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragging.current = true
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [])

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging.current) return
    if (e.buttons === 0) { endDrag(); return }   // ボタンが離れていたら終了（取りこぼし対策）
    const next = clamp(window.innerWidth - e.clientX)
    widthRef.current = next
    setWidth(next)
  }, [endDrag])

  // 画面が狭くなった時にハンドルが画面外へ出ないよう追随させる
  useEffect(() => {
    const onResize = () => {
      const next = clamp(widthRef.current)
      widthRef.current = next
      setWidth(next)
    }
    window.addEventListener('resize', onResize)
    // ドラッグ中にアンマウントされてもカーソル・選択不可が残らないようにする
    return () => {
      window.removeEventListener('resize', onResize)
      dragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [])

  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div
        className="animate-slide-in absolute right-0 top-0 flex h-full flex-col border-l border-surface-container-high bg-white"
        style={{ width }}
      >
        {/* 幅変更ハンドル（左端をドラッグ／キーボードは矢印キー） */}
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="パネルの幅を変更"
          tabIndex={0}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          onLostPointerCapture={endDrag}
          onKeyDown={(e) => {
            const step = e.shiftKey ? 80 : 24
            if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
            e.preventDefault()
            const next = clamp(widthRef.current + (e.key === 'ArrowLeft' ? step : -step))
            widthRef.current = next
            setWidth(next)
            localStorage.setItem(PANEL_WIDTH_KEY, String(next))
          }}
          onDoubleClick={() => {
            const next = clamp(460)
            widthRef.current = next
            setWidth(next)
            localStorage.setItem(PANEL_WIDTH_KEY, String(next))
          }}
          title="ドラッグ（または矢印キー）で幅を変更・ダブルクリックで既定幅"
          className="group absolute inset-y-0 left-0 z-10 flex w-1.5 -translate-x-1/2 cursor-col-resize touch-none items-center justify-center focus:outline-none"
        >
          <span className="h-10 w-1 rounded-full bg-outline-variant/60 group-hover:bg-primary-container group-focus:bg-primary-container" />
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
