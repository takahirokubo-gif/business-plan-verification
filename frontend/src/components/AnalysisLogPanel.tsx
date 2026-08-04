import type { AnalysisRun } from '../types'
import { Icon } from './Icon'

/** AI解析の診断ログ（検証用）。
 *
 *  「AIが検知しなかった」のか「出力が上限で切れた／APIが失敗した」のかを
 *  切り分けるための情報を表示する。出力トークンが上限に達している場合は
 *  結果の取りこぼしが確定しているため、強調して警告する。 */

const STEP_LABEL: Record<string, string> = {
  items: '① 抽出・確認事項',
  kpi: '② KPI構造',
  scenarios: '③ ストレスシナリオ',
  deal_info: '案件情報の読み取り',
}

const STATUS: Record<string, { label: string; cls: string; icon: string }> = {
  ok: { label: '成功', cls: 'text-green-700', icon: 'check_circle' },
  truncated: { label: '出力が上限で打ち切り', cls: 'text-error', icon: 'content_cut' },
  error: { label: '失敗', cls: 'text-error', icon: 'error' },
}

function fmtTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function analysisHasProblem(runs: AnalysisRun[]): boolean {
  return runs.some((r) => r.status !== 'ok')
}

export function AnalysisLogList({ runs }: { runs: AnalysisRun[] }) {
  if (runs.length === 0) {
    return (
      <div className="py-10 text-center text-[12px] text-outline">
        まだAI解析が実行されていません。
      </div>
    )
  }
  return (
    <div className="space-y-3">
      <p className="rounded bg-surface-container-low/70 px-3 py-2 text-[11px] text-on-surface-variant">
        解析1ステップごとの実行記録です。<b>出力トークンが上限に達している場合、結果の一部が
        失われています</b>（AIが検知しなかったわけではありません）。検証時の切り分けに使ってください。
      </p>
      {runs.map((r) => {
        const st = STATUS[r.status] ?? STATUS.error
        const nearLimit = r.output_tokens != null && r.max_tokens != null
          && r.output_tokens >= r.max_tokens * 0.95
        return (
          <div
            key={r.id}
            className={`rounded border p-3 ${
              r.status === 'ok' && !nearLimit
                ? 'border-surface-container-high'
                : 'border-error/40 bg-error-container/20'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[12px] font-bold">{STEP_LABEL[r.step] ?? r.step}</span>
              <span className={`flex items-center gap-1 text-[11px] font-bold ${st.cls}`}>
                <Icon name={st.icon} className="text-[14px]" />
                {st.label}
              </span>
            </div>
            <div className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-0.5 text-[11px] text-on-surface-variant">
              <div>実行：{fmtTime(r.at)}</div>
              <div>所要：{r.duration_ms != null ? `${(r.duration_ms / 1000).toFixed(1)}秒` : '－'}</div>
              <div>エンジン：{r.mode === 'anthropic' ? `AI（${r.model ?? ''}）` : 'モック'}</div>
              <div>停止理由：{r.stop_reason ?? '－'}</div>
              <div>
                入力：{r.input_tokens != null ? `${r.input_tokens.toLocaleString()}トークン` : '－'}
              </div>
              <div className={nearLimit ? 'font-bold text-error' : ''}>
                出力：{r.output_tokens != null ? `${r.output_tokens.toLocaleString()}` : '－'}
                {r.max_tokens != null && ` / 上限 ${r.max_tokens.toLocaleString()}`}
              </div>
            </div>
            {r.result_summary && (
              <div className="mt-1.5 text-[12px]">結果：{r.result_summary}</div>
            )}
            {nearLimit && r.status === 'ok' && (
              <div className="mt-1.5 flex items-start gap-1 text-[11px] text-error">
                <Icon name="warning" className="mt-0.5 shrink-0 text-[14px]" />
                出力が上限付近です。結果が途中で切れている可能性があります。
              </div>
            )}
            {r.error && (
              <div className="mt-1.5 whitespace-pre-wrap rounded bg-error-container/40 px-2 py-1.5 text-[11px] text-on-error-container">
                {r.error}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
