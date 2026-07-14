import { useState } from 'react'
import { api } from '../../api'
import { Icon } from '../../components/Icon'
import { Badge, ReviewStatusBadge } from '../../components/Badge'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { useUser } from '../../context/UserContext'
import type { DealFull } from '../../types'

const CONCLUSIONS = ['続行', '再検討', '推進', '保留', '見送り']
const CONCLUSION_BADGE: Record<string, 'success' | 'warning' | 'info' | 'neutral'> = {
  続行: 'success', 再検討: 'warning', 推進: 'success', 保留: 'neutral', 見送り: 'neutral',
}
const STATUS_MAP: Record<string, string | null> = {
  続行: null, 再検討: '再検討中', 推進: '推進', 保留: '保留', 見送り: '見送り',
}

interface FindingDraft {
  target_type: string
  target_key: string
  text: string
}

export function MemoTab({ full, refresh, dealId }: {
  full: DealFull
  refresh: () => Promise<void>
  dealId: number
}) {
  const { users, userKey } = useUser()
  const [showForm, setShowForm] = useState(false)
  const [meetingDate, setMeetingDate] = useState(new Date().toISOString().slice(0, 10))
  const [attendees, setAttendees] = useState<string[]>(['田中（稟議担当）', '佐藤（部長）'])
  const [conclusion, setConclusion] = useState('続行')
  const [note, setNote] = useState('')
  const [findings, setFindings] = useState<FindingDraft[]>([])
  const [statusConfirm, setStatusConfirm] = useState(false)
  const [busy, setBusy] = useState(false)

  const targetOptions: { value: string; label: string }[] = [
    { value: '', label: '（紐付けなし）' },
    ...full.scenarios.map((s) => ({ value: `scenario:${s.key}`, label: `シナリオ${s.key}：${s.title.slice(0, 18)}` })),
    { value: 'kpi:', label: 'KPI構造' },
    ...full.items.filter((i) => i.mismatch || i.status === 'held').map((i) => ({ value: `item:${i.key}`, label: `数値：${i.label}` })),
  ]

  const newStatus = STATUS_MAP[conclusion]
  const statusWillChange = newStatus && newStatus !== full.deal.review_status

  const save = async (updateStatus: boolean) => {
    setBusy(true)
    try {
      await api.createMemo(dealId, {
        meeting_date: meetingDate,
        attendees,
        conclusion,
        note: note || null,
        findings: findings.filter((f) => f.text.trim()).map((f) => ({
          target_type: f.target_type || null,
          target_key: f.target_key || null,
          text: f.text,
        })),
        update_review_status: updateStatus,
        user: userKey,
      })
      setShowForm(false)
      setNote('')
      setFindings([])
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  const onSave = () => {
    if (statusWillChange) setStatusConfirm(true)
    else save(false)
  }

  return (
    <div className="mx-auto max-w-[860px]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-[16px] font-bold">審査相談メモ</h2>
          <div className="flex items-center gap-1.5 text-[12px] text-on-surface-variant">
            検討ステータス <ReviewStatusBadge status={full.deal.review_status} />
          </div>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(true)}>
          <Icon name="add" className="text-[16px]" /> 審査相談メモを追加
        </button>
      </div>

      {/* 追加フォーム */}
      {showForm && (
        <div className="card mt-4 p-4">
          <div className="text-[14px] font-bold">審査相談の記録</div>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <label className="block text-[12px]">
              <span className="text-on-surface-variant">相談日</span>
              <input type="date" className="input-base mt-1" value={meetingDate} onChange={(e) => setMeetingDate(e.target.value)} />
            </label>
            <label className="block text-[12px]">
              <span className="text-on-surface-variant">結論</span>
              <select className="input-base mt-1" value={conclusion} onChange={(e) => setConclusion(e.target.value)}>
                {CONCLUSIONS.map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
            <div className="block text-[12px]">
              <span className="text-on-surface-variant">出席者</span>
              <div className="mt-1.5 flex flex-wrap gap-2">
                {users.map((u) => (
                  <label key={u.key} className="flex items-center gap-1 text-[12px]">
                    <input
                      type="checkbox"
                      checked={attendees.includes(u.display)}
                      onChange={(e) => setAttendees(e.target.checked
                        ? [...attendees, u.display]
                        : attendees.filter((a) => a !== u.display))}
                    />
                    {u.name}
                  </label>
                ))}
              </div>
            </div>
          </div>
          {statusWillChange && (
            <div className="mt-2 text-[11px] text-amber-700">
              <Icon name="info" className="mr-0.5 align-middle text-[13px]" />
              結論「{conclusion}」の記録時に、検討ステータスを「{newStatus}」へ更新できます。
            </div>
          )}

          <div className="mt-3">
            <div className="flex items-center justify-between">
              <span className="text-[12px] text-on-surface-variant">指摘事項（シナリオ・数値・KPIに紐付け可）</span>
              <button
                className="text-[12px] font-medium text-primary-container"
                onClick={() => setFindings([...findings, { target_type: '', target_key: '', text: '' }])}
              >
                ＋ 指摘を追加
              </button>
            </div>
            {findings.map((f, i) => (
              <div key={i} className="mt-2 flex gap-2">
                <select
                  className="input-base !w-64"
                  value={f.target_type ? `${f.target_type}:${f.target_key}` : ''}
                  onChange={(e) => {
                    const [t, k] = e.target.value.split(':')
                    setFindings(findings.map((x, j) => (j === i ? { ...x, target_type: t ?? '', target_key: k ?? '' } : x)))
                  }}
                >
                  {targetOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <input
                  className="input-base flex-1"
                  placeholder="指摘の内容"
                  value={f.text}
                  onChange={(e) => setFindings(findings.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)))}
                />
                <button className="text-outline hover:text-error" onClick={() => setFindings(findings.filter((_, j) => j !== i))}>
                  <Icon name="delete" className="text-[18px]" />
                </button>
              </div>
            ))}
          </div>

          <label className="mt-3 block text-[12px]">
            <span className="text-on-surface-variant">メモ</span>
            <textarea className="input-base mt-1 h-20" value={note} onChange={(e) => setNote(e.target.value)}
              placeholder="合意事項・次回までのアクション等" />
          </label>

          <div className="mt-4 flex justify-end gap-2">
            <button className="btn-secondary" onClick={() => setShowForm(false)}>キャンセル</button>
            <button className="btn-primary" disabled={busy} onClick={onSave}>記録する</button>
          </div>
        </div>
      )}

      {/* タイムライン */}
      <div className="relative mt-6 space-y-6 pl-8">
        <div className="absolute bottom-2 left-[9px] top-2 w-px bg-outline-variant" />
        {full.memos.map((m, idx) => (
          <div key={m.id} className="relative">
            <div className="absolute -left-8 top-1 flex flex-col items-center">
              <span className="h-[10px] w-[10px] rounded-full border-2 border-primary-container bg-white" />
            </div>
            <div className="text-[12px] font-data-tabular text-on-surface-variant">{m.meeting_date.replaceAll('-', '/')}</div>
            <div className="card mt-1.5">
              <div className="flex items-center gap-2.5 border-b border-surface-container-low px-4 py-2.5">
                <span className="text-[14px] font-bold">第{full.memos.length - idx}回審査相談</span>
                <Badge kind={CONCLUSION_BADGE[m.conclusion] ?? 'neutral'}>{m.conclusion}</Badge>
                <span className="ml-auto flex items-center gap-1 text-[11px] text-outline">
                  <Icon name="groups" className="text-[14px]" /> {m.attendees.join('、')}
                </span>
                <span className="flex items-center gap-1 text-[11px] text-outline">
                  <Icon name="edit_note" className="text-[14px]" />
                  記録：{m.created_by === 'tanaka' ? '田中' : m.created_by === 'sato' ? '佐藤' : m.created_by === 'takahashi' ? '高橋' : m.created_by}
                </span>
              </div>
              {m.findings.length > 0 && (
                <div className="border-b border-surface-container-low px-4 py-3">
                  <div className="text-[11px] font-bold text-on-surface-variant">指摘事項</div>
                  <ol className="mt-1.5 space-y-2">
                    {m.findings.map((f, i) => (
                      <li key={f.id} className="text-[12.5px]">
                        <span className="mr-1 text-outline">{i + 1}.</span>
                        「{f.text}」
                        {f.target_type && (
                          <span className="badge-base badge-info ml-1.5 !text-[10px]">
                            <Icon name="link" className="text-[11px]" />
                            {f.target_type === 'scenario'
                              ? `シナリオ${f.target_key}`
                              : f.target_type === 'kpi'
                                ? 'KPI構造'
                                : `数値：${full.items.find((i) => i.key === f.target_key)?.label ?? f.target_key}`}
                          </span>
                        )}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
              {m.note && (
                <div className="px-4 py-3">
                  <div className="text-[11px] font-bold text-on-surface-variant">メモ</div>
                  <p className="mt-1 whitespace-pre-wrap text-[12.5px] leading-relaxed">{m.note}</p>
                </div>
              )}
              {m.conclusion !== '続行' && (
                <div className="flex items-center gap-1.5 border-t border-surface-container-low px-4 py-2 text-[11px] text-outline">
                  <Icon name="sync_alt" className="text-[13px]" />
                  この記録により検討ステータスの更新対象：「{STATUS_MAP[m.conclusion] ?? '変更なし'}」
                </div>
              )}
            </div>
          </div>
        ))}
        {full.memos.length === 0 && (
          <div className="card p-10 text-center text-[13px] text-outline">
            審査相談の記録はまだありません。
          </div>
        )}
      </div>

      <ConfirmDialog
        open={statusConfirm}
        title={`検討ステータスを「${newStatus}」に更新しますか？`}
        confirmLabel="更新して記録"
        cancelLabel="更新せず記録"
        onConfirm={() => { setStatusConfirm(false); save(true) }}
        onCancel={() => { setStatusConfirm(false); save(false) }}
      >
        結論「{conclusion}」に連動して、案件の検討ステータスを
        「{full.deal.review_status}」から「{newStatus}」へ更新できます。
      </ConfirmDialog>
    </div>
  )
}
