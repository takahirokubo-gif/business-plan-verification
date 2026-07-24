import { useMemo } from 'react'
import { Icon } from '../../components/Icon'
import { Badge } from '../../components/Badge'
import { buildFinTable, finNotesOf, finRowItems } from '../../finTable'
import type { DealFull, ExtractedItem, KpiNode } from '../../types'

/** 長文のAIテキストを先頭n文に要約表示する */
function brief(text: string | null | undefined, n = 2): string {
  if (!text) return '－'
  const parts = text.split('。').filter((s) => s.trim())
  return parts.length <= n ? text : `${parts.slice(0, n).join('。')}。…`
}

const SCENARIO_KEY_COLOR: Record<string, string> = {
  A: 'bg-primary-container',
  B: 'bg-amber-700',
  C: 'bg-error',
}

/** 概要の各セクションカード。ヘッダー＝「▼ 見出し」＋状態バッジ＋対応タブへの「編集 →」リンク */
function SectionCard({ title, badges, editLabel, onEdit, children }: {
  title: string
  badges?: React.ReactNode
  editLabel: string
  onEdit: () => void
  children: React.ReactNode
}) {
  return (
    <section className="card mt-4 overflow-hidden first:mt-0">
      <div className="flex items-center justify-between border-b border-surface-container-high bg-surface-container-low/50 px-4 py-2.5">
        <span className="flex items-center gap-1.5 text-[13.5px] font-bold">
          <span className="text-[10px] text-primary-container">▼</span>
          {title}
        </span>
        <span className="flex items-center gap-2.5">
          {badges}
          <button
            className="flex items-center gap-0.5 text-[12px] font-medium text-primary-container hover:underline"
            onClick={onEdit}
            title={`${editLabel}タブで確認・修正する`}
          >
            編集
            <Icon name="arrow_forward" className="text-[14px]" />
          </button>
        </span>
      </div>
      {children}
    </section>
  )
}

