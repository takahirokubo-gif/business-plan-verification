import { useState } from 'react'
import { api } from '../../api'
import { Icon } from '../../components/Icon'
import { ChatPanel } from '../../components/ChatPanel'
import { useUser } from '../../context/UserContext'
import type { ChatDiff, DealFull, Scenario } from '../../types'

function AdoptToggle({ adopted, onChange }: { adopted: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onChange(!adopted) }}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${adopted ? 'bg-primary-container' : 'bg-outline-variant'}`}
      title={adopted ? '採用中（クリックで不採用）' : '不採用（クリックで採用）'}
    >
      <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${adopted ? 'left-[22px]' : 'left-0.5'}`} />
    </button>
  )
}

function Section({ no, title, children, note }: {
  no: string; title: string; children: React.ReactNode; note?: string
}) {
  return (
    <div className="rounded border border-surface-container-low bg-surface-container-low/40 px-3 py-2">
      <div className="flex items-center gap-1.5 text-[11px] font-bold text-on-surface-variant">
        {no} {title}
        {note && (
          <span className="badge-base badge-neutral">
            <Icon name="smart_toy" className="text-[11px]" /> {note}
          </span>
        )}
      </div>
      <div className="mt-1 text-[12.5px] leading-relaxed">{children}</div>
    </div>
  )
}

