import { useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Icon } from './Icon'
import type { Evidence, EvidenceSnippet } from '../types'

/** ソースの抜粋イメージ。sheet＝該当セル周辺のミニ表、doc＝該当段落（強調付き） */
function SnippetView({ s }: { s: EvidenceSnippet }) {
  return (
    <div className="mt-2">
      {s.title && <div className="mb-1 text-[10.5px] font-medium text-outline">{s.title}</div>}
      {s.kind === 'sheet' && s.rows && (
        <div className="overflow-hidden rounded border border-outline-variant/60">
          {s.head && (
            <div className="flex bg-surface-container-low text-[10.5px] font-medium text-on-surface-variant">
              {s.head.map((h, i) => (
                <div key={i} className={`border-r border-outline-variant/40 px-1.5 py-0.5 last:border-r-0 ${i === 0 ? 'w-[104px] shrink-0' : 'flex-1 text-right'}`}>{h}</div>
              ))}
            </div>
          )}
          {s.rows.map((r, i) => (
            <div key={i} className={`flex border-t border-outline-variant/40 text-[10.5px] ${r.hl ? 'bg-primary-fixed/50 font-bold' : ''}`}>
              <div className="w-[104px] shrink-0 border-r border-outline-variant/40 px-1.5 py-0.5">{r.name}</div>
              {r.cells.map((c, j) => (
                <div key={j} className="font-data-tabular flex-1 border-r border-outline-variant/40 px-1.5 py-0.5 text-right last:border-r-0">{c}</div>
              ))}
            </div>
          ))}
          {s.formula && (
            <div className="break-all border-t border-outline-variant/40 bg-surface-container-low/60 px-1.5 py-1 font-mono text-[10px] leading-snug text-on-surface-variant">
              {s.formula}
            </div>
          )}
        </div>
      )}
      {s.kind === 'doc' && s.text && (
        <div className="rounded border border-outline-variant/60 bg-white px-2.5 py-2 text-[11px] leading-relaxed text-on-surface-variant">
          {s.hl && s.text.includes(s.hl)
            ? s.text.split(s.hl).flatMap((part, i, arr) =>
                i < arr.length - 1
                  ? [<span key={`p${i}`}>{part}</span>, <mark key={`h${i}`} className="rounded-sm bg-amber-100 px-0.5 font-medium text-on-surface">{s.hl}</mark>]
                  : [<span key={`p${i}`}>{part}</span>])
            : s.text}
        </div>
      )}
    </div>
  )
}

/**
 * ホバーで根拠（①ソース資料 ②該当箇所 ③抜粋）を吹き出し表示する。
 * - 対象要素を隠さないよう、要素の下（入らなければ上）に固定配置で表示する
 * - 表のoverflowにクリップされないよう body へポータル描画
 * - クリック操作（根拠パネルを開く等）を妨げないよう吹き出し自体はマウスを拾わない
 */
export function EvidenceHover({ evidence, children, className }: {
  evidence: Evidence | null | undefined
  children: React.ReactNode
  className?: string
}) {
  const [rect, setRect] = useState<DOMRect | null>(null)
  const [style, setStyle] = useState<React.CSSProperties>({ visibility: 'hidden' })
  const tipRef = useRef<HTMLDivElement>(null)
  const timer = useRef<number | undefined>(undefined)

  useLayoutEffect(() => {
    if (!rect || !tipRef.current) return
    const t = tipRef.current.getBoundingClientRect()
    const vw = window.innerWidth
    const vh = window.innerHeight
    const gap = 6
    // 既定は対象の直下。収まらない場合のみ直上（対象を隠さない）
    let top = rect.bottom + gap
    if (top + t.height > vh - 8 && rect.top - gap - t.height > 8) top = rect.top - gap - t.height
    let left = rect.left
    if (left + t.width > vw - 8) left = vw - 8 - t.width
    if (left < 8) left = 8
    setStyle({ position: 'fixed', top, left, zIndex: 60, visibility: 'visible' })
  }, [rect])

  if (!evidence) return <span className={className}>{children}</span>

  const show = (e: React.MouseEvent<HTMLSpanElement>) => {
    const el = e.currentTarget
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => {
      setStyle({ visibility: 'hidden' })
      setRect(el.getBoundingClientRect())
    }, 120)
  }
  const hide = () => {
    window.clearTimeout(timer.current)
    setRect(null)
    setStyle({ visibility: 'hidden' })
  }

  return (
    <span className={className} onMouseEnter={show} onMouseLeave={hide}>
      {children}
      {rect && createPortal(
        <div
          ref={tipRef}
          style={{ ...style, pointerEvents: 'none' }}
          className="w-[440px] max-w-[92vw] rounded border border-outline-variant bg-white p-3 shadow-lg"
        >
          {/* リード文：この値/記述が資料のどこから来ているかを言い切る */}
          <div className="flex items-start gap-1.5 text-[11.5px] leading-relaxed text-on-surface">
            <Icon
              name={evidence.file.endsWith('.pdf') ? 'picture_as_pdf' : 'table_chart'}
              className="mt-0.5 shrink-0 text-[14px] text-primary-container"
            />
            <span>
              <b>{evidence.file}</b> の <b>{evidence.location}</b>
              {evidence.snippet?.lead
                ?? (evidence.snippet
                  ? (evidence.snippet.kind === 'sheet'
                    ? (evidence.snippet.formula ? ' に次の数式が記載されています。' : ' にそのまま記載されています。')
                    : ' に次の記述があります。')
                  : evidence.file.endsWith('.pdf') ? ' に次の記述があります。' : ' に記載されています。')}
            </span>
          </div>
          {evidence.snippet ? (
            <SnippetView s={evidence.snippet} />
          ) : evidence.quote && (
            <div className="mt-2 whitespace-pre-line rounded-r border-l-2 border-primary-container/40 bg-surface-container-low/60 px-2.5 py-1.5 text-[11.5px] leading-relaxed text-on-surface-variant">
              「{evidence.quote}」
            </div>
          )}
          {evidence.logic && (
            <div className="mt-1.5 text-[10.5px] leading-relaxed text-outline">{evidence.logic}</div>
          )}
        </div>,
        document.body,
      )}
    </span>
  )
}
