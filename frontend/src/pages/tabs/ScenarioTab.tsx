import { useMemo, useState } from 'react'
import { api } from '../../api'
import { Icon } from '../../components/Icon'
import { ChatPanel } from '../../components/ChatPanel'
import { SlidePanel } from '../../components/EvidencePanel'
import { FinTableView } from '../../components/FinTableView'
import { useUser } from '../../context/UserContext'
import { buildFinTable } from '../../finTable'
import { kpiLabelOf, resolveKpiNode } from '../../kpiMatch'
import type { ChatDiff, DealFull, KpiNode, Scenario } from '../../types'

/** 長文のAIテキストを先頭n文に要約表示する（全文はトグルで） */
function brief(text: string | null | undefined, n = 2): string {
  if (!text) return '－'
  const parts = text.split('。').filter((s) => s.trim())
  return parts.length <= n ? text : `${parts.slice(0, n).join('。')}。…`
}

/** KPIノードの現在値をテキストから拾う（例: '88%（FY26実績）' → 88, '%'）。決定的なパースのみ。
 *  年度表記（FY26・2026/3期 等）の数字を値と誤認しないよう先に除去する */
function parseBase(valueText?: string | null): { value: number; suffix: string } | null {
  if (!valueText) return null
  const cleaned = valueText.replace(/,/g, '').replace(/FY\d+|\d{4}\/\d+期|\d{4}年\d*月?/g, '')
  const m = cleaned.match(/(-?\d+(?:\.\d+)?)\s*(%|％|百万円|千円|億円|名|人|回|円|pt)?/)
  if (!m) return null
  return { value: parseFloat(m[1]), suffix: m[2] === '％' ? '%' : (m[2] ?? '') }
}

/** 変化幅テキストからそのKPIの±%を拾う（例: '稼働率-15%・新規採用数-20%'）。
 *  誤計算を避けるため、KPIラベル近傍で見つかった符号付き%のみ採用
 *  （ラベルが本文に無い場合は全文フォールバックせず null＝試算しない） */
function parseChangePct(changeText: string | null | undefined, label: string): number | null {
  if (!changeText) return null
  const core = label.replace(/（.*/, '')
  const idx = changeText.indexOf(core)
  if (idx < 0) return null
  const scope = changeText.slice(idx, idx + core.length + 25)
  const m = scope.match(/([+＋▲△\-−])\s*(\d+(?:\.\d+)?)\s*[%％]/)
  if (!m) return null
  const sign = m[1] === '+' || m[1] === '＋' ? 1 : -1
  return sign * parseFloat(m[2])
}

/** 「76%横置きから、例えば74%水準へ低下」「88%→80%」のような A→B 型の変化記述を
 *  ラベル近傍から拾う（KPIラベルの後ろ60文字以内のみ・誤マッチ防止） */
function parseArrowNear(text: string, label: string): { from: number; to: number } | null {
  const core = label.replace(/（.*/, '')
  const idx = text.indexOf(core)
  if (idx < 0) return null
  const scope = text.slice(idx, idx + core.length + 60).replace(/,/g, '')
  const m = scope.match(/(\d+(?:\.\d+)?)\s*[%％].{0,14}?(?:から|→).{0,10}?(\d+(?:\.\d+)?)\s*[%％]/)
  return m ? { from: parseFloat(m[1]), to: parseFloat(m[2]) } : null
}

function fmtNum(v: number, suffix: string): string {
  const rounded = suffix === '%' || Math.abs(v) < 100 ? Math.round(v * 10) / 10 : Math.round(v)
  return `${rounded.toLocaleString()}${suffix}`
}

const labelCore = (l: string) => l.replace(/（.*/, '')