export function ScenarioTab({ full, refresh, dealId }: {
  full: DealFull
  refresh: () => Promise<void>
  dealId: number
}) {
  const { userKey } = useUser()
  const scenarios = full.scenarios
  const [openKeys, setOpenKeys] = useState<Set<string>>(new Set())
  const nodeLabel = (id: string) => full.kpi_nodes.find((n) => n.node_id === id)?.label ?? id

  const toggleOpen = (key: string) => {
    setOpenKeys((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const adoptToggle = async (sc: Scenario, adopted: boolean) => {
    await api.scenarioAdopt(dealId, sc.key, adopted, userKey)
    await refresh()
  }

  const clearStale = async (sc: Scenario) => {
    await api.scenarioClearStale(dealId, sc.key, userKey)
    await refresh()
  }

  const renderDiff = (diff: ChatDiff) => {
    if (diff.type === 'add_card') {
      const card = diff.card as Record<string, string>
      return (
        <div className="space-y-1 text-[12px]">
          <div className="flex items-center gap-1.5">
            <span className="badge-base badge-success !px-1.5 !py-0 !text-[10px]">カード追加</span>
            <span className="font-bold">{card.title}</span>
          </div>
          <div className="text-[11px] text-on-surface-variant">変化幅：{card.change ?? card.change_text}</div>
          <div className="text-[11px] text-on-surface-variant">影響（AI推定）：{card.impact}</div>
        </div>
      )
    }
    if (diff.type === 'update_card') {
      const fields = diff.fields as Record<string, string>
      const cardKey = diff.card_key as string
      const target = scenarios.find((s) => s.key === cardKey)
      const fieldLabels: Record<string, string> = {
        change: '③ 変化幅', change_text: '③ 変化幅', impact: '④ 返済能力への影響',
        safeguards: '⑤ 保全策', cause: '① 発生要因', questions: '⑤ 確認事項',
      }
      const oldOf = (k: string): string | null => {
        if (!target) return null
        if (k === 'change' || k === 'change_text') return target.change_text
        return (target as unknown as Record<string, string | null>)[k] ?? null
      }
      return (
        <div className="space-y-2 text-[12px]">
          <div className="font-bold">シナリオ{cardKey}：{target?.title}</div>
          {Object.entries(fields).map(([k, v]) => (
            <div key={k}>
              <div className="text-[11px] font-medium text-on-surface-variant">{fieldLabels[k] ?? k}</div>
              {oldOf(k) && (
                <div className="mt-0.5 rounded bg-red-50 px-2 py-1 text-[11px] text-red-800 line-through decoration-red-300">
                  {oldOf(k)}
                </div>
              )}
              <div className="mt-0.5 rounded bg-green-100 px-2 py-1 text-[11px] text-green-900">{v}</div>
            </div>
          ))}
        </div>
      )
    }
    return <div className="text-[12px]">{JSON.stringify(diff)}</div>
  }

  const applyDiff = async (diff: ChatDiff) => {
    await api.scenariosApply(dealId, diff, userKey)
    if (diff.type === 'add_card') {
      const key = (diff.card as { key?: string }).key
      if (key) setOpenKeys((prev) => new Set(prev).add(key))
    }
    await refresh()
  }

  return (
    <div className="grid grid-cols-[1fr_360px] gap-4">
      <div>
        <div className="mb-3 flex items-center justify-between">
          <div className="text-[14px] font-bold">検証シナリオ</div>
          <div className="text-[11px] text-outline">
            行をクリックで詳細を展開。採用トグルON＝確定シナリオ（エクスポート対象）。
          </div>
        </div>

        {/* シナリオ一覧（アコーディオン行） */}
        <div className="card divide-y divide-surface-container-low">
          {scenarios.map((sc) => {
            const findings = full.findings.filter((f) => f.target_type === 'scenario' && f.target_key === sc.key)
            const open = openKeys.has(sc.key)
            return (
              <div key={sc.id}>
                {/* 行 */}
                <div
                  className={`flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-surface-container-low/50 ${!sc.adopted ? 'opacity-70' : ''}`}
                  onClick={() => toggleOpen(sc.key)}
                >
                  <Icon name={open ? 'expand_more' : 'chevron_right'} className="shrink-0 text-[20px] text-outline" />
                  <span className="w-8 shrink-0 text-[12px] font-bold text-outline">S{sc.key}</span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13.5px] font-bold">{sc.title}</div>
                    <div className="mt-0.5 flex items-center gap-2 text-[11px] text-outline">
                      <span>
                        {sc.origin === 'ai' ? 'AI推奨' : '自分の仮説'}
                        {sc.type_label && sc.type_label !== (sc.origin === 'ai' ? 'AI推奨' : '自分の仮説') && `｜${sc.type_label}`}
                      </span>
                      {sc.affected_kpis.length > 0 && (
                        <span className="truncate">
                          影響KPI：{sc.affected_kpis.map(nodeLabel).join('・')}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {findings.length > 0 && (
                      <span className="badge-base badge-neutral" title="前回審査相談での指摘あり">
                        <Icon name="feedback" className="text-[12px]" /> 指摘{findings.length}
                      </span>
                    )}
                    {sc.stale_reason && (
                      <span className="badge-base badge-warning" title={sc.stale_reason}>
                        <Icon name="warning" className="text-[12px]" /> 上流変更
                      </span>
                    )}
                    <span className={`text-[11px] font-medium ${sc.adopted ? 'text-primary-container' : 'text-outline'}`}>
                      {sc.adopted ? '採用' : '不採用'}
                    </span>
                    <AdoptToggle adopted={sc.adopted} onChange={(v) => adoptToggle(sc, v)} />
                  </div>
                </div>

                {/* 詳細（アコーディオン展開） */}
                {open && (
                  <div className="border-t border-surface-container-low bg-surface-container-low/20 px-4 pb-4 pt-3">
                    {sc.stale_reason && (
                      <div className="mb-3 flex items-center justify-between rounded border border-amber-300 bg-amber-50 px-3 py-2">
                        <div className="flex items-center gap-1.5 text-[12px] text-amber-800">
                          <Icon name="warning" className="text-[15px]" /> {sc.stale_reason}
                        </div>
                        <button
                          className="shrink-0 text-[11px] font-medium text-amber-800 underline"
                          onClick={(e) => { e.stopPropagation(); clearStale(sc) }}
                        >
                          再確認済みにする
                        </button>
                      </div>
                    )}
                    {findings.map((f) => (
                      <div key={f.id} className="mb-3 rounded border border-surface-container-high bg-white px-3 py-2 text-[12px]">
                        <div className="flex items-center gap-1 font-bold text-on-surface-variant">
                          <Icon name="feedback" className="text-[13px]" />
                          前回審査相談での指摘（{f.meeting_date?.replaceAll('-', '/')}）
                        </div>
                        <p className="mt-0.5 text-on-surface-variant">{f.text}</p>
                      </div>
                    ))}
                    {!sc.adopted && sc.rejection_note && (
                      <div className="mb-3 rounded bg-surface-container-low px-3 py-2 text-[12px] text-on-surface-variant">
                        <span className="font-medium">不採用メモ：</span>{sc.rejection_note}
                      </div>
                    )}
                    <div className="space-y-2">
                      <Section no="①" title="シナリオ名・発生要因">{sc.cause}</Section>
                      <Section no="②" title="影響を受けるKPI">
                        <div className="flex flex-wrap gap-1.5">
                          {sc.affected_kpis.length ? sc.affected_kpis.map((k) => (
                            <span key={k} className="badge-base badge-neutral">{nodeLabel(k)}</span>
                          )) : <span className="text-outline">－（PLへの直接影響）</span>}
                        </div>
                      </Section>
                      <Section no="③" title="KPIの変化幅と根拠">
                        <div className="font-medium">{sc.change_text}</div>
                        <div className="mt-0.5 text-[11.5px] text-on-surface-variant">根拠：{sc.change_basis}</div>
                      </Section>
                      <Section no="④" title="返済能力への影響" note="AI推定・モデル再計算なし">
                        {sc.impact}
                      </Section>
                      <Section no="⑤" title="保全策・確認事項">
                        <div>{sc.safeguards}</div>
                        <div className="mt-0.5 text-[11.5px] text-on-surface-variant">確認事項：{sc.questions}</div>
                      </Section>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <div className="mt-4 rounded border border-dashed border-outline-variant p-4 text-center text-[12px] text-outline">
          <Icon name="add_circle" className="mr-1 align-middle text-[16px]" />
          自分の仮説シナリオを追加するには、右のチャットに一言（例：「大口派遣先（構成比28%）が契約終了したら」）を
          入力してください。標準5部構成に展開されます。
        </div>
      </div>

      <div className="h-[calc(100vh-220px)] min-h-[480px] sticky top-16">
        <ChatPanel
          dealId={dealId}
          context="scenario"
          suggestions={full.chat_suggestions.scenario}
          renderDiff={renderDiff}
          onApply={applyDiff}
          title="AIとブラッシュアップ"
          targetLabel="対象シナリオ"
          targetOptions={scenarios.map((s) => ({
            value: s.key,
            label: `シナリオ${s.key}：${s.title.length > 16 ? `${s.title.slice(0, 16)}…` : s.title}`,
          }))}
        />
      </div>
    </div>
  )
}
