import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api'
import { Icon } from '../../components/Icon'
import { Badge } from '../../components/Badge'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { useUser } from '../../context/UserContext'
import { sortYears } from '../../finTable'
import type { DealFull, ExportPreview, ExtractedItem, KpiNode, Scenario } from '../../types'

/** 出力ファイル（PDF/Excel）と同じ配色のシナリオキー丸バッジ */
const SCENARIO_KEY_COLOR: Record<string, string> = {
  A: 'bg-primary-container',
  B: 'bg-amber-700',
  C: 'bg-error',
}

/** 出力ファイルと同じ行順（backend export と共通の並び） */
const METRIC_ORDER = [
  'revenue', 'gross', 'op', 'ordinary', 'ni', 'ebitda',
  'utilization', 'new_hires', 'unit_price', 'cpa',
  'cash', 'goodwill', 'net_assets', 'debt', 'total_assets',
  'op_cf', 'inv_cf', 'fin_cf', 'fcf',
]

/** ケース（act/base/sponsor）の確定済み行を出力ファイルと同じ順で集める */
function caseRows(items: ExtractedItem[], prefix: string): { item: ExtractedItem; label: string }[] {
  const found = items
    .filter((i) => i.status === 'confirmed' && i.key.startsWith(`${prefix}_`)
      && i.effective_values && Object.keys(i.effective_values).length > 0)
    .map((i) => ({
      item: i,
      metric: i.key.slice(prefix.length + 1),
      label: i.label + (i.unit !== '百万円' ? `（${i.unit}）` : ''),
    }))
  const order = new Map(METRIC_ORDER.map((m, idx) => [m, idx]))
  found.sort((a, b) => (order.get(a.metric) ?? METRIC_ORDER.length) - (order.get(b.metric) ?? METRIC_ORDER.length))
  return found
}

/** ケースの年度列（実データのキーから導出・最大5列＝出力ファイルと同じ） */
function caseYears(rows: { item: ExtractedItem }[]): string[] {
  return sortYears([...new Set(rows.flatMap((r) => Object.keys(r.item.effective_values ?? {})))]).slice(0, 5)
}

/** 番号チップ付きセクション見出し（PDFのheadingと同じ見せ方） */
function DocHeading({ num, title }: { num: string; title: string }) {
  return (
    <div className="mt-7 border-b-2 border-primary-container pb-1.5 first:mt-0">
      <span className="inline-flex items-center gap-2.5">
        <span className="bg-primary-container px-2 py-0.5 text-[11px] font-bold text-white">{num}</span>
        <span className="text-[14px] font-bold text-primary-container">{title}</span>
      </span>
    </div>
  )
}

/** 「■ 見出し」の小見出し（PDFのsubheadingと同じ見せ方） */
function DocSubheading({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-3 flex items-center gap-1.5 text-[12px] font-bold">
      <span className="h-[7px] w-[7px] shrink-0 bg-primary-container" />
      {children}
    </div>
  )
}

