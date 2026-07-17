import type { KpiNode } from './types'

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/** シナリオの affected_kpis の表記ゆれを吸収してKPIノードを解決する。
 *  実AIは「B31（リピート率）」のようにIDとラベルを混ぜて返すことがあるため、
 *  ①ID完全一致 → ②ID一致（単語境界つき・最長一致。B3がB31を誤って拾わない）
 *  → ③ラベル一致（括弧内表記にも対応・最長一致）の順で探す。 */
export function resolveKpiNode(nodes: KpiNode[], aid: string): KpiNode | undefined {
  const exact = nodes.find((n) => n.node_id === aid)
  if (exact) return exact
  const byId = nodes
    .filter((n) =>
      n.node_id.length >= 2 &&
      new RegExp(`(^|[^A-Za-z0-9_])${escapeRegExp(n.node_id)}([^A-Za-z0-9_]|$)`).test(aid))
    .sort((a, b) => b.node_id.length - a.node_id.length)[0]
  if (byId) return byId
  // 「B31（リピート率）」→ リピート率 を取り出してラベルで探す
  const inParen = aid.match(/（(.+?)）/)?.[1] ?? aid
  return nodes.find((n) => n.label === inParen)
    ?? nodes
      .filter((n) => n.label.includes(inParen) || inParen.includes(n.label))
      .sort((a, b) => b.label.length - a.label.length)[0]
}

/** 表示用：affected_kpis のエントリをノードのラベルに解決（できなければ元の文字列） */
export function kpiLabelOf(nodes: KpiNode[], aid: string): string {
  return resolveKpiNode(nodes, aid)?.label ?? aid
}
