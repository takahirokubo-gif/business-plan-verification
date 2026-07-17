import { useMemo, useState } from 'react'
import { api } from '../../api'
import { Icon } from '../../components/Icon'
import { EvidenceBlock, SlidePanel } from '../../components/EvidencePanel'
import { useUser } from '../../context/UserContext'
import type { DealFull, ExtractedItem, Mismatch } from '../../types'

const YEAR_ORDER = ['FY24', 'FY25', 'FY26', 'FY27', 'FY28', 'FY29', 'FY30', 'FY31']

/** 年度キーの表示順。既知のFY形式を先に、それ以外（'2027/3期' など実AIの表記）も
 *  捨てずに末尾へ昇順で並べる（キー形式が想定と違っても数値を必ず表示する）。 */
function sortYears(years: string[]): string[] {
  const known = YEAR_ORDER.filter((y) => years.includes(y))
  const unknown = years.filter((y) => !YEAR_ORDER.includes(y)).sort()
  return [...known, ...unknown]
}

/** mismatch のキー表記ゆれを吸収する（fixture形式と実AIの自由形式の両対応）。
 *  other_value が数値でない場合は「値の採用選択」は出せない（説明表示のみ）。 */
function normalizeMismatch(mm: Mismatch) {
  return {
    note: mm.note ?? mm.description ?? '',
    file: mm.other_file ?? mm.source_file ?? '',
    location: mm.other_location ?? mm.source_location ?? '',
    quote: mm.other_quote ?? mm.source_quote ?? '',
    otherValue: typeof mm.other_value === 'number' ? mm.other_value : null,
  }
}

/** 不整合の「値の採用選択」が必要な項目か（＝一括確定の対象外・個別確定が必要） */
function needsChoice(item: ExtractedItem): boolean {
  if (!item.mismatch) return false
  const mm = normalizeMismatch(item.mismatch)
  return mm.otherValue != null && Object.keys(item.effective_values ?? {}).length === 1
}

/** 一括確定のチェック対象にできる項目か。
 *  保留（held）は意図して止めた項目なので対象外（保留解除→個別確定を通す） */
function bulkSelectable(item: ExtractedItem): boolean {
  return item.status === 'proposed' && !needsChoice(item)
}

// ---- 財務情報の統合テーブル（過去実績・Base・Sponsorを横並び、PL/KPI/BS/CFを縦並び） ----

type CaseKey = 'act' | 'base' | 'sponsor'
type FinGroup = 'PL' | '重要KPI' | 'BS' | 'CF'

interface FinRow {
  metric: string
  label: string
  group: FinGroup
  items: Partial<Record<CaseKey, ExtractedItem>>
  kpiItem?: ExtractedItem // ケース区分のないKPI項目
}

const BS_METRICS = new Set(['cash', 'net_assets', 'debt', 'total_assets', 'goodwill', 'net_debt'])
const CF_METRICS = new Set(['fcf', 'op_cf', 'inv_cf', 'fin_cf', 'capex'])

function parseCaseKey(key: string): { case: CaseKey; metric: string } | null {
  const m = key.match(/^(act|base|sponsor)_(.+)$/)
  return m ? { case: m[1] as CaseKey, metric: m[2] } : null
}

/** 「売上高（実績）」「Adj. EBITDA―BaseCase」等からケース注記を除いた行ラベル */
function cleanMetricLabel(label: string): string {
  return label
    .replace(/（実績）|（実績値）|（Base.?ケース.*?）|（Sponsor.?ケース.*?）|（ベースケース.*?）|（スポンサーケース.*?）/g, '')
    .replace(/[―ー-]\s*(Base|Sponsor)\s*Case.*$/i, '')
    .trim()
}