/** 「約1.9x」「976名」「75%」等の表示値から数値と単位を取り出す（決定的パースのみ） */
function parseDispVal(s: string): { approx: boolean; num: number; suffix: string } | null {
  const m = s.replace(/,/g, '').match(/(約)?\s*(-?\d+(?:\.\d+)?)\s*(x|倍|%|％|百万円|千円|億円|名|人|円)?/)
  if (!m) return null
  return { approx: !!m[1], num: parseFloat(m[2]), suffix: m[3] === '％' ? '%' : (m[3] ?? '') }
}

/** impact_calc の before/after 文字列から末尾の「＝ 結果」を取り出す（{{}}マーカーは除去） */
function resultOf(s: string | null | undefined): string | null {
  if (!s) return null
  const i = s.lastIndexOf('＝')
  if (i < 0) return null
  return s.slice(i + 1).replace(/\{\{|\}\}/g, '').trim() || null
}

/** ストレス前後の表示値から変化幅ラベルを作る。DSCRはコベナンツ閾値との抵触も判定 */
function deltaLabelOf(before: string | null, after: string | null, metric: string, safeguards: string | null | undefined): string {
  if (!before || !after) return '－'
  const b = parseDispVal(before)
  const a = parseDispVal(after)
  if (!b || !a || b.suffix !== a.suffix) return '－'
  if (/DSCR/i.test(metric) && safeguards) {
    const cov = safeguards.match(/コベナンツ[（(]([\d.]+)x[）)]/)
    if (cov && a.num < parseFloat(cov[1])) return `コベナンツ${cov[1]}x抵触`
  }
  const approx = b.approx || a.approx ? '約' : ''
  if (b.suffix === 'x' || b.suffix === '倍') {
    const d = Math.round((a.num - b.num) * 10) / 10
    return `${d >= 0 ? '＋' : '▲'}${approx}${Math.abs(d)}${b.suffix}`
  }
  if (b.num === 0) return '－'
  const pct = Math.round(((a.num - b.num) / Math.abs(b.num)) * 100)
  return `${pct >= 0 ? '＋' : '▲'}${approx}${Math.abs(pct)}%`
}

/** impact_calc の {{...}} マーカーを強調スパンに変換する */
function hlText(text: string, cls: string): React.ReactNode {
  return text.split(/\{\{(.*?)\}\}/g).map((part, i) =>
    i % 2 === 1 ? <b key={i} className={cls}>{part}</b> : <span key={i}>{part}</span>)
}
/** ノードの表示用の値（'88%（FY26実績）' → '88%'） */
const displayVal = (n: KpiNode) => (n.value_text ?? '').replace(/（.*?）/g, '').trim()

interface Seg { text: string; hl: boolean }

/** 数式のラベルを値に置換したセグメント列を作る。
 *  stressedMap があれば該当KPIをストレス後の値（強調）に置き換える。決定的な文字列置換のみ。 */
function substituteFormula(formula: string, nodes: KpiNode[], stressedMap: Map<string, string> | null): Seg[] {
  let segs: Seg[] = [{ text: formula.replace(/^[=＝]\s*/, ''), hl: false }]
  // 長いラベルから置換して部分一致の誤置換を防ぐ（例:「在籍登録スタッフ数」を先に）
  const candidates = nodes
    .map((n) => ({ core: labelCore(n.label), val: displayVal(n) }))
    .filter((c) => c.core && (c.val || stressedMap?.has(c.core)))
    .sort((a, b) => b.core.length - a.core.length)
  for (const c of candidates) {
    const replacement = stressedMap?.get(c.core) ?? c.val
    if (!replacement) continue
    const hl = stressedMap?.has(c.core) ?? false
    const next: Seg[] = []
    for (const s of segs) {
      if (s.hl || !s.text.includes(c.core)) { next.push(s); continue }
      const parts = s.text.split(c.core)
      parts.forEach((p, i) => {
        if (p) next.push({ text: p, hl: false })
        if (i < parts.length - 1) next.push({ text: replacement, hl })
      })
    }
    segs = next
  }
  return segs
}

/** 参考試算：ストレス（KPI変化）がKPIツリーの数式を通じてインパクトへ波及する様子を、
 *  「計算式／元の値／ストレス後」の3列で見せる。AIの再計算ではなく決定的な単純置換・比例計算のみ。 */
