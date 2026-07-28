import { Fragment } from 'react'
import { Icon } from './Icon'
import { EvidenceHover } from './EvidenceTooltip'
import { cellText, finRowItems, hasRatioRow, ratioValue } from '../finTable'
import type { CaseKey, FinTable } from '../finTable'
import type { ExtractedItem } from '../types'

/**
 * 財務情報の統合テーブル（読み取り専用）。
 * 概要タブと、ストレス仮説タブの「財務データを見る」サイドパネルで共用する。
 */
export function FinTableView({ fin, onCellClick, highlightLabels }: {
  fin: FinTable
  /** セルクリック時の遷移（概要タブ→事業・財務タブ）。省略時はクリック不可 */
  onCellClick?: () => void
  /** アンバーで強調する行ラベル（シナリオのストレス対象KPI等） */
  highlightLabels?: string[]
}) {
  // 「新規採用人数」と「新規採用数」、「採用単価CPA」と「採用CPA」のような表記揺れを
  // 吸収するため、片方がもう片方の部分列（文字順を保った部分文字）かで照合する
  const isSubseq = (a: string, b: string) => {
    let i = 0
    for (const ch of b) if (ch === a[i]) i++
    return i === a.length
  }
  const isHighlight = (label: string) =>
    highlightLabels?.some((l) => l.length >= 2 && (isSubseq(l, label) || isSubseq(label, l))) ?? false

  const finCell = (item: ExtractedItem | undefined, y: string, first: boolean) => {
    const v = item?.effective_values?.[y]
    return (
      <td
        key={y}
        onClick={item && onCellClick ? onCellClick : undefined}
        className={`px-2 py-1.5 text-right ${first ? 'border-l border-surface-container-high' : ''} ${
          item && onCellClick ? 'cursor-pointer hover:bg-primary-fixed/30' : ''
        } ${item && item.status !== 'confirmed' ? 'bg-amber-50/70' : ''}`}
      >
        {v != null && item
          ? (
            <EvidenceHover evidence={item.evidence}>
              <span className="font-data-tabular">{cellText(item, v)}</span>
            </EvidenceHover>
          )
          : v != null
            ? <span className="font-data-tabular">{v.toLocaleString()}</span>
            : <span className="text-outline-variant">－</span>}
      </td>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="border-b border-surface-container-high bg-surface-container-low/30 text-[11px] text-on-surface-variant">
            <th className="w-8 px-1 py-1.5" />
            <th className="min-w-[110px] px-2 py-1.5 text-left font-medium">項目（百万円）</th>
            {fin.yearsAct.length > 0 && (
              <th colSpan={fin.yearsAct.length} className="border-l border-surface-container-high px-2 py-1.5 text-center font-bold">
                確定財務
              </th>
            )}
            {fin.yearsBase.length > 0 && (
              <th colSpan={fin.yearsBase.length} className="border-l border-surface-container-high px-2 py-1.5 text-center font-bold">
                ベースケース
              </th>
            )}
            {fin.yearsSponsor.length > 0 && (
              <th colSpan={fin.yearsSponsor.length} className="border-l border-surface-container-high px-2 py-1.5 text-center font-bold">
                スポンサーケース
              </th>
            )}
          </tr>
          <tr className="border-b border-surface-container-high text-[11px] text-on-surface-variant">
            <th /><th />
            {fin.yearsAct.map((y, i) => (
              <th key={`a-${y}`} className={`px-2 py-1 text-right font-medium ${i === 0 ? 'border-l border-surface-container-high' : ''}`}>{y}</th>
            ))}
            {fin.yearsBase.map((y, i) => (
              <th key={`b-${y}`} className={`px-2 py-1 text-right font-medium ${i === 0 ? 'border-l border-surface-container-high' : ''}`}>{y}</th>
            ))}
            {fin.yearsSponsor.map((y, i) => (
              <th key={`s-${y}`} className={`px-2 py-1 text-right font-medium ${i === 0 ? 'border-l border-surface-container-high' : ''}`}>{y}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {fin.grouped.map(([group, rows]) =>
            rows.map((r, ri) => {
              const rowItems = finRowItems(r)
              const anyUnconfirmed = rowItems.some((it) => it.status !== 'confirmed')
              const hl = isHighlight(r.label)
              const ratioCell = (c: CaseKey, y: string, first: boolean) => (
                <td key={y} className={`px-2 py-1 text-right ${first ? 'border-l border-surface-container-high' : ''}`}>
                  <span className="font-data-tabular text-[11px] text-outline">{ratioValue(fin, r, c, y) ?? ''}</span>
                </td>
              )
              const groupSpan = rows.length + rows.filter(hasRatioRow).length
              return (
                <Fragment key={r.metric}>
                <tr className={`border-b border-surface-container-low last:border-0 ${hl ? 'bg-amber-50/60' : ''}`}>
                  {ri === 0 && (
                    <td
                      rowSpan={groupSpan}
                      className="w-8 border-r border-surface-container-high bg-surface-container-low/40 px-1 py-2 text-center align-middle text-[11px] font-bold text-on-surface-variant"
                      style={{ writingMode: 'vertical-rl' }}
                    >
                      {group}
                    </td>
                  )}
                  <td className="whitespace-nowrap px-2 py-1.5 font-medium">
                    {hl
                      ? <span className="rounded bg-amber-100 px-1 text-amber-900">{r.label}</span>
                      : r.label}
                    {anyUnconfirmed && <span className="ml-1 align-middle text-amber-600" title="未確定の値があります">●</span>}
                    {rowItems.some((it) => it.mismatch) && (
                      <Icon name="warning" className="ml-1 align-middle text-[13px] text-amber-600" />
                    )}
                  </td>
                  {fin.yearsAct.map((y, i) => finCell(r.kpiItem ?? r.items.act, y, i === 0))}
                  {fin.yearsBase.map((y, i) => finCell(r.kpiItem ?? r.items.base, y, i === 0))}
                  {fin.yearsSponsor.map((y, i) => finCell(r.kpiItem ? undefined : r.items.sponsor, y, i === 0))}
                </tr>
                {hasRatioRow(r) && (
                  <tr className="border-b border-surface-container-low">
                    <td className="px-2 py-1 pl-6 text-[11px] text-outline">同率</td>
                    {fin.yearsAct.map((y, i) => ratioCell('act', y, i === 0))}
                    {fin.yearsBase.map((y, i) => ratioCell('base', y, i === 0))}
                    {fin.yearsSponsor.map((y, i) => ratioCell('sponsor', y, i === 0))}
                  </tr>
                )}
                </Fragment>
              )
            }),
          )}
        </tbody>
      </table>
    </div>
  )
}