/** 財務テーブル（色付きヘッダー＋ゼブラ行＝PDFのtableと同じ見せ方） */
function DocFinTable({ title, rows, years }: {
  title: string
  rows: { item: ExtractedItem; label: string }[]
  years: string[]
}) {
  if (rows.length === 0) return null
  return (
    <table className="mt-3 w-full text-[11.5px]">
      <thead>
        <tr className="bg-primary-fixed/70 text-[11px] font-bold text-primary-container">
          <th className="px-2 py-1 text-left">{title}</th>
          {years.map((y) => <th key={y} className="px-2 py-1 text-right">{y}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.map(({ item, label }, i) => (
          <tr key={item.key} className={`border-b border-surface-container-low ${i % 2 === 1 ? 'bg-surface-container-low/40' : ''}`}>
            <td className="px-2 py-1 font-medium">{label}</td>
            {years.map((y) => {
              const v = item.effective_values?.[y]
              return (
                <td key={y} className="font-data-tabular px-2 py-1 text-right">
                  {v != null ? v.toLocaleString() : '－'}
                </td>
              )
            })}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function ExportTab({ full, refresh, dealId }: {
  full: DealFull
  refresh: () => Promise<void>
  dealId: number
}) {
  const { userKey } = useUser()
  const [preview, setPreview] = useState<ExportPreview | null>(null)
  const [confirmHeld, setConfirmHeld] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState('')
  const deal = full.deal

  useEffect(() => {
    api.exportPreview(dealId).then(setPreview)
  }, [dealId, full])

  const [format, setFormat] = useState<'xlsx' | 'pdf'>('xlsx')

  const doExport = async (fmt: 'xlsx' | 'pdf' = format) => {
    setDownloading(true)
    setError('')
    try {
      if (fmt === 'pdf') await api.exportPdf(dealId, userKey)
      else await api.exportExcel(dealId, userKey)
      await refresh()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setDownloading(false)
    }
  }

  const onExportClick = (fmt: 'xlsx' | 'pdf') => {
    setFormat(fmt)
    if (preview && preview.held_items.length > 0) setConfirmHeld(true)
    else doExport(fmt)
  }

  // ---- 出力ファイルと同じデータ（確定値のみ） ----
  const actRows = useMemo(() => caseRows(full.items, 'act'), [full.items])
  const baseRows = useMemo(() => caseRows(full.items, 'base'), [full.items])
  const sponsorRows = useMemo(() => caseRows(full.items, 'sponsor'), [full.items])
  const finNotes = full.items.filter((i) => i.status === 'confirmed' && i.section === '財務ハイライト' && i.effective_text)
  const adopted = full.scenarios.filter((s) => s.adopted)
  const rejected = full.scenarios.filter((s) => !s.adopted)
  const qualItems = full.items.filter(
    (i) => i.status === 'confirmed' && i.unit === 'テキスト' && i.section !== '財務ハイライト',
  )
  const heldLabels = preview?.held_items.map((h) => h.label) ?? []

  const kpiLabelOf = (id: string) => full.kpi_nodes.find((n) => n.node_id === id)?.label ?? id

  // KPIツリー（親→子）
  const childrenOf = useMemo(() => {
    const map = new Map<string | null, KpiNode[]>()
    for (const n of full.kpi_nodes) {
      const key = n.parent_id ?? null
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(n)
    }
    return map
  }, [full.kpi_nodes])

  const renderKpiLines = (parent: string | null, depth: number): React.ReactNode =>
    (childrenOf.get(parent) ?? []).map((n) => (
      <div key={n.node_id}>
        <div
          className={`flex items-baseline gap-1.5 px-1.5 py-[3px] text-[11.5px] ${n.star ? 'bg-amber-50 font-medium text-amber-900' : ''}`}
          style={{ marginLeft: depth * 16 }}
        >
          <span className={`shrink-0 ${n.star ? 'text-amber-600' : 'text-outline-variant'}`}>
            {n.star ? '★' : '・'}
          </span>
          <span className="shrink-0 font-bold">{n.label}</span>
          {n.formula ? (
            <span className="font-data-tabular text-on-surface-variant">＝ {n.formula.replace(/^[=＝]\s*/, '')}</span>
          ) : n.value_text ? (
            <span className="text-on-surface-variant">（{n.value_text}）</span>
          ) : null}
        </div>
        {renderKpiLines(n.node_id, depth + 1)}
      </div>
    ))

  const scenarioBlock = (sc: Scenario) => (
    <div key={sc.key} className="mt-3 first:mt-0">
      <div className="flex items-center gap-2">
        <span className={`flex h-[20px] w-[20px] shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white ${SCENARIO_KEY_COLOR[sc.key] ?? 'bg-outline'}`}>
          {sc.key}
        </span>
        <span className="text-[12.5px] font-bold text-primary-container">{sc.title}</span>
        <span className="text-[11px] text-outline">
          （{sc.origin === 'ai' ? 'AI推奨' : '自分の仮説'}／{sc.type_label}）
        </span>
      </div>
      <ul className="mt-1 space-y-0.5 pl-7 text-[11.5px] leading-relaxed text-on-surface-variant">
        <li><b className="text-on-surface">・【KPIとリスク】</b>{sc.affected_kpis.map(kpiLabelOf).join('、') || '－'}。{sc.cause}</li>
        <li><b className="text-on-surface">・【ストレスと根拠】</b>{sc.change_text}（根拠：{sc.change_basis}）</li>
        <li className="text-amber-800"><b>・【インパクト】</b>{sc.impact}（AI推定・モデル再計算なし）</li>
        <li><b className="text-on-surface">・【保全策・構造】</b>{sc.safeguards}</li>
        <li><b className="text-on-surface">・【Q&A】</b>{sc.questions}</li>
      </ul>
    </div>
  )

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <div className="text-[14px] font-bold">審査相談資料の出力</div>
        <div className="text-[11px] text-outline">
          下は実際に出力される資料（PDF/Excel）のプレビューです。確定データのみを転記し、AIによる推定値には注記が付きます。
        </div>
      </div>

      <div className="grid grid-cols-[1fr_320px] items-start gap-4">
        {/* ---- 紙面プレビュー（出力されるPDFと同じ構成・デザイン） ---- */}
        <div className="rounded bg-surface-container/70 p-5">
          <div className="mx-auto max-w-[760px] border border-outline-variant/60 bg-white">
            {/* ヘッダー帯（PDF表紙と同じ） */}
            <div className="bg-primary px-8 pb-5 pt-6 text-white">
              <div className="text-[10.5px] tracking-widest opacity-90">審査相談資料（事業計画検証）</div>
              <div className="mt-1.5 text-[19px] font-bold leading-snug">{deal.name}</div>
              <div className="mt-1.5 text-[10px] text-primary-fixed">
                作成 {new Date().toLocaleDateString('ja-JP')}／担当 {userKey === 'tanaka' ? '田中' : userKey === 'sato' ? '佐藤' : '高橋'}
                ／確定データのみを転記（AIによる推定値には注記）
              </div>
            </div>
            <div className="h-[3px] bg-primary-container" />

            <div className="px-8 py-6">
              {/* 01 案件基本情報・事業要約 */}
              <DocHeading num="01" title="案件基本情報・事業要約" />
              <div className="mt-3 grid grid-cols-4 gap-2.5">
                {[
                  ['EV（買収総額）', deal.ev_mm != null ? `${deal.ev_mm.toLocaleString()}百万円` : '－'],
                  ['シニア（本行取組）', deal.senior_mm != null ? `${deal.senior_mm.toLocaleString()}（${(deal.our_commitment_mm ?? 0).toLocaleString()}）百万円` : '－'],
                  ['エクイティ', deal.equity_mm != null ? `${deal.equity_mm.toLocaleString()}百万円` : '－'],
                  ['レバレッジ／LTV', deal.initial_leverage != null ? `${deal.initial_leverage}x／${deal.ltv_pct}%` : '－'],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-sm border border-surface-container-high bg-surface-container-low/50 px-2 py-2 text-center">
                    <div className="text-[9px] text-outline">{label}</div>
                    <div className="font-data-tabular mt-0.5 text-[12.5px] font-bold text-primary-container">{value}</div>
                  </div>
                ))}
              </div>
              <table className="mt-3 w-full text-[11.5px]">
                <tbody>
                  {([
                    ['案件スキーム', deal.deal_type ?? '－'],
                    ['借入人（SPC）', deal.borrower || '－'],
                    ['対象会社', `${deal.target}（${deal.industry ?? '－'}）`],
                    ['スポンサー', deal.sponsor ?? '－'],
                    ['クローズ予定日', deal.close_date?.replaceAll('-', '/') ?? '－'],
                  ] as [string, string][]).map(([k, v]) => (
                    <tr key={k} className="border-b border-surface-container-low">
                      <td className="w-36 py-1 pl-1 text-outline">{k}</td>
                      <td className="py-1">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {deal.summary && (
                <p className="mt-2.5 text-[11px] leading-relaxed text-on-surface-variant">事業要約：{deal.summary}</p>
              )}

              {/* 02 重要KPIとその構造 */}
              <DocHeading num="02" title="重要KPIとその構造（ツリー）" />
              <div className="mt-2.5">{renderKpiLines(null, 0)}</div>
              <div className="mt-1.5 text-[10px] text-outline">
                ★＝最重要KPI（ストレスシナリオの起点）。数式は財務モデルの構文解析結果（再計算なし）。
              </div>

              {/* 03 財務情報 */}
              <DocHeading num="03" title="財務情報（百万円・確定値のみ）" />
              <DocFinTable title="実績" rows={actRows} years={caseYears(actRows)} />
              <DocFinTable title="計画（ベースケース）" rows={baseRows} years={caseYears(baseRows)} />
              <DocFinTable title="計画（スポンサーケース）" rows={sponsorRows} years={caseYears(sponsorRows)} />
              {finNotes.map((item) => (
                <div key={item.id}>
                  <DocSubheading>{item.label}（AI推定・モデル再計算なし）</DocSubheading>
                  <p className="mt-1 whitespace-pre-line pl-3.5 text-[11px] leading-relaxed text-on-surface-variant">
                    {item.effective_text}
                  </p>
                </div>
              ))}

              {/* 04 ストレス仮説 */}
              <DocHeading num="04" title="ストレス仮説とその根拠データ" />
              <div className="mt-2.5 inline-block bg-amber-50 px-1.5 py-0.5 text-[10.5px] text-amber-800">
                ※ インパクト数値はAIによる推定であり、財務モデルの再計算値ではありません。
              </div>
              <div className="mt-2">
                {adopted.map(scenarioBlock)}
                {rejected.map((sc) => (
                  <div key={sc.key} className="mt-1.5 pl-7 text-[10.5px] text-outline">
                    （参考・不採用）S{sc.key}｜{sc.title}
                    {sc.rejection_note && `　※${sc.rejection_note}`}
                  </div>
                ))}
              </div>

              {/* 05 前提・定性情報 */}
              <DocHeading num="05" title="前提・定性情報（確定済み）" />
              {qualItems.map((i) => (
                <div key={i.key}>
                  <DocSubheading>{i.label}</DocSubheading>
                  <p className="mt-0.5 pl-3.5 text-[11.5px] leading-relaxed">{i.effective_text}</p>
                  {i.evidence && (
                    <div className="mt-0.5 pl-3.5 text-[10px] text-outline">
                      出典：{i.evidence.file}｜{i.evidence.location}
                    </div>
                  )}
                </div>
              ))}

              {/* 06 審査相談の記録（末尾） */}
              {full.memos.length > 0 && (
                <>
                  <DocHeading num="06" title="審査相談の記録" />
                  {full.memos.slice().reverse().map((m) => (
                    <div key={m.id}>
                      <DocSubheading>
                        {m.meeting_date.replaceAll('-', '/')}　結論：{m.conclusion}（出席：{m.attendees.join('、')}）
                      </DocSubheading>
                      <div className="mt-0.5 space-y-0.5 pl-3.5 text-[11px] leading-relaxed">
                        {m.findings.map((f, i) => (
                          <div key={f.id}>
                            指摘{i + 1}
                            {f.target_type && (
                              <span>
                                【{f.target_type === 'scenario' ? `シナリオ${f.target_key}`
                                  : f.target_type === 'kpi' ? 'KPI構造' : `数値：${f.target_key}`}】
                              </span>
                            )}
                            ：{f.text}
                          </div>
                        ))}
                        {m.note && <div className="text-outline">メモ：{m.note}</div>}
                      </div>
                    </div>
                  ))}
                </>
              )}

              {heldLabels.length > 0 && (
                <div className="mt-5 text-[10.5px] text-outline">
                  ※ 保留中の{heldLabels.length}項目（{heldLabels.join('、')}）は本資料から除外しています。
                </div>
              )}

              {/* フッター（PDFと同じ） */}
              <div className="mt-6 flex items-center justify-between border-t border-surface-container-high pt-2 text-[9.5px] text-outline">
                <span>Confidential — 審査相談用（確定データのみ）</span>
                <span>1</span>
              </div>
            </div>
          </div>
          <div className="mt-2.5 text-center text-[10.5px] text-outline">
            出力されるPDFの紙面イメージ。Excel（.xlsx）は同じ内容が「審査サマリー／KPI構造／ストレス仮説／審査相談メモ」の4シートに、
            各数値の出典（参照ファイル・箇所）付きで収録されます。
          </div>
        </div>

        {/* ---- 出力設定 ---- */}
        <div className="space-y-4">
          {preview && preview.held_items.length > 0 && (
            <div className="rounded border border-amber-300 bg-amber-50 p-3 text-[12px]">
              <div className="flex items-center gap-1.5 font-bold text-amber-800">
                <Icon name="warning" className="text-[16px]" /> 保留が{preview.held_items.length}項目あります
              </div>
              <p className="mt-1 text-amber-900">保留項目を除いて出力されます。</p>
              <ul className="mt-1.5 list-inside list-disc text-amber-900">
                {preview.held_items.map((h) => <li key={h.key}>{h.label}</li>)}
              </ul>
            </div>
          )}
          {preview?.stale_warnings && (
            <div className="rounded border border-amber-300 bg-amber-50 p-3 text-[12px] text-amber-900">
              <Icon name="warning" className="mr-1 align-middle text-[15px]" />
              上流変更の警告が残っています。内容を再確認してから出力することを推奨します。
            </div>
          )}

          <section className="card overflow-hidden">
            <div className="flex items-center justify-between border-b border-surface-container-high bg-surface-container-low/50 px-4 py-2.5">
              <span className="flex items-center gap-1.5 text-[13.5px] font-bold">
                <span className="text-[10px] text-primary-container">▼</span>
                出力設定
              </span>
            </div>
            <div className="px-4 py-3">
              <div className="text-[11px] font-bold tracking-wider text-outline">収録コンテンツ（概要タブ構成）</div>
              <div className="mt-1.5 space-y-1.5 text-[12px]">
                {[
                  '01 案件基本情報・事業要約',
                  '02 重要KPIとその構造（ツリー）',
                  '03 財務情報（確定値・出典付き）',
                  '04 ストレス仮説（AI推定注記付き）',
                  '05 前提・定性情報（全文）',
                  '06 審査相談メモ（末尾）',
                ].map((c) => (
                  <div key={c} className="flex items-center gap-1.5">
                    <Icon name="check" className="text-[15px] text-primary-container" /> {c}
                  </div>
                ))}
              </div>
              <button
                className="btn-primary mt-4 w-full justify-center"
                disabled={!preview?.can_export || downloading}
                onClick={() => onExportClick('xlsx')}
              >
                <Icon name="download" className="text-[18px]" />
                {downloading ? '生成中…' : 'Excelをダウンロード（.xlsx）'}
              </button>
              <button
                className="btn-secondary mt-2 w-full justify-center"
                disabled={!preview?.can_export || downloading}
                onClick={() => onExportClick('pdf')}
              >
                <Icon name="picture_as_pdf" className="text-[18px]" /> PDFをダウンロード（補助）
              </button>
              {!preview?.can_export && (
                <div className="mt-2 text-[11px] text-error">
                  {!preview?.required_confirmed && '必須項目の確定が完了していません。'}
                  {preview && !preview.kpi_confirmed && 'KPI構造が確定されていません。'}
                </div>
              )}
              {error && <div className="mt-2 text-[11px] text-error">{error}</div>}
              <div className="mt-2 border-t border-surface-container-low pt-2 text-[10px] leading-relaxed text-outline">
                ※ 行内標準フォーマットに準拠したテンプレートへ確定値のみを転記します。
                AIによる推定値には注記が付きます。
              </div>
            </div>
          </section>

          <section className="card overflow-hidden">
            <div className="flex items-center justify-between border-b border-surface-container-high bg-surface-container-low/50 px-4 py-2.5">
              <span className="flex items-center gap-1.5 text-[13.5px] font-bold">
                <span className="text-[10px] text-primary-container">▼</span>
                出力履歴
              </span>
              {full.exports.length > 0 && <Badge kind="neutral">{full.exports.length}件</Badge>}
            </div>
            <div className="space-y-2 px-4 py-3">
              {full.exports.slice().reverse().map((e) => (
                <div key={e.id} className="flex items-start gap-2 border-b border-surface-container-low pb-2 text-[11px] last:border-0 last:pb-0">
                  <Icon
                    name={e.filename?.endsWith('.pdf') ? 'picture_as_pdf' : 'table_chart'}
                    className={`mt-0.5 text-[16px] ${e.filename?.endsWith('.pdf') ? 'text-error' : 'text-green-700'}`}
                  />
                  <div className="min-w-0">
                    <div className="truncate font-medium">{e.filename}</div>
                    <div className="text-outline">
                      {e.at ? new Date(e.at).toLocaleString('ja-JP') : ''}
                      {e.excluded_held > 0 && `・保留${e.excluded_held}件除外`}
                    </div>
                  </div>
                </div>
              ))}
              {full.exports.length === 0 && <div className="text-[11px] text-outline">まだ出力されていません</div>}
            </div>
          </section>
        </div>
      </div>

      <ConfirmDialog
        open={confirmHeld}
        title={`保留${preview?.held_items.length ?? 0}項目を除いて出力します`}
        confirmLabel="出力する"
        onConfirm={() => { setConfirmHeld(false); doExport(format) }}
        onCancel={() => setConfirmHeld(false)}
      >
        保留中の項目（{preview?.held_items.map((h) => h.label).join('、')}）は出力に含まれません。
        よろしいですか？
      </ConfirmDialog>
    </div>
  )
}