function buildFinTable(items: ExtractedItem[]) {
  const rows: FinRow[] = []
  const rowByMetric = new Map<string, FinRow>()
  const tableIds = new Set<number>()
  for (const it of items) {
    if (!it.values) continue
    const ck = parseCaseKey(it.key)
    if (ck) {
      let row = rowByMetric.get(ck.metric)
      if (!row) {
        const group: FinGroup = BS_METRICS.has(ck.metric) ? 'BS' : CF_METRICS.has(ck.metric) ? 'CF' : 'PL'
        row = { metric: ck.metric, label: cleanMetricLabel(it.label), group, items: {} }
        rowByMetric.set(ck.metric, row)
        rows.push(row)
      }
      row.items[ck.case] = it
      tableIds.add(it.id)
    } else if (it.key.startsWith('kpi_') || it.section.includes('KPI')) {
      rows.push({ metric: it.key, label: it.label, group: '重要KPI', items: {}, kpiItem: it })
      tableIds.add(it.id)
    }
  }
  // sponsor_equity（ストラクチャー項目）等の誤分類を防ぐ：
  // act/base のどちらにも存在しない sponsor 単独指標はケース行にしない（元のセクションに残す）
  for (let i = rows.length - 1; i >= 0; i--) {
    const r = rows[i]
    if (!r.kpiItem && !r.items.act && !r.items.base && r.items.sponsor) {
      tableIds.delete(r.items.sponsor.id)
      rowByMetric.delete(r.metric)
      rows.splice(i, 1)
    }
  }

  const yearsOf = (pick: (r: FinRow) => ExtractedItem | undefined) =>
    sortYears([...new Set(rows.flatMap((r) => Object.keys(pick(r)?.effective_values ?? {})))])
  const yearsAct = yearsOf((r) => r.items.act)
  const yearsBase = sortYears([...new Set(rows.flatMap((r) =>
    Object.keys(r.items.base?.effective_values ?? {}).concat(Object.keys(r.kpiItem?.effective_values ?? {}))))])
    .filter((y) => !yearsAct.includes(y) || rows.some((r) => r.items.base?.effective_values?.[y] != null))
  const yearsSponsor = yearsOf((r) => r.items.sponsor)
  const groups: FinGroup[] = ['PL', '重要KPI', 'BS', 'CF']
  const grouped = groups
    .map((g) => [g, rows.filter((r) => r.group === g)] as const)
    .filter(([, rs]) => rs.length > 0)
  return { grouped, yearsAct, yearsBase, yearsSponsor, tableIds, hasRows: rows.length > 0 }
}

