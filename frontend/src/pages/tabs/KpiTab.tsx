import { useMemo, useState } from 'react'
import { api } from '../../api'
import { Icon } from '../../components/Icon'
import { OriginBadge, Badge } from '../../components/Badge'
import { ChatPanel } from '../../components/ChatPanel'
import { EvidenceBlock, SlidePanel } from '../../components/EvidencePanel'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { useUser } from '../../context/UserContext'
import { resolveKpiNode } from '../../kpiMatch'
import type { ChatDiff, DealFull, KpiNode } from '../../types'

/** シナリオキー（A/B/C…）ごとの表示色 */
const SCENARIO_CHIP: Record<string, string> = {
  A: 'bg-sky-100 text-sky-800',
  B: 'bg-violet-100 text-violet-800',
  C: 'bg-teal-100 text-teal-800',
}

/** カード右端に出す「最新の値」。value_text に数式が混ざっている場合は
 *  数式より前の値部分だけを出す（数式・出典はサイドパネルで確認）。 */
function latestValue(node: KpiNode): string {
  const t = node.value_text ?? ''
  if (!t) return ''
  if (!t.includes('=')) return t
  const head = t.split('=')[0].replace(/[：:／/・、]\s*$/, '').trim()
  // 「FY27以降」のような数値のないラベルだけが残った場合は出さない
  return /\d/.test(head) ? head : ''
}

function NodeCard({ node, depth, onSelect, highlight, scenarioKeys, hasChildren, collapsed, onToggle }: {
  node: KpiNode
  depth: number
  onSelect: (n: KpiNode) => void
  highlight?: boolean
  scenarioKeys: { key: string; title: string }[]
  hasChildren: boolean
  collapsed: boolean
  onToggle: () => void
}) {
  const important = node.star
  return (
    <div
      onClick={(e) => { e.stopPropagation(); onSelect(node) }}
      className={`flex cursor-pointer items-center gap-2 rounded border px-3 py-2 transition-colors ${
        highlight
          ? 'border-green-400 bg-green-50'
          : important
            ? 'border-amber-300 bg-amber-50 hover:border-amber-500'
            : 'border-surface-container-high bg-white hover:border-primary-container'
      }`}
      style={{ marginLeft: depth * 24 }}
    >
      {hasChildren ? (
        <button
          onClick={(e) => { e.stopPropagation(); onToggle() }}
          className="-ml-1 rounded p-0.5 hover:bg-black/5"
          title={collapsed ? '展開する' : '折りたたむ'}
        >
          <Icon name={collapsed ? 'chevron_right' : 'expand_more'} className="text-[16px] text-outline" />
        </button>
      ) : (
        depth > 0 && <Icon name="subdirectory_arrow_right" className="-ml-1 text-[14px] text-outline-variant" />
      )}
      <span className={`text-[13px] font-medium ${important ? 'text-amber-900' : ''}`}>{node.label}</span>
      {important && (
        <span className="rounded bg-amber-200/80 px-1.5 py-0.5 text-[10px] font-bold text-amber-900">重要KPI</span>
      )}
      {scenarioKeys.map((s) => (
        <span
          key={s.key}
          title={`シナリオ${s.key}：${s.title} で使用`}
          className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${SCENARIO_CHIP[s.key] ?? 'bg-surface-container text-on-surface-variant'}`}
        >
          {s.key}
        </span>
      ))}
      {collapsed && hasChildren && <span className="text-[10px] text-outline">…</span>}
      <span className="font-data-tabular ml-auto text-[12px] text-on-surface-variant">{latestValue(node)}</span>
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
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
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

  // ノードID → 使用しているシナリオ（affected_kpis から逆引き。表記ゆれはあいまい一致で解決）
  const scenariosOf = useMemo(() => {
    const map = new Map<string, { key: string; title: string }[]>()
    for (const sc of full.scenarios) {
      for (const aid of sc.affected_kpis ?? []) {
        const node = resolveKpiNode(nodes, aid)
        if (!node) continue
        if (!map.has(node.node_id)) map.set(node.node_id, [])
        if (!map.get(node.node_id)!.some((s) => s.key === sc.key)) {
          map.get(node.node_id)!.push({ key: sc.key, title: sc.title })
        }
      }
    }
    return map
  }, [full.scenarios, nodes])

  const toggleCollapse = (id: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const renderTree = (parent: string | null, depth: number): React.ReactNode =>
    (childrenOf.get(parent) ?? []).map((n) => {
      const hasChildren = (childrenOf.get(n.node_id) ?? []).length > 0
      const isCollapsed = collapsed.has(n.node_id)
      return (
        <div key={n.node_id} className="space-y-1.5">
          <NodeCard
            node={n}
            depth={depth}
            onSelect={setSelected}
            highlight={lastAdded === n.node_id}
            scenarioKeys={scenariosOf.get(n.node_id) ?? []}
            hasChildren={hasChildren}
            collapsed={isCollapsed}
            onToggle={() => toggleCollapse(n.node_id)}
          />
          {!isCollapsed && <div className="space-y-1.5">{renderTree(n.node_id, depth + 1)}</div>}
        </div>
      )
    })

  const renderDiff = (diff: ChatDiff) => {
    // AIの応答形式が想定と異なる場合に画面を落とさない（不明な形はJSONで見せる）
    if (diff.type === 'add_node' && diff.node) {
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
    if (diff.type === 'add_node') setLastAdded((diff.node as { id?: string } | undefined)?.id ?? null)
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
              {deal.kpi_status !== 'confirmed' && <Badge kind="warning">レビュー待ち</Badge>}
            </div>
            <div className="flex items-center gap-2">
              <button
                className="btn-secondary !py-1.5 !text-[12px]"
                onClick={() => {
                  const parents = nodes.filter((n) => (childrenOf.get(n.node_id) ?? []).length > 0)
                  setCollapsed((prev) => (prev.size > 0 ? new Set() : new Set(parents.map((n) => n.node_id))))
                }}
              >
                <Icon name={collapsed.size > 0 ? 'unfold_more' : 'unfold_less'} className="text-[16px]" />
                {collapsed.size > 0 ? 'すべて展開' : 'すべて折りたたむ'}
              </button>
              <button
                className="btn-primary !py-1.5 !text-[12px]"
                disabled={!stage1Done}
                onClick={() => setConfirmOpen(true)}
              >
                <Icon name="check" className="text-[16px]" />
                {deal.kpi_status === 'confirmed' ? 'KPIを再確定' : 'KPIを確定'}
              </button>
            </div>
          </div>
          <div className="p-4">
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
              {selected.label}
              {selected.star && (
                <span className="rounded bg-amber-200/80 px-1.5 py-0.5 text-[10px] font-bold text-amber-900">重要KPI</span>
              )}
            </div>
          }
          onClose={() => setSelected(null)}
        >
          <div className="mb-3 flex flex-wrap gap-1.5">
            <OriginBadge origin={selected.origin} />
            {selected.badge && <Badge kind="neutral">{selected.badge}</Badge>}
            {selected.added_via_chat && <Badge kind="neutral">チャットで追加</Badge>}
            {(scenariosOf.get(selected.node_id) ?? []).map((s) => (
              <span key={s.key} className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${SCENARIO_CHIP[s.key] ?? 'bg-surface-container text-on-surface-variant'}`}>
                シナリオ{s.key}：{s.title}
              </span>
            ))}
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
