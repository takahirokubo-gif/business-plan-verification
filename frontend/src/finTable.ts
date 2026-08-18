import type { ExtractedItem } from './types'

/**
 * 財務情報の統合テーブル（確定財務・Base・Sponsorを横並び、PL/重要KPI/BS/CFを縦並び）の
 * 構築ロジック。財務ダイジェストタブ（編集）と概要タブ（読み取り専用）で共用する。
 */

/** 年度キーの表示順。FY形式（FY22〜FY33等・A/Eサフィックス許容）は年度の昇順、
 *  それ以外（'2027/3期' など実AIの表記）も捨てずに末尾へ昇順で並べる
 *  （期数は資料に追随する可変スキーマ。ハードコードの年度リストは持たない）。 */
export function sortYears(years: string[]): string[] {
  const fyNum = (y: string): number | null => {
    const m = y.match(/^FY(\d{2})[AE]?$/)
    return m ? Number(m[1]) : null
  }
  const known = years.filter((y) => fyNum(y) != null)
    .sort((a, b) => (fyNum(a) as number) - (fyNum(b) as number))
  const unknown = years.filter((y) => fyNum(y) == null).sort()
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
const KPI_METRICS = new Set(['utilization', 'new_hires', 'unit_price', 'cpa'])

/** 表示行の標準順序（PL→重要KPI→BS→CFの中での並び）。未知の指標は各グループ末尾に出す */
const METRIC_ORDER = [
  'revenue', 'gross', 'op', 'ordinary', 'ni', 'ebitda',
  'utilization', 'new_hires', 'unit_price', 'cpa',
  'cash', 'goodwill', 'debt', 'net_assets',
  'op_cf', 'inv_cf', 'fin_cf', 'fcf',
]
/** 抽出はするがテーブルには出さない指標（エクスポート等では使用）。
 *  他項目の合計にすぎない指標のみを対象とする。
 *  必須項目には適用しない（隠すと確定できなくなるため。buildFinTable内で判定） */
const HIDDEN_METRICS = new Set(['total_assets'])
/** この指標の直後に「同率」（対売上比）行を挟む */
const RATIO_AFTER = new Set(['gross', 'op', 'ordinary'])

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
      // 非表示にしてよいのは任意項目だけ。必須項目を隠すと確定する場所が
      // 画面から消え、必須N/Mが埋まらずKPI確定・エクスポートへ進めなくなる
      if (HIDDEN_METRICS.has(ck.metric) && !it.required) {
        tableIds.add(it.id) // 表にもセクションにも出さない（帳票では使用）
        continue
      }
      let row = rowByMetric.get(ck.metric)
      if (!row) {
        const group: FinGroup = KPI_METRICS.has(ck.metric) ? '重要KPI'
          : BS_METRICS.has(ck.metric) ? 'BS' : CF_METRICS.has(ck.metric) ? 'CF' : 'PL'
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
  // グループ内を標準順に並べ替え（未知の指標は挿入順のまま末尾）
  const orderOf = (r: FinRow) => {
    const i = METRIC_ORDER.indexOf(r.metric)
    return i < 0 ? METRIC_ORDER.length : i
  }
  const groups: FinGroup[] = ['PL', '重要KPI', 'BS', 'CF']
  const grouped = groups
    .map((g) => [g, rows.filter((r) => r.group === g).sort((a, b) => orderOf(a) - orderOf(b))] as const)
    .filter(([, rs]) => rs.length > 0)
  const revenueRow = rowByMetric.get('revenue') ?? null
  return { grouped, yearsAct, yearsBase, yearsSponsor, tableIds, revenueRow, hasRows: rows.length > 0 }
}

export type FinTable = ReturnType<typeof buildFinTable>

/** この行の直後に「同率」（対売上比）行を表示するか */
export function hasRatioRow(r: FinRow): boolean {
  return RATIO_AFTER.has(r.metric)
}

/** 同率（対売上比）。売上行と同じケース・年度の値から表示用に単純計算（%・小数1桁） */
export function ratioValue(fin: FinTable, r: FinRow, c: CaseKey, y: string): string | null {
  const v = r.items[c]?.effective_values?.[y]
  const rev = fin.revenueRow?.items[c]?.effective_values?.[y]
  if (v == null || rev == null || rev === 0) return null
  return `${(Math.round((v / rev) * 1000) / 10).toFixed(1)}%`
}

/** テーブルセルの表示文字列（%単位のKPIは%を付ける） */
export function cellText(item: ExtractedItem, v: number): string {
  return item.unit === '%' ? `${v.toLocaleString()}%` : v.toLocaleString()
}

/** 財務テーブル直下に表示する論述項目（財務ハイライト・ケース前提差異）のセクション名 */
export const FIN_NOTE_SECTION = '財務ハイライト'

export function finNotesOf(items: ExtractedItem[]): ExtractedItem[] {
  return items.filter((it) => it.section === FIN_NOTE_SECTION && (it.effective_text ?? it.text_value))
}

/** 1行にぶら下がる項目（act/base/sponsor 最大3、またはKPI単独） */
export function finRowItems(r: FinRow): ExtractedItem[] {
  return r.kpiItem
    ? [r.kpiItem]
    : (['act', 'base', 'sponsor'] as CaseKey[]).map((c) => r.items[c]).filter(Boolean) as ExtractedItem[]
}