function RefCalc({ sc, nodes }: { sc: Scenario; nodes: KpiNode[] }) {
  // あいまい一致・正規表現パースはコストがあるため、入力が変わったときだけ再計算
  const calc = useMemo(() => {
    // 変化幅の記述は change_text 以外（発生要因・根拠）に書かれていることもあるため広く探す
    const searchText = [sc.change_text, sc.cause, sc.change_basis].filter(Boolean).join('／')
    const kpis = (sc.affected_kpis ?? [])
      .map((id) => {
        const node = resolveKpiNode(nodes, id)
        if (!node) return null
        const base = parseBase(node.value_text)
        const arrow = parseArrowNear(searchText, node.label)
        const pct = parseChangePct(searchText, node.label)
        const stressed = arrow ? arrow.to : base && pct != null ? base.value * (1 + pct / 100) : null
        const suffix = arrow ? '%' : base?.suffix ?? ''
        const factor = arrow && arrow.from !== 0 ? arrow.to / arrow.from : pct != null ? 1 + pct / 100 : null
        const changeLabel = arrow
          ? `${fmtNum(((arrow.to - arrow.from) / arrow.from) * 100, '%')}`
          : pct != null ? fmtNum(pct, '%') : null
        return { node, base, stressed, suffix, factor, changeLabel }
      })
      .filter((r): r is NonNullable<typeof r> => r != null)

    // ストレス後の値マップ（ラベル核 → 表示文字列）と比例係数マップ
    const stressedMap = new Map<string, string>()
    const factorMap = new Map<string, number>()
    for (const k of kpis) {
      if (k.stressed == null) continue
      stressedMap.set(labelCore(k.node.label), fmtNum(k.stressed, k.suffix))
      if (k.factor != null) factorMap.set(labelCore(k.node.label), k.factor)
    }

    // 分解チェーン：ルート（EBITDA等）からストレス対象KPIまでの経路上の数式を全部展開する。
    // 「インパクト指標 → どの数式を通って → ストレスKPIに行き着くか」を漏れなく見せるための構造。
    // 対象KPIのノード自身に加え、対象KPIを数式内で参照しているノード（例: 採用費＝新規採用人数×CPA）
    // の経路も含める（ツリーの親子関係と数式参照の両方を辿る）
    const byId = new Map(nodes.map((n) => [n.node_id, n]))
    const hlAll = new Map(kpis.map((k) => [labelCore(k.node.label), labelCore(k.node.label)]))
    const affectedNodes = kpis.map((k) => k.node)
    const referencing = nodes.filter(
      (n) => n.formula && kpis.some((k) => n.formula!.includes(labelCore(k.node.label))),
    )
    const pathIds = new Set<string>()
    for (const seed of [...affectedNodes, ...referencing]) {
      let cur: KpiNode | undefined = seed
      while (cur) {
        pathIds.add(cur.node_id)
        cur = cur.parent_id ? byId.get(cur.parent_id) : undefined
      }
    }
    const chain: { node: KpiNode; depth: number; sym: Seg[] }[] = []
    const visit = (n: KpiNode, depth: number) => {
      const hasLine = !!n.formula
      if (hasLine) chain.push({ node: n, depth, sym: substituteFormula(n.formula!, affectedNodes, hlAll) })
      for (const c of nodes.filter((x) => x.parent_id === n.node_id && pathIds.has(x.node_id))) {
        visit(c, depth + (hasLine ? 1 : 0))
      }
    }
    for (const r of nodes.filter((x) => pathIds.has(x.node_id) && (!x.parent_id || !pathIds.has(x.parent_id)))) {
      visit(r, 0)
    }

    // 影響KPIが登場する数式行（重複排除・シナリオに関係するモデル構造）
    const formulaNodes = nodes.filter(
      (n) => n.formula && kpis.some((k) => n.formula!.includes(labelCore(k.node.label))),
    )
    const rows = formulaNodes.slice(0, 4).map((n) => {
      // ×のみの数式は「影響KPIの変化率の積」で結果を比例計算できる（＋−を含む式は結果を出さない）
      const body = n.formula!.replace(/^[=＝]\s*/, '')
      const scalable = !/[+＋−]|(?<!\d)-/.test(body)
      let factorProduct: number | null = 1
      for (const [core, f] of factorMap) {
        if (body.includes(core)) factorProduct = factorProduct == null ? null : factorProduct * f
      }
      const affected = kpis.filter((k) => k.stressed != null && body.includes(labelCore(k.node.label)))
      const hasAffected = affected.length > 0
      const ownBase = parseBase(n.value_text)
      const stressedResult = scalable && hasAffected && factorProduct != null && ownBase
        ? fmtNum(ownBase.value * factorProduct, ownBase.suffix)
        : null
      // 記号のままの数式（ストレス対象KPIだけハイライト）
      const hlOnly = new Map(affected.map((k) => [labelCore(k.node.label), labelCore(k.node.label)]))
      const origResult = displayVal(n) || null
      // 補足説明：どのKPIがどう変わり、この数式の結果がどうなるか
      const changes = affected
        .map((k) => `${k.node.label}が${displayVal(k.node) || (k.base && fmtNum(k.base.value, k.suffix))}→${fmtNum(k.stressed!, k.suffix)}`)
        .join('、')
      const caption = stressedResult && origResult && factorProduct != null
        ? `${changes}となるため、${n.label}は${origResult}から${stressedResult}（${fmtNum((factorProduct - 1) * 100, '%')}）に変化する単純試算です。`
        : `${changes}の変化が${n.label}に波及します（利益・返済能力への影響は【インパクト】欄のAI推定を参照）。`
      return {
        node: n,
        sym: substituteFormula(n.formula!, affected.map((k) => k.node), hlOnly),
        orig: substituteFormula(n.formula!, nodes, null),
        stress: substituteFormula(n.formula!, nodes, stressedMap),
        origResult,
        stressedResult,
        caption,
      }
    })
    return { kpis, rows, chain }
  }, [sc, nodes])

  const [showCalc, setShowCalc] = useState(false)
  const impactCalc = sc.impact_calc ?? []
  if (calc.kpis.length === 0 && impactCalc.length === 0) return null
  const calculable = calc.kpis.filter((k) => k.stressed != null)

  // インパクトサマリー：ストレス対象KPI＋波及指標の「ストレス前→ストレス後」を一覧化。
  // すべて既存の決定的パース値（calc.kpis / impact_calc / calc.rows）の再構成で、新規の推定はしない。
  const summaryRows: { key: string; kpi: boolean; label: string; before: string; after: string | null; delta: string }[] = [
    ...calc.kpis.map((k) => ({
      key: `kpi-${k.node.node_id}`,
      kpi: true,
      label: labelCore(k.node.label),
      before: displayVal(k.node) || (k.base ? fmtNum(k.base.value, k.suffix) : '－'),
      after: k.stressed != null ? fmtNum(k.stressed, k.suffix) : null,
      delta: k.changeLabel ?? '－',
    })),
    ...impactCalc.map((b, i) => ({
      key: `ic-${i}`,
      kpi: false,
      label: b.metric,
      before: resultOf(b.before) ?? '－',
      after: resultOf(b.after),
      delta: deltaLabelOf(resultOf(b.before), resultOf(b.after), b.metric, sc.safeguards),
    })),
    ...(impactCalc.length === 0
      ? calc.rows
        .filter((r) => r.origResult && r.stressedResult)
        .map((r) => ({
          key: `row-${r.node.node_id}`,
          kpi: false,
          label: r.node.label,
          before: r.origResult!,
          after: r.stressedResult,
          delta: deltaLabelOf(r.origResult, r.stressedResult, r.node.label, sc.safeguards),
        }))
      : []),
  ]

  return (
    <div className="mt-2 overflow-hidden rounded border border-primary-container/25 bg-white">
      <div className="flex items-baseline gap-2 bg-primary-fixed/40 px-3 py-1.5">
        <span className="text-[11px] font-bold text-primary-container">インパクトサマリー</span>
        <span className="text-[10px] text-outline">AI推定・モデル再計算なし</span>
      </div>
      <table className="w-full text-[12px]">
        <thead>
          <tr className="border-b border-surface-container-low text-[10.5px] text-outline">
            <th className="px-3 py-1 text-left font-medium">指標</th>
            <th className="py-1 text-right font-medium">ストレス前（ベース）</th>
            <th className="w-7" />
            <th className="py-1 text-right font-medium">ストレス後</th>
            <th className="px-3 py-1 text-right font-medium">変化幅</th>
          </tr>
        </thead>
        <tbody>
          {summaryRows.map((r) => (
            <tr key={r.key} className="border-b border-surface-container-low last:border-0">
              <td className="px-3 py-1.5">
                {r.kpi
                  ? <span className="rounded bg-amber-100 px-1.5 py-0.5 font-medium text-amber-900">{r.label}</span>
                  : r.label}
              </td>
              {r.after != null ? (
                <>
                  <td className="font-data-tabular py-1.5 text-right">{r.before}</td>
                  <td className="text-center text-outline">
                    <Icon name="arrow_right_alt" className="align-middle text-[15px]" />
                  </td>
                  <td className="font-data-tabular py-1.5 text-right font-bold text-error">{r.after}</td>
                  <td className="font-data-tabular px-3 py-1.5 text-right text-on-surface-variant">{r.delta}</td>
                </>
              ) : (
                <td colSpan={4} className="px-3 py-1.5 text-right text-[11px] text-on-surface-variant">
                  数値の変化幅を特定できないため試算なし（本文参照）
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      <button
        className="flex w-full items-center gap-1 border-t border-surface-container-low px-3 py-1.5 text-left text-[11px] text-primary-container hover:bg-surface-container-low/40"
        onClick={(e) => { e.stopPropagation(); setShowCalc(!showCalc) }}
      >
        <Icon name={showCalc ? 'expand_more' : 'chevron_right'} className="text-[14px]" />
        計算過程を表示（KPIツリーの分解・値入り計算式）
      </button>
      {showCalc && (
      <div className="border-t border-surface-container-low bg-primary-fixed/10 px-3 pb-3">

      {/* ① ストレスをかける対象KPI（ハイライト表示） */}
      <div className="mt-2 space-y-1">
        {calc.kpis.map((k) => (
          <div key={k.node.node_id} className="flex flex-wrap items-baseline gap-x-2 text-[12px]">
            <span className="rounded bg-amber-100 px-1.5 py-0.5 font-bold text-amber-900">{k.node.label}</span>
            {k.stressed != null ? (
              <span className="font-data-tabular">
                {displayVal(k.node) || (k.base && fmtNum(k.base.value, k.suffix))}
                <Icon name="arrow_right_alt" className="mx-1 align-middle text-[14px] text-error" />
                <b className="text-error">{fmtNum(k.stressed, k.suffix)}</b>
                {k.changeLabel && <span className="ml-1.5 text-on-surface-variant">（{k.changeLabel}）</span>}
              </span>
            ) : (
              <span className="text-on-surface-variant">数値の変化幅を特定できないため試算なし（本文参照）</span>
            )}
          </div>
        ))}
      </div>

      {/* ①' KPIツリーの分解チェーン：インパクト指標の構成要素からストレスKPIまで全部展開 */}
      {calc.chain.length > 0 && (
        <div className="mt-2.5 rounded border border-primary-container/20 bg-white px-3 py-2.5">
          <div className="text-[10.5px] font-bold text-on-surface-variant">
            KPIツリーの分解（インパクト指標の構成要素 → ストレス対象KPI）
          </div>
          <div className="font-data-tabular mt-1.5 space-y-0.5 text-[12px] leading-relaxed">
            {calc.chain.map(({ node, depth, sym }) => (
              <div key={node.node_id} style={{ marginLeft: depth * 18 }}>
                {depth > 0 && <Icon name="subdirectory_arrow_right" className="mr-0.5 align-middle text-[13px] text-outline-variant" />}
                <b className="font-sans">{node.label}</b>
                <span className="text-on-surface-variant"> ＝ {sym.map((s, i) => s.hl
                  ? <span key={i} className="rounded bg-amber-100 px-0.5 font-bold text-amber-900">{s.text}</span>
                  : <span key={i}>{s.text}</span>)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ② インパクト指標の分解：左辺＝インパクトの最終指標、右辺＝ストレス対象KPIを含む式 */}
      {impactCalc.length > 0 && (
        <div className="mt-2.5 space-y-2">
          {impactCalc.map((b, bi) => (
            <div key={bi} className="rounded border border-primary-container/20 bg-white px-3 py-2.5">
              {/* 指標 ＝ 分解式 */}
              <div className="font-data-tabular text-[12px] leading-relaxed">
                <b className="font-sans">{b.metric}</b>
                <span className="text-on-surface-variant"> ＝ {hlText(b.formula, 'rounded bg-amber-100 px-0.5 font-bold text-amber-900')}</span>
              </div>
              {/* ストレス前後の値入り計算式（縦積みで比較） */}
              <div className="font-data-tabular mt-1.5 grid grid-cols-[72px_minmax(0,1fr)] gap-y-1 border-t border-surface-container-low pt-1.5 text-[12px] leading-relaxed">
                <span className="text-[11px] text-outline">ストレス前</span>
                <span className="text-on-surface-variant">＝ {hlText(b.before, 'text-on-surface')}</span>
                <span className="text-[11px] font-bold text-error">ストレス後</span>
                <span className="text-on-surface-variant">＝ {hlText(b.after, 'text-error')}</span>
              </div>
              {/* 補足説明 */}
              {b.note && (
                <div className="mt-1.5 text-[11px] leading-relaxed text-on-surface-variant">
                  <Icon name="subdirectory_arrow_right" className="mr-0.5 align-middle text-[12px] text-outline" />
                  {hlText(b.note, 'rounded bg-amber-100 px-0.5 font-medium text-amber-900')}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ②' impact_calc が無いシナリオ（チャット追加等）：KPIツリーの数式から積み上げる従来表示 */}
      {impactCalc.length === 0 && calc.rows.length > 0 && (
        <div className="mt-2.5 space-y-2">
          {calc.rows.map((r) => (
            <div key={r.node.node_id} className="rounded border border-primary-container/20 bg-white px-3 py-2.5">
              {/* 数式（ストレス対象KPIをハイライト） */}
              <div className="font-data-tabular text-[12px] leading-relaxed">
                <b className="font-sans">{r.node.label}</b>
                <span className="text-on-surface-variant"> ＝ {r.sym.map((s, i) => s.hl
                  ? <span key={i} className="rounded bg-amber-100 px-0.5 font-bold text-amber-900">{s.text}</span>
                  : <span key={i}>{s.text}</span>)}
                </span>
              </div>
              {/* ストレス前後の値入り計算式（縦積みで桁を比較しやすく） */}
              <div className="font-data-tabular mt-1.5 grid grid-cols-[72px_minmax(0,1fr)] gap-y-1 border-t border-surface-container-low pt-1.5 text-[12px] leading-relaxed">
                <span className="text-[11px] text-outline">ストレス前</span>
                <span className="text-on-surface-variant">
                  ＝ {r.orig.map((s, i) => <span key={i}>{s.text}</span>)}
                  {r.origResult && <span> ＝ <b className="text-on-surface">{r.origResult}</b></span>}
                </span>
                <span className="text-[11px] font-bold text-error">ストレス後</span>
                <span className="text-on-surface-variant">
                  ＝ {r.stress.map((s, i) => s.hl
                    ? <b key={i} className="text-error">{s.text}</b>
                    : <span key={i}>{s.text}</span>)}
                  {r.stressedResult && <span> ＝ <b className="text-error">{r.stressedResult}</b></span>}
                </span>
              </div>
              {/* 補足説明 */}
              <div className="mt-1.5 text-[11px] leading-relaxed text-on-surface-variant">
                <Icon name="subdirectory_arrow_right" className="mr-0.5 align-middle text-[12px] text-outline" />
                {r.caption}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ③ インパクトへの接続 */}
      <div className="mt-2 text-[11px] leading-relaxed text-on-surface-variant">
        ※ 上記は<b>【ストレスと根拠】</b>のKPI変化が<b>【インパクト】</b>欄の推定値
        （AI推定・モデル再計算なし）にどう繋がるかを分解して示した参考表示です。
      </div>

      </div>
      )}
      {calculable.length === 0 && (
        <div className="border-t border-surface-container-low px-3 py-1.5 text-[11px] text-outline">
          ※ シナリオ本文に数値の変化幅（例: -15%、76%→74%）が明記されると自動で試算されます。
        </div>
      )}
    </div>
  )
}

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

const SCENARIO_KEY_COLOR: Record<string, string> = {
  A: 'bg-primary-container',
  B: 'bg-amber-700',
  C: 'bg-error',
}

export function ScenarioTab({ full, refresh, dealId }: {
  full: DealFull
  refresh: () => Promise<void>
  dealId: number
}) {
  const { userKey } = useUser()
  const scenarios = full.scenarios
  // 既定で全シナリオを展開する。「閉じたもの」を覚える方式にして、
  // 解析後やAIチャットで後から増えたシナリオも自動的に開いた状態になるようにする
  const [closedKeys, setClosedKeys] = useState<Set<string>>(new Set())
  const [fullText, setFullText] = useState<Set<string>>(new Set())
  const [finPanelSc, setFinPanelSc] = useState<Scenario | null>(null)
  const fin = useMemo(() => buildFinTable(full.items), [full.items])
  const nodeLabel = (id: string) => kpiLabelOf(full.kpi_nodes, id)

  const toggleOpen = (key: string) => {
    setClosedKeys((prev) => {
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
    // AIの応答形式が想定と異なる場合に画面を落とさない（不明な形はJSONで見せる）
    if (diff.type === 'add_card' && diff.card) {
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
    if (diff.type === 'update_card' && diff.fields) {
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
      // 追加直後のカードは必ず開いた状態で見せる（閉じ済みリストから外す）
      const key = (diff.card as { key?: string } | undefined)?.key
      if (key) {
        setClosedKeys((prev) => {
          const next = new Set(prev)
          next.delete(key)
          return next
        })
      }
    }
    await refresh()
  }

  return (
    <div className="grid grid-cols-[1fr_360px] gap-4">
      <div>
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="text-[14px] font-bold">検証シナリオ</div>
          <div className="flex items-center gap-3">
            <div className="text-[11px] text-outline">
              行をクリックで開閉。採用トグルON＝確定シナリオ（エクスポート対象）。
            </div>
            <button
              className="btn-secondary shrink-0 !py-1 !text-[11px]"
              onClick={() =>
                setClosedKeys((prev) =>
                  prev.size === 0 ? new Set(scenarios.map((s) => s.key)) : new Set(),
                )
              }
            >
              <Icon
                name={closedKeys.size === 0 ? 'unfold_less' : 'unfold_more'}
                className="text-[15px]"
              />
              {closedKeys.size === 0 ? 'すべて閉じる' : 'すべて開く'}
            </button>
          </div>
        </div>

        {/* シナリオ一覧（アコーディオン行） */}
        <div className="card divide-y divide-surface-container-low">
          {scenarios.map((sc) => {
            const findings = full.findings.filter((f) => f.target_type === 'scenario' && f.target_key === sc.key)
            const open = !closedKeys.has(sc.key)
            return (
              <div key={sc.id}>
                {/* 行 */}
                <div
                  className={`flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-surface-container-low/50 ${!sc.adopted ? 'opacity-70' : ''}`}
                  onClick={() => toggleOpen(sc.key)}
                >
                  <Icon name={open ? 'expand_more' : 'chevron_right'} className="shrink-0 text-[20px] text-outline" />
                  <span className={`flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full text-[12px] font-bold text-white ${SCENARIO_KEY_COLOR[sc.key] ?? 'bg-outline'}`}>
                    {sc.key}
                  </span>
                  <div className="min-w-0 flex-1 truncate text-[13.5px] font-bold">{sc.title}</div>
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
                    {/* 財務数値を参照しながらシナリオをチェックできるサイドパネルを開く */}
                    <div className="mb-2 flex justify-end">
                      <button
                        className="btn-secondary !py-1 !text-[11px]"
                        onClick={(e) => { e.stopPropagation(); setFinPanelSc(sc) }}
                      >
                        <Icon name="table_chart" className="text-[14px]" /> 財務データを見る
                      </button>
                    </div>
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
                    {/* 端的な箇条書き（全文はトグルで表示） */}
                    <div className="space-y-1.5 text-[12.5px] leading-relaxed">
                      <div>
                        <span className="font-bold">・【KPIとリスク】</span>
                        {sc.affected_kpis.map(nodeLabel).join('・') || '－'}。
                        {fullText.has(sc.key) ? sc.cause : brief(sc.cause)}
                      </div>
                      <div>
                        <span className="font-bold">・【ストレスと根拠】</span>
                        <span className="rounded bg-amber-100 px-1 font-medium text-amber-900">{sc.change_text || '－'}</span>
                        （根拠：{fullText.has(sc.key) ? sc.change_basis : brief(sc.change_basis, 1)}）
                      </div>
                      <div>
                        <span className="font-bold">・【インパクト】</span>
                        {fullText.has(sc.key) ? sc.impact : brief(sc.impact)}
                        <span className="ml-1 text-[10px] text-outline">（AI推定・モデル再計算なし）</span>
                      </div>
                      <div>
                        <span className="font-bold">・【保全策・構造】</span>
                        {fullText.has(sc.key) ? sc.safeguards : brief(sc.safeguards)}
                      </div>
                      <div>
                        <span className="font-bold">・【Q&A】</span>
                        {fullText.has(sc.key) ? sc.questions : brief(sc.questions)}
                      </div>
                      <button
                        className="text-[11px] text-primary-container underline"
                        onClick={(e) => {
                          e.stopPropagation()
                          setFullText((prev) => {
                            const next = new Set(prev)
                            if (next.has(sc.key)) next.delete(sc.key)
                            else next.add(sc.key)
                            return next
                          })
                        }}
                      >
                        {fullText.has(sc.key) ? '要約表示に戻す' : '全文を表示'}
                      </button>
                    </div>

                    {/* 数式ベースの参考試算 */}
                    <RefCalc sc={sc} nodes={full.kpi_nodes} />
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

      {/* 財務データのサイドパネル（概要タブと同じ統合テーブル・ストレス対象KPI行を強調） */}
      {finPanelSc && (
        <SlidePanel
          title="財務情報（百万円）"
          widthClass="w-[640px] max-w-[92vw]"
          onClose={() => setFinPanelSc(null)}
        >
          <div className="mb-2 text-[11px] text-outline">
            黄色の行＝シナリオ{finPanelSc.key}のストレス対象KPI。セルにカーソルを合わせると根拠（出典）が表示されます。
          </div>
          <FinTableView
            fin={fin}
            highlightLabels={finPanelSc.affected_kpis.map((id) => labelCore(nodeLabel(id)))}
          />
        </SlidePanel>
      )}
    </div>
  )
}