export function OverviewTab({ full, onNavigate }: {
  full: DealFull
  onNavigate: (tab: string) => void
}) {
  const { deal } = full
  const items = full.items
  const fin = useMemo(() => buildFinTable(items), [items])

  // セクション別の未確定件数（バッジ表示用）
  const finItems = useMemo(() => items.filter((it) => fin.tableIds.has(it.id)), [items, fin])
  const finPending = finItems.filter((it) => it.status !== 'confirmed').length
  const finMismatch = finItems.filter((it) => it.mismatch).length
  const finNotes = useMemo(() => finNotesOf(items), [items])
  const bizItems = useMemo(
    () => items.filter((it) => !fin.tableIds.has(it.id) && !finNotes.some((n) => n.id === it.id)),
    [items, fin, finNotes],
  )
  const bizPending = bizItems.filter((it) => it.status !== 'confirmed').length

  const kpiConfirmed = deal.kpi_status === 'confirmed'
  const adopted = full.scenarios.filter((s) => s.adopted).length

  const basicInfo: [string, string][] = [
    ['スキーム', deal.deal_type ?? '－'],
    ['対象会社', deal.target || '－'],
    ['スポンサー', deal.sponsor ?? '－'],
    ['EV（買収総額）', deal.ev_mm != null ? `${deal.ev_mm.toLocaleString()}百万円` : '－'],
    ['シニアローン', deal.senior_mm != null
      ? `${deal.senior_mm.toLocaleString()}百万円${deal.our_commitment_mm != null ? `（本行 ${deal.our_commitment_mm.toLocaleString()}百万円）` : ''}`
      : '－'],
    ['エクイティ', deal.equity_mm != null ? `${deal.equity_mm.toLocaleString()}百万円` : '－'],
    ['レバレッジ／LTV', deal.initial_leverage != null ? `${deal.initial_leverage}x／${deal.ltv_pct}%` : '－'],
    ['クローズ予定日', deal.close_date?.replaceAll('-', '/') ?? '－'],
  ]

  // KPIツリー（親→子の階層をインデント付き数式リストで表示）
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
          className={`flex items-baseline gap-2 rounded px-2 py-1 text-[12.5px] ${n.star ? 'bg-amber-50' : ''}`}
          style={{ marginLeft: depth * 20 }}
        >
          <span className={`shrink-0 ${n.star ? 'text-amber-600' : 'text-outline-variant'}`}>
            {n.star ? '★' : '・'}
          </span>
          <span className={`shrink-0 font-bold ${n.star ? 'text-amber-900' : ''}`}>{n.label}</span>
          {n.formula ? (
            <span className="font-data-tabular text-on-surface-variant">＝ {n.formula.replace(/^[=＝]\s*/, '')}</span>
          ) : n.value_text ? (
            <span className="text-on-surface-variant">{n.value_text}</span>
          ) : null}
        </div>
        {renderKpiLines(n.node_id, depth + 1)}
      </div>
    ))

  // 財務テーブルの読み取り専用セル（クリックで財務ダイジェストタブへ）
  const finCell = (item: ExtractedItem | undefined, y: string, first: boolean) => {
    const v = item?.effective_values?.[y]
    return (
      <td
        key={y}
        onClick={item ? () => onNavigate('numbers') : undefined}
        className={`px-2 py-1.5 text-right ${first ? 'border-l border-surface-container-high' : ''} ${
          item ? 'cursor-pointer hover:bg-primary-fixed/30' : ''
        } ${item && item.status !== 'confirmed' ? 'bg-amber-50/70' : ''}`}
        title={item ? `${item.label}（クリックで事業・財務タブへ）` : undefined}
      >
        {v != null
          ? <span className="font-data-tabular">{v.toLocaleString()}</span>
          : <span className="text-outline-variant">－</span>}
      </td>
    )
  }

  return (
    <div>
      {/* ① 案件基本情報・事業要約 */}
      <SectionCard
        title="案件基本情報・事業要約"
        badges={bizPending > 0
          ? <Badge kind="warning">未確定 {bizPending}</Badge>
          : bizItems.length > 0 ? <Badge kind="success">✓ 確定済</Badge> : null}
        editLabel="事業・財務"
        onEdit={() => onNavigate('numbers')}
      >
        <div className="grid grid-cols-[380px_1fr] gap-6 px-4 py-3">
          <table className="self-start text-[12.5px]">
            <tbody>
              {basicInfo.map(([k, v]) => (
                <tr key={k} className="border-b border-surface-container-low last:border-0">
                  <td className="w-32 py-1.5 pr-3 align-top text-outline">{k}</td>
                  <td className="py-1.5 font-medium">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div>
            <div className="text-[11px] font-bold tracking-wider text-outline">事業要約</div>
            <p className="mt-1.5 text-[13px] leading-relaxed text-on-surface-variant">
              {deal.summary || '事業要約はまだ登録されていません。'}
            </p>
          </div>
        </div>
      </SectionCard>

      {/* ② 重要KPIとその構造（ツリー） */}
      <SectionCard
        title="重要KPIとその構造（ツリー）"
        badges={full.kpi_nodes.length === 0
          ? null
          : kpiConfirmed ? <Badge kind="success">✓ 確定済</Badge> : <Badge kind="warning">AI提案・レビュー待ち</Badge>}
        editLabel="KPIツリー"
        onEdit={() => onNavigate('kpi')}
      >
        <div className="px-4 py-3">
          {full.kpi_nodes.length > 0 ? (
            <div className="space-y-0.5">{renderKpiLines(null, 0)}</div>
          ) : (
            <div className="py-4 text-center text-[12px] text-outline">
              資料のAI解析が完了すると、KPI構造（Excel数式の構文解析結果）がここに表示されます。
            </div>
          )}
          {full.kpi_nodes.some((n) => n.star) && (
            <div className="mt-2 border-t border-surface-container-low pt-1.5 text-[11px] text-outline">
              ★＝最重要KPI（ストレスシナリオの起点）
            </div>
          )}
        </div>
      </SectionCard>

      {/* ③ 財務情報 */}
      <SectionCard
        title="財務情報"
        badges={
          <>
            {finPending > 0 && <Badge kind="warning">未確定 {finPending}</Badge>}
            {finMismatch > 0 && <Badge kind="error">⚠ 不整合 {finMismatch}</Badge>}
            {finItems.length > 0 && finPending === 0 && finMismatch === 0 && <Badge kind="success">✓ 確定済</Badge>}
          </>
        }
        editLabel="事業・財務"
        onEdit={() => onNavigate('numbers')}
      >
        {fin.hasRows ? (
          <>
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
                          <td className="whitespace-nowrap px-2 py-1.5 font-medium">
                            {r.label}
                            {anyUnconfirmed && <span className="ml-1 align-middle text-amber-600" title="未確定の値があります">●</span>}
                            {rowItems.some((it) => it.mismatch) && (
                              <Icon name="warning" className="ml-1 align-middle text-[13px] text-amber-600" />
                            )}
                          </td>
                          {fin.yearsAct.map((y, i) => finCell(r.kpiItem ?? r.items.act, y, i === 0))}
                          {fin.yearsBase.map((y, i) => finCell(r.kpiItem ?? r.items.base, y, i === 0))}
                          {fin.yearsSponsor.map((y, i) => finCell(r.kpiItem ? undefined : r.items.sponsor, y, i === 0))}
                        </tr>
                      )
                    }),
                  )}
                </tbody>
              </table>
            </div>
            <div className="border-t border-surface-container-low px-4 py-1.5 text-[11px] text-outline">
              薄い黄色のセル＝未確定。●＝未確定あり、⚠＝資料間の不整合あり。セルをクリックすると事業・財務タブで根拠を確認できます。
            </div>
          </>
        ) : (
          <div className="px-4 py-6 text-center text-[12px] text-outline">
            資料のAI解析が完了すると、財務情報（確定財務・ベースケース・スポンサーケース）がここに表示されます。
          </div>
        )}
        {/* 財務ハイライト・ケース前提差異（AI論述） */}
        {finNotes.length > 0 && (
          <div className="border-t border-surface-container-high">
            {finNotes.map((item) => (
              <div key={item.id} className="border-b border-surface-container-low px-4 py-3 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="text-[12px] font-bold text-on-surface-variant">{item.label}</span>
                  <span className="badge-base badge-ai !px-1.5 !py-0 !text-[10px]">AI推定・モデル再計算なし</span>
                </div>
                <p className="mt-1.5 whitespace-pre-line text-[12.5px] leading-relaxed text-on-surface-variant">{item.effective_text}</p>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      {/* ④ ストレス仮説とその根拠データ */}
      <SectionCard
        title="ストレス仮説とその根拠データ"
        badges={
          <>
            {full.scenarios.some((s) => s.origin === 'ai') && <Badge kind="ai">AI推定・モデル再計算なし</Badge>}
            {full.scenarios.length > 0 && <Badge kind={adopted > 0 ? 'success' : 'neutral'}>採用 {adopted}/{full.scenarios.length}</Badge>}
          </>
        }
        editLabel="ストレス仮説"
        onEdit={() => onNavigate('scenario')}
      >
        <div className="space-y-3 px-4 py-3">
          {full.scenarios.length === 0 && (
            <div className="py-4 text-center text-[12px] text-outline">
              KPI構造を確定すると、ストレスシナリオ（AI提案）がここに表示されます。
            </div>
          )}
          {full.scenarios.map((sc) => (
            <div key={sc.id} className={`rounded border border-surface-container-high ${!sc.adopted ? 'opacity-70' : ''}`}>
              <div className="flex items-center gap-2.5 border-b border-surface-container-low bg-surface-container-low/30 px-3 py-2">
                <span className={`flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full text-[12px] font-bold text-white ${SCENARIO_KEY_COLOR[sc.key] ?? 'bg-outline'}`}>
                  {sc.key}
                </span>
                <span className="min-w-0 flex-1 truncate text-[13px] font-bold">
                  {sc.title}
                  {sc.type_label && <span className="ml-1.5 text-[11px] font-normal text-outline">（{sc.type_label}）</span>}
                </span>
                <Badge kind={sc.origin === 'ai' ? 'ai' : 'neutral'}>{sc.origin === 'ai' ? 'AI推定' : '自分の仮説'}</Badge>
                <span className={`shrink-0 text-[11px] font-medium ${sc.adopted ? 'text-primary-container' : 'text-outline'}`}>
                  {sc.adopted ? '採用' : '不採用'}
                </span>
              </div>
              <ul className="space-y-1 px-3 py-2 text-[12px] leading-relaxed text-on-surface-variant">
                <li><b className="text-on-surface">・【KPIとリスク】</b>{brief(sc.cause)}</li>
                <li><b className="text-on-surface">・【ストレスと根拠】</b>{sc.change_text || '－'}（根拠：{brief(sc.change_basis, 1)}）</li>
                <li><b className="text-on-surface">・【インパクト】</b>{brief(sc.impact)}</li>
                <li><b className="text-on-surface">・【保全策・構造】</b>{brief(sc.safeguards)}</li>
                <li><b className="text-on-surface">・【Q&A】</b>{brief(sc.questions)}</li>
              </ul>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  )
}
