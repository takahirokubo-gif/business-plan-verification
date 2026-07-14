import { useMemo, useState } from 'react'
import { api } from '../../api'
import { Icon } from '../../components/Icon'
import { OriginBadge, Badge } from '../../components/Badge'
import { ChatPanel } from '../../components/ChatPanel'
import { EvidenceBlock, SlidePanel } from '../../components/EvidencePanel'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { useUser } from '../../context/UserContext'
import type { ChatDiff, DealFull, KpiNode } from '../../types'

function NodeCard({ node, depth, onSelect, highlight }: {
  node: KpiNode
  depth: number
  onSelect: (n: KpiNode) => void
  highlight?: boolean
}) {
  return (
    <div
      onClick={(e) => { e.stopPropagation(); onSelect(node) }}
      className={`flex cursor-pointer items-center gap-2 rounded border px-3 py-2 transition-colors hover:border-primary-container ${
        highlight ? 'border-green-400 bg-green-50' : 'border-surface-container-high bg-white'
      }`}
      style={{ marginLeft: depth * 24 }}
    >
      {depth > 0 && <Icon name="subdirectory_arrow_right" className="-ml-1 text-[14px] text-outline-variant" />}
      {node.star && <Icon name="star" className="text-[16px] text-amber-500" fill />}
      <span className="text-[13px] font-medium">{node.label}</span>
      {node.badge && <Badge kind="neutral">{node.badge}</Badge>}
      <OriginBadge origin={node.origin} />
      {node.added_via_chat && <Badge kind="neutral">チャット追加</Badge>}
      <span className="font-data-tabular ml-auto text-[12px] text-on-surface-variant">{node.value_text}</span>
    </div>
  )
}

