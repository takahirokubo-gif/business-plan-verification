export interface User {
  key: string
  name: string
  role: string
  display: string
}

export interface DealListItem {
  id: number
  name: string
  deal_type: string
  borrower: string
  target: string
  our_commitment_mm: number | null
  review_status: string
  work_status: string
  owner: string | null
  next_meeting_date: string | null
  updated_at: string | null
}

export interface Deal extends DealListItem {
  industry: string | null
  sponsor: string | null
  close_date: string | null
  ev_mm: number | null
  senior_mm: number | null
  equity_mm: number | null
  tenor_years: number | null
  sponsor_ebitda_mm: number | null
  summary: string | null
  initial_leverage: number | null
  ltv_pct: number | null
  kpi_status: 'none' | 'proposed' | 'confirmed'
  kpi_confirmed_by: string | null
  kpi_confirmed_at: string | null
  kpi_stale_reason: string | null
  progress: { required: number; confirmed: number; held: number; total: number }
  created_at: string | null
}

/** 根拠吹き出しに出す「ソースの抜粋イメージ」。
 *  sheet＝Excel/表形式（該当行ハイライト＋数式）、doc＝PDF/テキスト（該当文をマーカー強調） */
export interface EvidenceSnippet {
  kind: 'sheet' | 'doc'
  /** リード文の上書き（未指定なら kind と formula から自動生成） */
  lead?: string
  title?: string
  head?: string[]
  rows?: { name: string; cells: string[]; hl?: boolean }[]
  formula?: string
  text?: string
  hl?: string
}

export interface Evidence {
  file: string
  location: string
  quote: string | null
  logic: string
  snippet?: EvidenceSnippet | null
}

export interface Mismatch {
  other_value?: number | null
  other_file?: string
  other_location?: string
  other_quote?: string
  note?: string
  // 実AIがスキーマ厳格化前に返した自由形式キー（既存データの救済用）
  description?: string
  source_file?: string
  source_location?: string
  source_quote?: string
}

/** 数値取得の状態（仕様③5）: 抽出値／計算値（システムが資料内数式から算出）／AI推定／未取得 */
export type SourceType = 'extracted' | 'calculated' | 'estimated' | 'missing'

export interface ExtractedItem {
  id: number
  key: string
  section: string
  label: string
  unit: string
  source_type: SourceType
  source_unit: string | null
  case_name: string | null
  values: Record<string, number> | null
  text_value: string | null
  effective_values: Record<string, number> | null
  effective_text: string | null
  required: boolean
  evidence: Evidence | null
  mismatch: Mismatch | null
  status: 'proposed' | 'confirmed' | 'held'
  edited: boolean
  resolution_note: string | null
  confirmed_by: string | null
  confirmed_at: string | null
}

export interface KpiNode {
  id: number
  node_id: string
  parent_id: string | null
  label: string
  origin: 'model' | 'dd' | 'manual'
  star: boolean
  formula: string | null
  value_text: string | null
  badge: string | null
  evidence: Evidence | null
  added_via_chat: boolean
}

/** インパクト指標の分解（参考試算）：左辺＝最終指標、右辺＝ストレス対象KPIを含む式。
 *  {{...}} で囲まれた部分はストレス起因の変化としてUIで強調表示される */
export interface ImpactCalcBlock {
  metric: string
  formula: string
  before: string
  after: string
  note: string | null
}

export interface Scenario {
  id: number
  key: string
  origin: 'ai' | 'human'
  type_label: string | null
  title: string
  cause: string | null
  affected_kpis: string[]
  change_text: string | null
  change_basis: string | null
  impact: string | null
  impact_calc: ImpactCalcBlock[] | null
  safeguards: string | null
  questions: string | null
  adopted: boolean
  rejection_note: string | null
  stale_reason: string | null
  updated_at: string | null
}

export interface MemoFinding {
  id: number
  target_type: string | null
  target_key: string | null
  text: string
  meeting_date?: string | null
}

export interface Memo {
  id: number
  meeting_date: string
  attendees: string[]
  conclusion: string
  note: string | null
  created_by: string | null
  created_at: string | null
  findings: MemoFinding[]
}

export interface HistoryEvent {
  id: number
  at: string | null
  user: string | null
  action: string
  detail: string | null
}

export interface ExportRecord {
  id: number
  at: string | null
  user: string | null
  filename: string
  excluded_held: number
}

export interface DocumentInfo {
  id: number
  slot: string
  slot_label: string
  filename: string
  status: string
  identified_company: string | null
  identified_label: string | null
  identified_detail: string | null
  uploaded_at: string | null
  company_match?: boolean
}

/** AIが検知した「人への確認事項（照会）」（仕様②6・③6） */
export interface Inquiry {
  id: number
  category: string
  severity: 'high' | 'medium' | 'low'
  title: string
  detail: string | null
  source: Evidence | null
  suggested_question: string | null
  status: 'open' | 'resolved'
  resolution_note: string | null
  resolved_by: string | null
  resolved_at: string | null
  created_at: string | null
}

export interface DealFull {
  deal: Deal
  documents: DocumentInfo[]
  items: ExtractedItem[]
  kpi_nodes: KpiNode[]
  scenarios: Scenario[]
  memos: Memo[]
  history: HistoryEvent[]
  exports: ExportRecord[]
  findings: MemoFinding[]
  inquiries: Inquiry[]
  chat_suggestions: { kpi: string[]; scenario: string[] }
}

export interface ChatDiff {
  type: 'add_node' | 'star_change' | 'add_card' | 'update_card'
  [key: string]: unknown
}

export interface ChatResult {
  reply: string
  diff: ChatDiff | null
}

export interface ExportPreview {
  can_export: boolean
  required_confirmed: boolean
  kpi_confirmed: boolean
  adopted_scenarios: number
  held_items: { key: string; label: string }[]
  stale_warnings: boolean
}

export const YEARS_ACTUAL = ['FY24', 'FY25', 'FY26']
export const YEARS_PLAN = ['FY27', 'FY28', 'FY29', 'FY30', 'FY31']
