import { useState } from 'react'
import { api } from '../api'
import { useUser } from '../context/UserContext'
import type { Inquiry } from '../types'
import { Icon } from './Icon'

/** AIが検知した「人への確認事項（照会）」の一覧（仕様②6）。
 *  右サイドバー（SlidePanel）内に表示し、確認済みチェックとメモを付けられる。
 *  単位不明・名寄せ・参照切れ・資料間矛盾など、機械が勝手に解決してはいけない
 *  事象をAIがここへ報告する。 */

const SEVERITY_LABEL: Record<string, string> = { high: '高', medium: '中', low: '低' }

function severityClass(s: string): string {
  if (s === 'high') return 'badge-base badge-error'
  if (s === 'medium') return 'badge-base !bg-amber-100 !text-amber-900'
  return 'badge-base badge-neutral'
}

export function inquiryOpenCount(inquiries: Inquiry[]): number {
  return inquiries.filter((q) => q.status === 'open').length
}

export function InquiryList({ dealId, inquiries, refresh }: {
  dealId: number
  inquiries: Inquiry[]
  refresh: () => Promise<void> | void
}) {
  const { userKey } = useUser()
  const [busy, setBusy] = useState<number | null>(null)
  const [errors, setErrors] = useState<Record<number, string>>({})

  const toggle = async (q: Inquiry) => {
    setBusy(q.id)
    setErrors((e) => ({ ...e, [q.id]: '' }))
    try {
      await api.updateInquiry(dealId, q.id, {
        status: q.status === 'open' ? 'resolved' : 'open',
        user: userKey,
      })
      await refresh()
    } catch (e) {
      // 失敗を黙って飲み込むと「確認済みにしたつもり」の取り違えが起きる
      setErrors((prev) => ({ ...prev, [q.id]: (e as Error).message }))
    } finally {
      setBusy(null)
    }
  }

  if (inquiries.length === 0) {
    return (
      <div className="py-10 text-center text-[12px] text-outline">
        <Icon name="check_circle" className="mb-1 text-[28px] text-green-600" fill />
        <div>AIからの確認事項はありません。</div>
        <div className="mt-1">資料内で根拠が一意に決まらない事象（単位不明・名寄せ・参照切れ・数値の食い違い等）を検知すると、ここに表示されます。</div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {inquiries.map((q) => (
        <div
          key={q.id}
          className={`rounded border p-3 ${
            q.status === 'resolved'
              ? 'border-surface-container-high bg-surface-container-low/40 opacity-70'
              : 'border-amber-200 bg-amber-50/50'
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className={`${severityClass(q.severity)} !px-1.5 !py-0 !text-[10px]`}>
                重要度{SEVERITY_LABEL[q.severity] ?? q.severity}
              </span>
              <span className="badge-base badge-neutral !px-1.5 !py-0 !text-[10px]">{q.category}</span>
              <span className="text-[12px] font-bold">{q.title}</span>
            </div>
            <label className="flex shrink-0 cursor-pointer items-center gap-1 text-[11px] text-on-surface-variant">
              <input
                type="checkbox"
                checked={q.status === 'resolved'}
                disabled={busy === q.id}
                onChange={() => toggle(q)}
              />
              確認済み
            </label>
          </div>
          {q.detail && (
            <div className="mt-1.5 whitespace-pre-wrap text-[12px] text-on-surface-variant">{q.detail}</div>
          )}
          {q.source && (
            <div className="mt-1.5 rounded bg-surface-container-low/70 px-2 py-1.5 text-[11px] text-outline">
              <span className="font-bold">出所：</span>
              {q.source.file}｜{q.source.location}
              {q.source.quote && <span className="block truncate">「{q.source.quote}」</span>}
            </div>
          )}
          {errors[q.id] && (
            <div className="mt-1.5 flex items-center gap-1 text-[11px] text-error">
              <Icon name="error" className="text-[14px]" />
              状態を更新できませんでした（{errors[q.id]}）。再度お試しください。
            </div>
          )}
          {q.suggested_question && (
            <div className="mt-1.5 flex items-start gap-1.5 text-[12px]">
              <Icon name="contact_support" className="mt-0.5 shrink-0 text-[15px] text-primary-container" />
              <span className="text-on-surface-variant">
                <span className="font-bold text-primary-container">確認質問案：</span>
                {q.suggested_question}
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