function StatusIcon({ item }: { item: ExtractedItem }) {
  if (item.status === 'confirmed') {
    return (
      <span className="inline-flex items-center gap-1 text-green-700">
        <Icon name="check_circle" className="text-[15px]" fill />
        <span className="text-[11px] font-medium">{item.edited ? '修正済' : '確定'}</span>
      </span>
    )
  }
  if (item.status === 'held') {
    return (
      <span className="inline-flex items-center gap-1 text-outline">
        <Icon name="pause_circle" className="text-[15px]" />
        <span className="text-[11px] font-medium">保留</span>
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 text-amber-700">
      <Icon name="radio_button_unchecked" className="text-[15px]" />
      <span className="text-[11px] font-medium">未確定</span>
    </span>
  )
}

export function NumbersTab({ full, refresh, dealId }: {
  full: DealFull
  refresh: () => Promise<void>
  dealId: number
}) {
  const { userKey } = useUser()
  const [selected, setSelected] = useState<ExtractedItem | null>(null)
  const [onlyPending, setOnlyPending] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editValues, setEditValues] = useState<Record<string, string>>({})
  const [editText, setEditText] = useState('')
  const [mismatchChoice, setMismatchChoice] = useState<'model' | 'dd' | null>(null)
  const [resolutionNote, setResolutionNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [checked, setChecked] = useState<Set<number>>(new Set())

  const items = full.items
  const progress = full.deal.progress

  // 財務情報テーブル（act/base/sponsor＋KPIの数値項目を統合）
  const fin = useMemo(() => buildFinTable(items), [items])

  // 残りの項目（定性情報・ストラクチャー等）は従来のセクション表示
  const sections = useMemo(() => {
    const map = new Map<string, ExtractedItem[]>()
    for (const it of items) {
      if (fin.tableIds.has(it.id)) continue
      if (onlyPending && it.status === 'confirmed') continue
      if (!map.has(it.section)) map.set(it.section, [])
      map.get(it.section)!.push(it)
    }
    return [...map.entries()]
  }, [items, onlyPending, fin])

  const openItem = (item: ExtractedItem) => {
    setSelected(item)
    setEditMode(false)
    setMismatchChoice(null)
    setResolutionNote(item.resolution_note ?? '')
    setEditText(item.effective_text ?? '')
    const vals: Record<string, string> = {}
    for (const [y, v] of Object.entries(item.effective_values ?? {})) vals[y] = String(v)
    setEditValues(vals)
  }

  const doAction = async (action: string, extra: Record<string, unknown> = {}) => {
    if (!selected || busy) return
    setBusy(true)
    try {
      await api.itemAction(dealId, selected.id, { action, user: userKey, ...extra })
      await refresh()
      // 個別に処理した項目は一括確定の選択から外す
      setChecked((prev) => {
        const next = new Set(prev)
        next.delete(selected.id)
        return next
      })
      setSelected(null)
    } finally {
      setBusy(false)
    }
  }

  const toggleCheck = (id: number) => {
    setChecked((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSection = (sectionItems: ExtractedItem[]) => {
    const targets = sectionItems.filter(bulkSelectable)
    const allChecked = targets.length > 0 && targets.every((it) => checked.has(it.id))
    setChecked((prev) => {
      const next = new Set(prev)
      for (const it of targets) {
        if (allChecked) next.delete(it.id)
        else next.add(it.id)
      }
      return next
    })
  }

  const bulkConfirm = async () => {
    if (checked.size === 0 || busy) return
    setBusy(true)
    try {
      await api.itemsBulkConfirm(dealId, [...checked], userKey)
      await refresh()
      setChecked(new Set())
      setSelected(null)
    } finally {
      setBusy(false)
    }
  }

  // 不整合の正規化と「値の採用選択」の可否。
  // 選択できるのは相手側が数値で、対象が単一年度の値のときのみ（それ以外は説明表示＋そのまま確定）
  const mm = selected?.mismatch ? normalizeMismatch(selected.mismatch) : null
  const mmYears = Object.keys(selected?.effective_values ?? {})
  const mmYear = mmYears.length === 1 ? mmYears[0] : null
  const mmChoiceAvailable = mm != null && mm.otherValue != null && mmYear != null

  const confirmAsIs = () => {
    const extra: Record<string, unknown> = {}
    if (mmChoiceAvailable && mismatchChoice) {
      const model = selected?.effective_values?.[mmYear]
      const dd = mm.otherValue as number
      extra.values = { [mmYear]: mismatchChoice === 'model' ? model : dd }
      extra.resolution_note = resolutionNote
        || (mismatchChoice === 'model'
          ? `モデル値${model?.toLocaleString()}を採用（財務DD値${dd.toLocaleString()}との差異はPPAで確定予定）`
          : `財務DD値${dd.toLocaleString()}を採用（保守的な評価を優先）`)
    } else if (selected?.mismatch && resolutionNote) {
      extra.resolution_note = resolutionNote
    }
    doAction('confirm', extra)
  }

  const confirmEdited = () => {
    const extra: Record<string, unknown> = {}
    if (selected?.values) {
      const vals: Record<string, number> = {}
      for (const [y, v] of Object.entries(editValues)) {
        const n = Number(v)
        if (!Number.isNaN(n)) vals[y] = n
      }
      extra.values = vals
    }
    if (selected?.text_value != null) extra.text_value = editText
    if (resolutionNote) extra.resolution_note = resolutionNote
    doAction('confirm', extra)
  }

  const USER_NAMES: Record<string, string> = { tanaka: '田中', sato: '佐藤', takahashi: '高橋' }
  const deal = full.deal
  const basicInfo: [string, string][] = [
    // 旧ヘッダー行の情報（スキーム・当事者・ストラクチャー概要）はここに集約
    ['案件種別', deal.deal_type ?? '－'],
    ['借入人（SPC）', deal.borrower || '－'],
    ['対象会社', deal.target || '－'],
    ['スポンサー', deal.sponsor ?? '－'],
    ['対象会社の業種', deal.industry ?? '－'],
    ['クローズ予定日', deal.close_date?.replaceAll('-', '/') ?? '－'],
    ['EV（買収総額）', deal.ev_mm != null ? `${deal.ev_mm.toLocaleString()}百万円` : '－'],
    ['シニアローン', deal.senior_mm != null
      ? `${deal.senior_mm.toLocaleString()}百万円${deal.our_commitment_mm != null ? `（本行 ${deal.our_commitment_mm.toLocaleString()}百万円）` : ''}`
      : '－'],
    ['エクイティ', deal.equity_mm != null ? `${deal.equity_mm.toLocaleString()}百万円` : '－'],
    ['レバレッジ／LTV', deal.initial_leverage != null ? `${deal.initial_leverage}x／${deal.ltv_pct}%` : '－'],
    ['ローン期間', deal.tenor_years != null ? `${deal.tenor_years}年` : '－'],
    ['スポンサー提示EBITDA（速報）', deal.sponsor_ebitda_mm != null ? `${deal.sponsor_ebitda_mm.toLocaleString()}百万円` : '－'],
    ['次回審査相談日', deal.next_meeting_date?.replaceAll('-', '/') ?? '－'],
    ['担当者', USER_NAMES[deal.owner ?? ''] ?? deal.owner ?? '－'],
    ['登録日', deal.created_at ? new Date(deal.created_at).toLocaleDateString('ja-JP') : '－'],
  ]

  // 財務情報テーブルのセル描画（1行に act/base/sponsor 最大3項目がぶら下がる）
  const finRowItems = (r: FinRow): ExtractedItem[] =>
    r.kpiItem ? [r.kpiItem] : (['act', 'base', 'sponsor'] as CaseKey[]).map((c) => r.items[c]).filter(Boolean) as ExtractedItem[]

  return (
    <div>
      {/* 案件基本情報（概要に載せきれない情報） */}
      <section className="card mb-4">
        <div className="border-b border-surface-container-high bg-surface-container-low/50 px-4 py-2.5 text-[13px] font-bold">
          案件基本情報
        </div>
        <div className="grid grid-cols-3 gap-x-8 gap-y-2 px-4 py-3">
          {basicInfo.map(([k, v]) => (
            <div key={k} className="flex items-baseline gap-2 text-[12.5px]">
              <span className="w-44 shrink-0 text-outline">{k}</span>
              <span className="font-medium">{v}</span>
            </div>
          ))}
        </div>
        {full.documents.length > 0 && (
          <div className="border-t border-surface-container-low px-4 py-3">
            <div className="mb-1.5 text-[11px] font-medium text-outline">アップロード資料（{full.documents.length}件）</div>
            <div className="flex flex-wrap gap-2">
              {full.documents.map((d) => (
                <span key={d.id} className="badge-base badge-neutral" title={d.identified_detail ?? ''}>
                  <Icon name={d.filename.endsWith('.pdf') ? 'picture_as_pdf' : 'table_chart'} className="text-[13px]" />
                  {d.identified_label ?? d.slot_label}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      {progress.required > 0 && progress.confirmed === progress.required && (
        <div className="mb-3 flex items-center gap-2 rounded border border-green-300 bg-green-50 px-4 py-2.5 text-[13px] text-green-800">
          <Icon name="check_circle" className="text-[18px]" fill />
          必須項目がすべて確定しました。KPI構造タブへ進めます。
        </div>
      )}

      {items.length === 0 && (
        <div className="card mt-4 p-12 text-center text-[13px] text-outline">
          資料のAI解析が完了すると、抽出された数値がここに表示されます。
        </div>
      )}

      {/* 財務情報：過去実績・Base・Sponsorを横並び、PL/重要KPI/BS/CFを縦並びの統合テーブル */}
      {fin.hasRows && (
        <section className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-surface-container-high bg-surface-container-low/50 px-4 py-2.5 text-[13px] font-bold">
            <span className="flex items-center gap-2">
              財務情報 <span className="text-[11px] font-normal text-outline">（百万円）</span>
            </span>
            <span className="flex items-center gap-4 text-[11px] font-normal text-on-surface-variant">
              <span className="font-data-tabular">
                確定 {progress.confirmed}/{progress.required}必須項目
                {progress.held > 0 && `（保留 ${progress.held}）`}
              </span>
              {(() => {
                const targets = [...fin.grouped.flatMap(([, rs]) => rs)].flatMap(finRowItems).filter(bulkSelectable)
                if (targets.length === 0) return null
                return (
                  <label className="flex cursor-pointer items-center gap-1.5">
                    <input
                      type="checkbox"
                      checked={targets.every((it) => checked.has(it.id))}
                      onChange={() => toggleSection(targets)}
                    />
                    未確定を全選択
                  </label>
                )
              })()}
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[12.5px]">
              <thead>
                <tr className="border-b border-surface-container-high bg-surface-container-low/30 text-[11px] text-on-surface-variant">
                  <th className="w-8 px-1 py-1.5" />
                  <th className="w-8 px-1 py-1.5" />
                  <th className="min-w-[110px] px-2 py-1.5 text-left font-medium">項目</th>
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
                  <th /><th /><th />
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
                    const selectable = rowItems.filter(bulkSelectable)
                    const anyUnconfirmed = rowItems.some((it) => it.status !== 'confirmed')
                    const anyNeedsChoice = rowItems.some(needsChoice)
                    const cell = (item: ExtractedItem | undefined, y: string, first: boolean) => {
                      const v = item?.effective_values?.[y]
                      return (
                        <td
                          key={y}
                          onClick={item ? () => openItem(item) : undefined}
                          className={`px-2 py-2 text-right ${first ? 'border-l border-surface-container-high' : ''} ${
                            item ? 'cursor-pointer hover:bg-primary-fixed/30' : ''
                          } ${item && item.status !== 'confirmed' ? 'bg-amber-50/70' : ''}`}
                          title={item ? `${item.label}（クリックで根拠・確定操作）` : undefined}
                        >
                          {v != null
                            ? <span className={`font-data-tabular ${item?.mismatch ? 'rounded outline outline-1 outline-amber-300 px-1' : ''}`}>{v.toLocaleString()}</span>
                            : <span className="text-outline-variant">－</span>}
                        </td>
                      )
                    }
                    return (
                      <tr key={r.metric} className="border-b border-surface-container-low last:border-0">
                        {ri === 0 && (
                          <td
                            rowSpan={rows.length}
                            className="w-8 border-r border-surface-container-high bg-surface-container-low/40 px-1 py-2 text-center align-middle text-[11px] font-bold text-on-surface-variant"
                            style={{ writingMode: 'vertical-rl' }}
                          >
                            {group}
                          </td>
                        )}
                        <td className="px-1 py-2 text-center" onClick={(e) => e.stopPropagation()}>
                          {selectable.length > 0 ? (
                            <input
                              type="checkbox"
                              className="cursor-pointer"
                              checked={selectable.every((it) => checked.has(it.id))}
                              onChange={() => toggleSection(rowItems)}
                              title="この行の未確定項目を選択"
                            />
                          ) : anyNeedsChoice ? (
                            <span title="不整合の値選択が必要なため、セルを開いて個別に確定してください">
                              <Icon name="rule" className="text-[14px] text-amber-600" />
                            </span>
                          ) : null}
                        </td>
                        <td className="whitespace-nowrap px-2 py-2 font-medium">
                          {r.label}
                          {anyUnconfirmed && <span className="ml-1 align-middle text-amber-600" title="未確定の値があります">●</span>}
                          {rowItems.some((it) => it.mismatch) && (
                            <Icon name="warning" className="ml-1 align-middle text-[13px] text-amber-600" />
                          )}
                        </td>
                        {fin.yearsAct.map((y, i) => cell(r.kpiItem ?? r.items.act, y, i === 0))}
                        {fin.yearsBase.map((y, i) => cell(r.kpiItem ?? r.items.base, y, i === 0))}
                        {fin.yearsSponsor.map((y, i) => cell(r.kpiItem ? undefined : r.items.sponsor, y, i === 0))}
                      </tr>
                    )
                  }),
                )}
              </tbody>
            </table>
          </div>
          <div className="border-t border-surface-container-low px-4 py-1.5 text-[11px] text-outline">
            薄い黄色のセル＝未確定（クリックで根拠を確認して確定）。●＝未確定あり、⚠＝資料間の不整合あり。
          </div>
        </section>
      )}

      {/* 進捗カウントは財務テーブルが出ない案件（定性のみ等）でも常時表示する */}
      <div className="mt-3 flex items-center justify-end gap-4 text-[12px] text-on-surface-variant">
        <span className="font-data-tabular">
          確定 {progress.confirmed}/{progress.required}必須項目
          {progress.held > 0 && `（保留 ${progress.held}）`}
        </span>
        <label className="flex cursor-pointer items-center gap-1.5">
          <input type="checkbox" checked={onlyPending} onChange={(e) => setOnlyPending(e.target.checked)} />
          下のセクションで未確定のみ表示
        </label>
      </div>

      {/* セクション別テーブル */}
      {sections.map(([section, sectionItems]) => {
        const numeric = sectionItems.filter((i) => i.values)
        const textual = sectionItems.filter((i) => !i.values)
        const years = sortYears([...new Set(numeric.flatMap((i) => Object.keys(i.effective_values ?? {})))])
        return (
          <section key={section} className="card mt-4 overflow-hidden">
            <div className="flex items-center justify-between border-b border-surface-container-high bg-surface-container-low/50 px-4 py-2.5 text-[13px] font-bold">
              {section}
              {sectionItems.some(bulkSelectable) && (
                <label className="flex cursor-pointer items-center gap-1.5 text-[11px] font-normal text-on-surface-variant">
                  <input
                    type="checkbox"
                    checked={sectionItems.filter(bulkSelectable).every((it) => checked.has(it.id))}
                    onChange={() => toggleSection(sectionItems)}
                  />
                  未確定を全選択
                </label>
              )}
            </div>
            {numeric.length > 0 && (
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-surface-container-high text-left text-[11px] text-on-surface-variant">
                    <th className="w-9 px-2 py-2" />
                    <th className="px-2 py-2 font-medium">項目（百万円）</th>
                    {years.map((y) => (
                      <th key={y} className="px-3 py-2 text-right font-medium">
                        {y}
                        <span className="ml-0.5 text-outline-variant">{['FY24', 'FY25', 'FY26'].includes(y) ? '実' : ''}</span>
                      </th>
                    ))}
                    <th className="w-24 px-3 py-2 text-center font-medium">状態</th>
                  </tr>
                </thead>
                <tbody>
                  {numeric.map((item) => (
                    <tr
                      key={item.id}
                      onClick={() => openItem(item)}
                      className={`cursor-pointer border-b border-surface-container-low last:border-0 hover:bg-primary-fixed/20 ${
                        selected?.id === item.id ? 'bg-primary-fixed/30' : ''
                      }`}
                    >
                      <td className="px-2 py-2.5 text-center" onClick={(e) => e.stopPropagation()}>
                        {bulkSelectable(item) ? (
                          <input
                            type="checkbox"
                            className="cursor-pointer"
                            checked={checked.has(item.id)}
                            onChange={() => toggleCheck(item.id)}
                          />
                        ) : needsChoice(item) ? (
                          <span title="不整合の値選択が必要なため、行を開いて個別に確定してください">
                            <Icon name="rule" className="text-[15px] text-amber-600" />
                          </span>
                        ) : null}
                      </td>
                      <td className="px-2 py-2.5">
                        <span className="font-medium">{item.label}</span>
                        {!item.required && <span className="ml-1.5 text-[10px] text-outline">任意</span>}
                        {item.mismatch && (
                          <span className="badge-base badge-warning ml-2 !px-1.5 !py-0 !text-[10px]">
                            <Icon name="warning" className="text-[11px]" /> 不整合
                          </span>
                        )}
                      </td>
                      {years.map((y) => {
                        const v = item.effective_values?.[y]
                        const orig = item.values?.[y]
                        const changed = item.edited && orig !== undefined && v !== orig
                        return (
                          <td key={y} className="px-3 py-2.5 text-right">
                            {v != null ? (
                              <span className={`font-data-tabular ${changed ? 'font-bold text-primary-container' : ''} ${item.mismatch ? 'rounded bg-amber-50 px-1 py-0.5 outline outline-1 outline-amber-300' : ''}`}>
                                {v.toLocaleString()}
                              </span>
                            ) : <span className="text-outline-variant">－</span>}
                          </td>
                        )
                      })}
                      <td className="px-3 py-2.5 text-center"><StatusIcon item={item} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {textual.map((item) => (
              <div
                key={item.id}
                onClick={() => openItem(item)}
                className={`flex cursor-pointer items-start gap-4 border-t border-surface-container-low px-4 py-3 hover:bg-primary-fixed/20 ${
                  selected?.id === item.id ? 'bg-primary-fixed/30' : ''
                }`}
              >
                <div className="w-5 shrink-0 pt-0.5 text-center" onClick={(e) => e.stopPropagation()}>
                  {bulkSelectable(item) ? (
                    <input
                      type="checkbox"
                      className="cursor-pointer"
                      checked={checked.has(item.id)}
                      onChange={() => toggleCheck(item.id)}
                    />
                  ) : needsChoice(item) ? (
                    <span title="不整合の値選択が必要なため、行を開いて個別に確定してください">
                      <Icon name="rule" className="text-[15px] text-amber-600" />
                    </span>
                  ) : null}
                </div>
                <div className="w-52 shrink-0 text-[13px] font-medium">
                  {item.label}
                  {!item.required && <span className="ml-1.5 text-[10px] text-outline">任意</span>}
                </div>
                <div className="flex-1 text-[13px] leading-relaxed text-on-surface-variant">
                  {item.effective_text ?? (item.effective_values?.FY26 != null ? `${item.effective_values.FY26.toLocaleString()}百万円` : '')}
                </div>
                <div className="w-20 text-center"><StatusIcon item={item} /></div>
              </div>
            ))}
          </section>
        )
      })}

      {/* 一括確定バー */}
      {checked.size > 0 && (
        <div className="fixed bottom-5 left-1/2 z-40 flex -translate-x-1/2 items-center gap-3 rounded-lg border border-surface-container-high bg-white px-4 py-2.5 shadow-xl">
          <span className="text-[13px]">
            選択中 <b className="font-data-tabular text-primary-container">{checked.size}</b> 件
          </span>
          <button className="btn-primary !py-1.5 !text-[12px]" disabled={busy} onClick={bulkConfirm}>
            <Icon name="done_all" className="text-[16px]" />
            まとめて確定（{USER_NAMES[userKey] ?? userKey} として記録）
          </button>
          <button className="btn-secondary !py-1.5 !text-[12px]" disabled={busy} onClick={() => setChecked(new Set())}>
            選択解除
          </button>
        </div>
      )}

      {/* 根拠スライドパネル */}
      {selected && (
        <SlidePanel
          title={
            <div className="flex items-center gap-2">
              <span>{selected.label}</span>
              <StatusIcon item={selected} />
            </div>
          }
          onClose={() => setSelected(null)}
          footer={
            <div className="space-y-2">
              {mmChoiceAvailable && selected.status !== 'confirmed' && !mismatchChoice && (
                <div className="text-center text-[11px] text-amber-700">
                  不整合があります。採用する値を上で選択してください。
                </div>
              )}
              {!editMode ? (
                <div className="flex gap-2">
                  <button
                    className="btn-primary flex-1 justify-center"
                    disabled={busy || (mmChoiceAvailable && selected.status !== 'confirmed' && !mismatchChoice)}
                    onClick={confirmAsIs}
                  >
                    <Icon name="check" className="text-[16px]" />
                    {selected.status === 'confirmed' ? '再確定' : 'そのまま確定'}
                  </button>
                  <button className="btn-secondary flex-1 justify-center" disabled={busy} onClick={() => setEditMode(true)}>
                    <Icon name="edit" className="text-[16px]" /> 修正して確定
                  </button>
                  {selected.status !== 'held' ? (
                    <button className="btn-secondary" disabled={busy} onClick={() => doAction('hold')}>保留</button>
                  ) : (
                    <button className="btn-secondary" disabled={busy} onClick={() => doAction('unconfirm')}>保留解除</button>
                  )}
                </div>
              ) : (
                <div className="flex gap-2">
                  <button className="btn-primary flex-1 justify-center" disabled={busy} onClick={confirmEdited}>
                    <Icon name="check" className="text-[16px]" /> この内容で確定
                  </button>
                  <button className="btn-secondary" disabled={busy} onClick={() => setEditMode(false)}>戻る</button>
                </div>
              )}
              {selected.status === 'confirmed' && !editMode && (
                <button className="w-full text-center text-[11px] text-outline underline" disabled={busy} onClick={() => doAction('unconfirm')}>
                  確定を解除する（下流に警告が表示されます）
                </button>
              )}
            </div>
          }
        >
          {/* 値の表示・編集 */}
          {selected.values && !editMode && (
            <div className="mb-4 rounded bg-surface-container-low/60 p-3">
              <div className="flex flex-wrap gap-x-5 gap-y-1">
                {sortYears(Object.keys(selected.effective_values ?? {})).map((y) => (
                  <div key={y}>
                    <span className="text-[11px] text-outline">{y}</span>
                    <div className="font-data-tabular text-[18px] font-bold text-primary-container">
                      {selected.effective_values?.[y]?.toLocaleString()}
                      <span className="ml-1 text-[11px] font-normal text-outline">{selected.unit}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {editMode && selected.values && (
            <div className="mb-4 space-y-2 rounded border border-primary-container/30 bg-primary-fixed/10 p-3">
              <div className="text-[12px] font-bold text-primary-container">値を修正（{selected.unit}）</div>
              {sortYears(Object.keys(selected.effective_values ?? {})).map((y) => (
                <label key={y} className="flex items-center gap-2 text-[12px]">
                  <span className="w-12 text-outline">{y}</span>
                  <input
                    type="number"
                    className="input-base font-data-tabular !py-1"
                    value={editValues[y] ?? ''}
                    onChange={(e) => setEditValues({ ...editValues, [y]: e.target.value })}
                  />
                </label>
              ))}
              <input
                className="input-base !py-1 !text-[12px]"
                placeholder="修正理由（任意）"
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
              />
            </div>
          )}
          {selected.text_value && !editMode && (
            <div className="mb-4 rounded bg-surface-container-low/60 p-3 text-[13px] leading-relaxed">
              {selected.effective_text}
            </div>
          )}
          {editMode && selected.text_value != null && (
            <div className="mb-4">
              <textarea className="input-base h-28 !text-[12px]" value={editText} onChange={(e) => setEditText(e.target.value)} />
            </div>
          )}

          {/* 不整合警告と選択 */}
          {mm && (
            <div className="mb-4 rounded border border-amber-300 bg-amber-50 p-3">
              <div className="flex items-center gap-1.5 text-[12px] font-bold text-amber-800">
                <Icon name="warning" className="text-[16px]" /> 資料間の不整合
              </div>
              {mm.note && <p className="mt-1.5 text-[12px] leading-relaxed text-amber-900">{mm.note}</p>}
              {(mm.file || mm.quote) && (
                <div className="mt-2 rounded border border-amber-200 bg-white p-2 text-[11px] text-on-surface-variant">
                  <div className="font-medium">{mm.file}{mm.location && `（${mm.location}）`}</div>
                  {mm.quote && <div className="mt-1">「{mm.quote}」</div>}
                </div>
              )}
              {selected.status !== 'confirmed' && mmChoiceAvailable && (
                <div className="mt-2.5 space-y-1.5">
                  <label className="flex cursor-pointer items-center gap-2 rounded border border-amber-200 bg-white px-2.5 py-1.5 text-[12px]">
                    <input type="radio" name="mm" checked={mismatchChoice === 'model'} onChange={() => setMismatchChoice('model')} />
                    財務モデルの値を採用（<b className="font-data-tabular">{selected.effective_values?.[mmYear!]?.toLocaleString()}</b>）
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 rounded border border-amber-200 bg-white px-2.5 py-1.5 text-[12px]">
                    <input type="radio" name="mm" checked={mismatchChoice === 'dd'} onChange={() => setMismatchChoice('dd')} />
                    財務DDの値を採用（<b className="font-data-tabular">{mm.otherValue?.toLocaleString()}</b>）
                  </label>
                </div>
              )}
              {selected.status !== 'confirmed' && !mmChoiceAvailable && (
                <p className="mt-2 text-[11px] text-amber-800">
                  値の採用選択はありません。内容を確認のうえ、そのまま確定するか「修正して確定」で値・本文を調整してください。
                </p>
              )}
              {selected.resolution_note && (
                <div className="mt-2 text-[11px] text-amber-800">解決メモ：{selected.resolution_note}</div>
              )}
            </div>
          )}

          {/* 根拠3点セット */}
          {selected.evidence && <EvidenceBlock evidence={selected.evidence} />}

          {selected.status === 'confirmed' && (
            <div className="mt-4 rounded bg-surface-container-low/60 px-3 py-2 text-[11px] text-outline">
              確定：{selected.confirmed_by === 'tanaka' ? '田中' : selected.confirmed_by === 'sato' ? '佐藤' : selected.confirmed_by === 'takahashi' ? '高橋' : selected.confirmed_by}
              {selected.confirmed_at && `　${new Date(selected.confirmed_at).toLocaleString('ja-JP')}`}
            </div>
          )}

          {/* この項目への指摘（審査相談） */}
          {full.findings.filter((f) => f.target_type === 'item' && f.target_key === selected.key).map((f) => (
            <div key={f.id} className="mt-4 rounded border border-surface-container-high bg-surface-container-low/60 p-3 text-[12px]">
              <div className="flex items-center gap-1 font-bold text-on-surface-variant">
                <Icon name="feedback" className="text-[14px]" /> 前回審査相談での指摘
              </div>
              <p className="mt-1 text-on-surface-variant">{f.text}</p>
            </div>
          ))}
        </SlidePanel>
      )}
    </div>
  )
}
