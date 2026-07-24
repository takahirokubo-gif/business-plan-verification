import type { ExtractedItem } from './types'

/**
 * 財務情報の統合テーブル（確定財務・Base・Sponsorを横並び、PL/重要KPI/BS/CFを縦並び）の
 * 構築ロジック。財務ダイジェストタブ（編集）と概要タブ（読み取り専用）で共用する。
 */

const YEAR_ORDER = ['FY24', 'FY25', 'FY26', 'FY27', 'FY28', 'FY29', 'FY30', 'FY31']

/** 年度キーの表示順。既知のFY形式を先に、それ以外（'2027/3期' など実AIの表記）も
 *  捨てずに末尾へ昇順で並べる（キー形式が想定と違っても数値を必ず表示する）。 */
export function sortYears(years: string[]): string[] {
  const known = YEAR_ORDER.filter((y) => years.includes(y))
  const unknown = years.filter((y) => !YEAR_ORDER.includes(y)).sort()
  return [...known, ...unknown]
}

export type CaseKey = 'act' | 'base' | 'sponsor'
export type FinGroup = 'PL' | '重要KPI' | 'BS' | 'CF'

export interface FinRow {
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

export function buildFinTable(items: ExtractedItem[]) {
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

export type FinTable = ReturnType<typeof buildFinTable>

/** 1行にぶら下がる項目（act/base/sponsor 最大3、またはKPI単独） */
export function finRowItems(r: FinRow): ExtractedItem[] {
  return r.kpiItem
    ? [r.kpiItem]
    : (['act', 'base', 'sponsor'] as CaseKey[]).map((c) => r.items[c]).filter(Boolean) as ExtractedItem[]
}