export function KpiTab({ full, refresh, dealId, stage1Done }: {
  full: DealFull
  refresh: () => Promise<void>
  dealId: number
  stage1Done: boolean
}) {
  const { userKey } = useUser()
  const [selected, setSelected] = useState<KpiNode | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [lastAdded, setLastAdded] = useState<string | null>(null)
  const deal = full.deal
  const nodes = full.kpi_nodes

  const childrenOf = useMemo(() => {
    const map = new Map<string | null, KpiNode[]>()
    for (const n of nodes) {
      const key = n.parent_id ?? null
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(n)
    }
    return map
  }, [nodes])

  const renderTree = (parent: string | null, depth: number): React.ReactNode =>
    (childrenOf.get(parent) ?? []).map((n) => (
      <div key={n.node_id} className="space-y-1.5">
        <NodeCard node={n} depth={depth} onSelect={setSelected} highlight={lastAdded === n.node_id} />
        <div className="space-y-1.5">{renderTree(n.node_id, depth + 1)}</div>
      </div>
    ))

  const renderDiff = (diff: ChatDiff) => {
    if (diff.type === 'add_node') {
      const node = diff.node as unknown as KpiNode & { parent?: string }
      const parentLabel = nodes.find((n) => n.node_id === (node as { parent?: string }).parent)?.label
      return (
        <div className="text-[12px]">
          <div className="flex items-center gap-1.5 rounded border border-green-400 bg-white px-2 py-1.5">
            <span className="badge-base badge-success !px-1.5 !py-0 !text-[10px]">追加</span>
            <span className="font-medium">{node.label}</span>
            {node.badge && <Badge kind="ai">{node.badge}</Badge>}
          </div>
          <div className="mt-1 text-[11px] text-on-surface-variant">
            親ノード：{parentLabel ?? '売上高'}／{node.value_text}
          </div>
        </div>
      )
    }
    if (diff.type === 'star_change') {
      const rm = (diff.remove as string[] | undefined) ?? []
      const ad = (diff.add as string[] | undefined) ?? []
      const label = (id: string) => nodes.find((n) => n.node_id === id)?.label ?? id
      return (
        <div className="space-y-1 text-[12px]">
          {rm.map((id) => (
            <div key={id} className="flex items-center gap-1.5">
              <span className="badge-base badge-warning !px-1.5 !py-0 !text-[10px]">★解除</span>
              {label(id)}
            </div>
          ))}
          {ad.map((id) => (
            <div key={id} className="flex items-center gap-1.5">
              <span className="badge-base badge-success !px-1.5 !py-0 !text-[10px]">★付与</span>
              {label(id)}
            </div>
          ))}
        </div>
      )
    }
    return <div className="text-[12px]">{JSON.stringify(diff)}</div>
  }

  const applyDiff = async (diff: ChatDiff) => {
    await api.kpiApply(dealId, diff, userKey)
    if (diff.type === 'add_node') setLastAdded((diff.node as { id: string }).id)
    await refresh()
  }

  const kpiFindings = full.findings.filter((f) => f.target_type === 'kpi')

  return (
    <div className="grid grid-cols-[1fr_360px] gap-4">
      <div>
        {!stage1Done && (
          <div className="mb-3 flex items-center gap-2 rounded border border-amber-300 bg-amber-50 px-4 py-2.5 text-[13px] text-amber-800">
            <Icon name="lock" className="text-[16px]" />
            数値確定タブで必須項目をすべて確定すると、KPI構造を確定できます（表示は可能です）。
          </div>
        )}
        {deal.kpi_stale_reason && (
          <div className="mb-3 flex items-center justify-between rounded border border-amber-300 bg-amber-50 px-4 py-2.5">
            <div className="flex items-center gap-2 text-[13px] text-amber-800">
              <Icon name="warning" className="text-[18px]" /> {deal.kpi_stale_reason}
            </div>
            <button
              className="btn-secondary !py-1 !text-[12px]"
              onClick={async () => { await api.kpiClearStale(dealId, userKey); await refresh() }}
            >
              再確認して警告を解除
            </button>
          </div>
        )}

        <div className="card">
          <div className="flex items-center justify-between border-b border-surface-container-high px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="text-[14px] font-bold">
                KPI構造{deal.kpi_status === 'confirmed' ? '' : '（AI提案）'}
              </span>
              {deal.kpi_status === 'confirmed' ? (
                <Badge kind="success">
                  確定済み（{deal.kpi_confirmed_by === 'tanaka' ? '田中' : deal.kpi_confirmed_by}・
                  {deal.kpi_confirmed_at ? new Date(deal.kpi_confirmed_at).toLocaleDateString('ja-JP') : ''}）
                </Badge>
              ) : (
                <Badge kind="warning">レビュー待ち</Badge>
              )}
            </div>
            <button
              className="btn-primary !py-1.5 !text-[12px]"
              disabled={!stage1Done}
              onClick={() => setConfirmOpen(true)}
            >
              <Icon name="check" className="text-[16px]" />
              {deal.kpi_status === 'confirmed' ? 'KPIを再確定' : 'KPIを確定'}
            </button>
          </div>
          <div className="p-4">
            <div className="mb-3 text-[11px] text-outline">
              ★＝重要KPI（リスクドライバー）。財務モデルの数式の構文解析（再計算なし）と
              DDレポートの定性情報から生成。ノードをクリックすると根拠を表示します。
            </div>
            <div className="space-y-1.5">{renderTree(null, 0)}</div>
          </div>
        </div>

        {kpiFindings.map((f) => (
          <div key={f.id} className="mt-3 rounded border border-surface-container-high bg-surface-container-low/60 p-3 text-[12px]">
            <div className="flex items-center gap-1 font-bold text-on-surface-variant">
              <Icon name="feedback" className="text-[14px]" /> 前回審査相談での指摘（KPI構造）
            </div>
            <p className="mt-1 text-on-surface-variant">{f.text}</p>
          </div>
        ))}
      </div>

      {/* チャットパネル */}
      <div className="h-[calc(100vh-220px)] min-h-[480px] sticky top-16">
        <ChatPanel
          dealId={dealId}
          context="kpi"
          suggestions={full.chat_suggestions.kpi}
          renderDiff={renderDiff}
          onApply={applyDiff}
          title="AIと修正する"
          targetLabel="対象ブランチ"
          targetOptions={nodes
            .filter((n) => nodes.some((c) => c.parent_id === n.node_id))
            .map((n) => ({ value: n.node_id, label: n.label }))}
        />
      </div>

      {/* ノード根拠パネル */}
      {selected && (
        <SlidePanel
          title={
            <div className="flex items-center gap-2">
              {selected.star && <Icon name="star" className="text-[18px] text-amber-500" fill />}
              {selected.label}
            </div>
          }
          onClose={() => setSelected(null)}
        >
          <div className="mb-3 flex flex-wrap gap-1.5">
            <OriginBadge origin={selected.origin} />
            {selected.badge && <Badge kind="neutral">{selected.badge}</Badge>}
            {selected.added_via_chat && <Badge kind="neutral">チャットで追加</Badge>}
          </div>
          {selected.value_text && (
            <div className="mb-3 rounded bg-surface-container-low/60 p-3">
              <div className="text-[11px] text-outline">値</div>
              <div className="font-data-tabular text-[17px] font-bold text-primary-container">{selected.value_text}</div>
            </div>
          )}
          {selected.formula && (
            <div className="mb-4 rounded border border-surface-container-high p-3">
              <div className="text-[11px] text-outline">構造（数式・再計算なし）</div>
              <div className="font-data-tabular mt-1 text-[12px]">{selected.formula}</div>
            </div>
          )}
          {selected.evidence && <EvidenceBlock evidence={selected.evidence} />}
        </SlidePanel>
      )}

      <ConfirmDialog
        open={confirmOpen}
        title="KPI構造を確定しますか？"
        confirmLabel="確定する"
        onConfirm={async () => {
          setConfirmOpen(false)
          await api.kpiConfirm(dealId, userKey)
          await refresh()
        }}
        onCancel={() => setConfirmOpen(false)}
      >
        確定したKPI構造は、シナリオ検討（ステージ3）の入力になります。
        確定者として記録されます：<b>{userName(userKey)}</b>
      </ConfirmDialog>
    </div>
  )
}

function userName(key: string): string {
  return { tanaka: '田中', sato: '佐藤', takahashi: '高橋' }[key] ?? key
}
