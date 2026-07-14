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

export interface Evidence {
  file: string
  location: string
  quote: string | null
  logic: string
}

export interface Mismatch {
  other_value: number
  other_file: string
  other_location: string
  other_quote: string
  note: string
}

export interface ExtractedItem {
  id: number
  key: string
  section: string
  label: string
  unit: string
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
