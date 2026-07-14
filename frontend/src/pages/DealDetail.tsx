import { useCallback, useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { Layout } from '../components/Layout'
import { Icon } from '../components/Icon'
import { ReviewStatusBadge, WorkStatusBadge } from '../components/Badge'
import { SlidePanel } from '../components/EvidencePanel'
import type { DealFull } from '../types'
import { NumbersTab } from './tabs/NumbersTab'
import { KpiTab } from './tabs/KpiTab'
import { ScenarioTab } from './tabs/ScenarioTab'
import { ExportTab } from './tabs/ExportTab'
import { MemoTab } from './tabs/MemoTab'

const TABS = [
  { key: 'numbers', label: '数値確定' },
  { key: 'kpi', label: 'KPI構造' },
  { key: 'scenario', label: 'シナリオ' },
  { key: 'export', label: 'エクスポート' },
  { key: 'memo', label: '審査相談メモ' },
]

const USER_NAMES: Record<string, string> = { tanaka: '田中', sato: '佐藤', takahashi: '高橋' }

function fmtDateTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function DealDetail() {
  const { id } = useParams()
  const dealId = Number(id)
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') ?? 'numbers'
  const [full, setFull] = useState<DealFull | null>(null)
  const [error, setError] = useState('')
  const [showHistory, setShowHistory] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setFull(await api.dealFull(dealId))
    } catch (e) {
      setError((e as Error).message)
    }
  }, [dealId])

  useEffect(() => { refresh() }, [refresh])

  if (error) {
    return <Layout><div className="p-10 text-center text-error">{error}</div></Layout>
  }
  if (!full) {
    return (
      <Layout>
        <div className="flex justify-center p-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-surface-container-high border-t-primary-container" />
        </div>
      </Layout>
    )
  }

  const { deal } = full
  const stage1Done = deal.progress.required > 0 && deal.progress.confirmed === deal.progress.required
  const kpiConfirmed = deal.kpi_status === 'confirmed'

  const headerInfo = [
    deal.deal_type,
    `借入人：${deal.borrower}`,
    `対象会社：${deal.target}`,
    deal.ev_mm != null ? `EV ${(deal.ev_mm / 100).toLocaleString()}億円` : null,
    deal.senior_mm != null
      ? `シニア${(deal.senior_mm / 100).toLocaleString()}億円${deal.our_commitment_mm != null ? `（本行${(deal.our_commitment_mm / 100).toLocaleString()}億円）` : ''}`
      : null,
    deal.initial_leverage != null ? `レバレッジ ${deal.initial_leverage}x／LTV ${deal.ltv_pct}%` : null,
  ].filter(Boolean)

  return (
    <Layout breadcrumb={<><span className="text-outline-variant">/</span><span className="max-w-64 truncate font-medium">{deal.name}</span></>}>
      <div className="mx-auto max-w-[1280px]">
        {/* 案件ヘッダー */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-[22px] font-bold">{deal.name}</h1>
              <ReviewStatusBadge status={deal.review_status} />
              <WorkStatusBadge status={deal.work_status} />
            </div>
            <div className="mt-1.5 flex flex-wrap items-center gap-x-2 text-[12px] text-on-surface-variant">
              {headerInfo.map((t, i) => (
                <span key={i} className="flex items-center gap-2">
                  {i > 0 && <span className="text-outline-variant">｜</span>}{t}
                </span>
              ))}
            </div>
          </div>
          <button
            className="btn-secondary !py-1.5 text-[12px]"
            onClick={() => setShowHistory(true)}
            title="操作履歴（誰が・いつ・何を）"
          >
            <Icon name="history" className="text-[16px]" /> 操作履歴
          </button>
        </div>

        {/* タブ */}
        <div className="mt-4 flex gap-1 border-b border-surface-container-high">
          {TABS.map((t) => {
            const locked = (t.key === 'kpi' && !stage1Done)
              || (t.key === 'scenario' && !kpiConfirmed)
              || (t.key === 'export' && !kpiConfirmed)
            return (
              <button
                key={t.key}
                onClick={() => setSearchParams({ tab: t.key })}
                className={`flex items-center gap-1 border-b-2 px-4 pb-2 pt-1 text-[13px] transition-colors ${
                  tab === t.key
                    ? 'border-primary-container font-bold text-primary-container'
                    : 'border-transparent text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {t.label}
                {locked && <Icon name="lock" className="text-[13px] text-outline-variant" />}
              </button>
            )
          })}
        </div>

        {/* タブ本体 */}
        <div className="mt-4">
          {tab === 'numbers' && <NumbersTab full={full} refresh={refresh} dealId={dealId} />}
          {tab === 'kpi' && <KpiTab full={full} refresh={refresh} dealId={dealId} stage1Done={stage1Done} />}
          {tab === 'scenario' && <ScenarioTab full={full} refresh={refresh} dealId={dealId} />}
          {tab === 'export' && <ExportTab full={full} refresh={refresh} dealId={dealId} />}
          {tab === 'memo' && <MemoTab full={full} refresh={refresh} dealId={dealId} />}
        </div>
      </div>

      {/* 操作履歴パネル（トレーサビリティ：誰が・いつ・何を） */}
      {showHistory && (
        <SlidePanel title="操作履歴" onClose={() => setShowHistory(false)}>
          <div className="space-y-0">
            {full.history.map((h) => (
              <div key={h.id} className="border-b border-surface-container-low py-2.5 last:border-0">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] font-bold">{h.action}</span>
                  <span className="font-data-tabular text-[11px] text-outline">{fmtDateTime(h.at)}</span>
                </div>
                <div className="mt-0.5 text-[12px] text-on-surface-variant">{h.detail}</div>
                <div className="mt-0.5 text-[11px] text-outline">{USER_NAMES[h.user ?? ''] ?? h.user}</div>
              </div>
            ))}
            {full.history.length === 0 && <div className="py-8 text-center text-[12px] text-outline">履歴はまだありません</div>}
          </div>
        </SlidePanel>
      )}
    </Layout>
  )
}
