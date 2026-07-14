import { useMemo, useState } from 'react'
import { api } from '../../api'
import { Icon } from '../../components/Icon'
import { EvidenceBlock, SlidePanel } from '../../components/EvidencePanel'
import { useUser } from '../../context/UserContext'
import type { DealFull, ExtractedItem } from '../../types'

const YEAR_ORDER = ['FY24', 'FY25', 'FY26', 'FY27', 'FY28', 'FY29', 'FY30', 'FY31']

function sortYears(years: string[]): string[] {
  return YEAR_ORDER.filter((y) => years.includes(y))
}

function StatusIcon({ item }: { item: ExtractedItem }) {
  if (item.status === 'confirmed') {
    return (
      <span className="inline-flex items-center gap-1 text-green-700">
        <Icon name="check_circle" className="text-[15px]" fill />
        <span className="text-[11px] font-medium">{item.edited ? '修正済' : '確定'}</span>
      </span>
    )
  }
  if (item.status === 'held') {
    return (
      <span className="inline-flex items-center gap-1 text-outline">
        <Icon name="pause_circle" className="text-[15px]" />
        <span className="text-[11px] font-medium">保留</span>
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 text-amber-700">
      <Icon name="radio_button_unchecked" className="text-[15px]" />
      <span className="text-[11px] font-medium">未確定</span>
    </span>
  )
}

export function NumbersTab({ full, refresh, dealId }: {
  full: DealFull
  refresh: () => Promise<void>
  dealId: number
}) {
  const { userKey } = useUser()
  const [selected, setSelected] = useState<ExtractedItem | null>(null)
  const [onlyPending, setOnlyPending] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editValues, setEditValues] = useState<Record<string, string>>({})
  const [editText, setEditText] = useState('')
  const [mismatchChoice, setMismatchChoice] = useState<'model' | 'dd' | null>(null)
  const [resolutionNote, setResolutionNote] = useState('')
  const [busy, setBusy] = useState(false)

  const items = full.items
  const progress = full.deal.progress
  const pct = progress.required ? Math.round((progress.confirmed / progress.required) * 100) : 0

  const sections = useMemo(() => {
    const map = new Map<string, ExtractedItem[]>()
    for (const it of items) {
      if (onlyPending && it.status === 'confirmed') continue
      if (!map.has(it.section)) map.set(it.section, [])
      map.get(it.section)!.push(it)
    }
    return [...map.entries()]
  }, [items, onlyPending])

  const openItem = (item: ExtractedItem) => {
    setSelected(item)
    setEditMode(false)
    setMismatchChoice(null)
    setResolutionNote(item.resolution_note ?? '')
    setEditText(item.effective_text ?? '')
    const vals: Record<string, string> = {}
    for (const [y, v] of Object.entries(item.effective_values ?? {})) vals[y] = String(v)
    setEditValues(vals)
  }

  const doAction = async (action: string, extra: Record<string, unknown> = {}) => {
    if (!selected || busy) return
    setBusy(true)
    try {
      await api.itemAction(dealId, selected.id, { action, user: userKey, ...extra })
      await refresh()
      setSelected(null)
    } finally {
      setBusy(false)
    }
  }

  const confirmAsIs = () => {
    const extra: Record<string, unknown> = {}
    if (selected?.mismatch && mismatchChoice) {
      const model = selected.values?.FY27
      const dd = selected.mismatch.other_value
      extra.values = { FY27: mismatchChoice === 'model' ? model : dd }
      extra.resolution_note = resolutionNote
        || (mismatchChoice === 'model'
          ? `モデル値${model?.toLocaleString()}を採用（財務DD値${dd.toLocaleString()}との差異はPPAで確定予定）`
          : `財務DD値${dd.toLocaleString()}を採用（保守的な評価を優先）`)
    }
    doAction('confirm', extra)
  }

  const confirmEdited = () => {
    const extra: Record<string, unknown> = {}
    if (selected?.values) {
      const vals: Record<string, number> = {}
      for (const [y, v] of Object.entries(editValues)) {
        const n = Number(v)
        if (!Number.isNaN(n)) vals[y] = n
      }
      extra.values = vals
    }
    if (selected?.text_value != null) extra.text_value = editText
    if (resolutionNote) extra.resolution_note = resolutionNote
    doAction('confirm', extra)
  }

  return (
    <div>
      {/* 確定進捗 */}
      <div className="card flex items-center gap-5 px-5 py-3">
        <div className="text-[13px] font-bold">確定進捗</div>
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-container">
          <div className="h-full rounded-full bg-primary-container transition-all" style={{ width: `${pct}%` }} />
        </div>
        <div className="font-data-tabular text-[13px]">
          確定 <b>{progress.confirmed}</b>/{progress.required}必須項目
          {progress.held > 0 && <span className="ml-1 text-outline">（保留 {progress.held}）</span>}
        </div>
        <label className="flex cursor-pointer items-center gap-1.5 text-[12px] text-on-surface-variant">
          <input type="checkbox" checked={onlyPending} onChange={(e) => setOnlyPending(e.target.checked)} />
          未確定のみ表示
        </label>
      </div>

      {progress.required > 0 && progress.confirmed === progress.required && (
        <div className="mt-3 flex items-center gap-2 rounded border border-green-300 bg-green-50 px-4 py-2.5 text-[13px] text-green-800">
          <Icon name="check_circle" className="text-[18px]" fill />
          必須項目がすべて確定しました。KPI構造タブへ進めます。
        </div>
      )}

      {items.length === 0 && (
        <div className="card mt-4 p-12 text-center text-[13px] text-outline">
          資料のAI解析が完了すると、抽出された数値がここに表示されます。
        </div>
      )}

      {/* セクション別テーブル */}
      {sections.map(([section, sectionItems]) => {
        const numeric = sectionItems.filter((i) => i.values)
        const textual = sectionItems.filter((i) => !i.values)
        const years = sortYears([...new Set(numeric.flatMap((i) => Object.keys(i.effective_values ?? {})))])
        return (
          <section key={section} className="card mt-4 overflow-hidden">
            <div className="border-b border-surface-container-high bg-surface-container-low/50 px-4 py-2.5 text-[13px] font-bold">
              {section}
            </div>
            {numeric.length > 0 && (
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-surface-container-high text-left text-[11px] text-on-surface-variant">
                    <th className="px-4 py-2 font-medium">項目（百万円）</th>
                    {years.map((y) => (
                      <th key={y} className="px-3 py-2 text-right font-medium">
                        {y}
                        <span className="ml-0.5 text-outline-variant">{['FY24', 'FY25', 'FY26'].includes(y) ? '実' : ''}</span>
                      </th>
                    ))}
                    <th className="w-24 px-3 py-2 text-center font-medium">状態</th>
                  </tr>
                </thead>
                <tbody>
                  {numeric.map((item) => (
                    <tr
                      key={item.id}
                      onClick={() => openItem(item)}
                      className={`cursor-pointer border-b border-surface-container-low last:border-0 hover:bg-primary-fixed/20 ${
                        selected?.id === item.id ? 'bg-primary-fixed/30' : ''
                      }`}
                    >
                      <td className="px-4 py-2.5">
                        <span className="font-medium">{item.label}</span>
                        {!item.required && <span className="ml-1.5 text-[10px] text-outline">任意</span>}
                        {item.mismatch && (
                          <span className="badge-base badge-warning ml-2 !px-1.5 !py-0 !text-[10px]">
                            <Icon name="warning" className="text-[11px]" /> 不整合
                          </span>
                        )}
                      </td>
                      {years.map((y) => {
                        const v = item.effective_values?.[y]
                        const orig = item.values?.[y]
                        const changed = item.edited && orig !== undefined && v !== orig
                        return (
                          <td key={y} className="px-3 py-2.5 text-right">
                            {v != null ? (
                              <span className={`font-data-tabular ${changed ? 'font-bold text-primary-container' : ''} ${item.mismatch ? 'rounded bg-amber-50 px-1 py-0.5 outline outline-1 outline-amber-300' : ''}`}>
                                {v.toLocaleString()}
                              </span>
                            ) : <span className="text-outline-variant">－</span>}
                          </td>
                        )
                      })}
                      <td className="px-3 py-2.5 text-center"><StatusIcon item={item} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {textual.map((item) => (
              <div
                key={item.id}
                onClick={() => openItem(item)}
                className={`flex cursor-pointer items-start gap-4 border-t border-surface-container-low px-4 py-3 hover:bg-primary-fixed/20 ${
                  selected?.id === item.id ? 'bg-primary-fixed/30' : ''
                }`}
              >
                <div className="w-52 shrink-0 text-[13px] font-medium">
                  {item.label}
                  {!item.required && <span className="ml-1.5 text-[10px] text-outline">任意</span>}
                </div>
                <div className="flex-1 text-[13px] leading-relaxed text-on-surface-variant">
                  {item.effective_text ?? (item.effective_values?.FY26 != null ? `${item.effective_values.FY26.toLocaleString()}百万円` : '')}
                </div>
                <div className="w-20 text-center"><StatusIcon item={item} /></div>
              </div>
            ))}
          </section>
        )
      })}

      {/* 根拠スライドパネル */}
      {selected && (
        <SlidePanel
          title={
            <div className="flex items-center gap-2">
              <span>{selected.label}</span>
              <StatusIcon item={selected} />
            </div>
          }
          onClose={() => setSelected(null)}
          footer={
            <div className="space-y-2">
              {selected.mismatch && selected.status !== 'confirmed' && !mismatchChoice && (
                <div className="text-center text-[11px] text-amber-700">
                  不整合があります。採用する値を上で選択してください。
                </div>
              )}
              {!editMode ? (
                <div className="flex gap-2">
                  <button
                    className="btn-primary flex-1 justify-center"
                    disabled={busy || (!!selected.mismatch && selected.status !== 'confirmed' && !mismatchChoice)}
                    onClick={confirmAsIs}
                  >
                    <Icon name="check" className="text-[16px]" />
                    {selected.status === 'confirmed' ? '再確定' : 'そのまま確定'}
                  </button>
                  <button className="btn-secondary flex-1 justify-center" disabled={busy} onClick={() => setEditMode(true)}>
                    <Icon name="edit" className="text-[16px]" /> 修正して確定
                  </button>
                  {selected.status !== 'held' ? (
                    <button className="btn-secondary" disabled={busy} onClick={() => doAction('hold')}>保留</button>
                  ) : (
                    <button className="btn-secondary" disabled={busy} onClick={() => doAction('unconfirm')}>保留解除</button>
                  )}
                </div>
              ) : (
                <div className="flex gap-2">
                  <button className="btn-primary flex-1 justify-center" disabled={busy} onClick={confirmEdited}>
                    <Icon name="check" className="text-[16px]" /> この内容で確定
                  </button>
                  <button className="btn-secondary" disabled={busy} onClick={() => setEditMode(false)}>戻る</button>
                </div>
              )}
              {selected.status === 'confirmed' && !editMode && (
                <button className="w-full text-center text-[11px] text-outline underline" disabled={busy} onClick={() => doAction('unconfirm')}>
                  確定を解除する（下流に警告が表示されます）
                </button>
              )}
            </div>
          }
        >
          {/* 値の表示・編集 */}
          {selected.values && !editMode && (
            <div className="mb-4 rounded bg-surface-container-low/60 p-3">
              <div className="flex flex-wrap gap-x-5 gap-y-1">
                {sortYears(Object.keys(selected.effective_values ?? {})).map((y) => (
                  <div key={y}>
                    <span className="text-[11px] text-outline">{y}</span>
                    <div className="font-data-tabular text-[18px] font-bold text-primary-container">
                      {selected.effective_values?.[y]?.toLocaleString()}
                      <span className="ml-1 text-[11px] font-normal text-outline">{selected.unit}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {editMode && selected.values && (
            <div className="mb-4 space-y-2 rounded border border-primary-container/30 bg-primary-fixed/10 p-3">
              <div className="text-[12px] font-bold text-primary-container">値を修正（{selected.unit}）</div>
              {sortYears(Object.keys(selected.effective_values ?? {})).map((y) => (
                <label key={y} className="flex items-center gap-2 text-[12px]">
                  <span className="w-12 text-outline">{y}</span>
                  <input
                    type="number"
                    className="input-base font-data-tabular !py-1"
                    value={editValues[y] ?? ''}
                    onChange={(e) => setEditValues({ ...editValues, [y]: e.target.value })}
                  />
                </label>
              ))}
              <input
                className="input-base !py-1 !text-[12px]"
                placeholder="修正理由（任意）"
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
              />
            </div>
          )}
          {selected.text_value && !editMode && (
            <div className="mb-4 rounded bg-surface-container-low/60 p-3 text-[13px] leading-relaxed">
              {selected.effective_text}
            </div>
          )}
          {editMode && selected.text_value != null && (
            <div className="mb-4">
              <textarea className="input-base h-28 !text-[12px]" value={editText} onChange={(e) => setEditText(e.target.value)} />
            </div>
          )}

          {/* 不整合警告と選択 */}
          {selected.mismatch && (
            <div className="mb-4 rounded border border-amber-300 bg-amber-50 p-3">
              <div className="flex items-center gap-1.5 text-[12px] font-bold text-amber-800">
                <Icon name="warning" className="text-[16px]" /> 資料間の不整合
              </div>
              <p className="mt-1.5 text-[12px] leading-relaxed text-amber-900">{selected.mismatch.note}</p>
              <div className="mt-2 rounded border border-amber-200 bg-white p-2 text-[11px] text-on-surface-variant">
                <div className="font-medium">{selected.mismatch.other_file}（{selected.mismatch.other_location}）</div>
                <div className="mt-1">「{selected.mismatch.other_quote}」</div>
              </div>
              {selected.status !== 'confirmed' && (
                <div className="mt-2.5 space-y-1.5">
                  <label className="flex cursor-pointer items-center gap-2 rounded border border-amber-200 bg-white px-2.5 py-1.5 text-[12px]">
                    <input type="radio" name="mm" checked={mismatchChoice === 'model'} onChange={() => setMismatchChoice('model')} />
                    財務モデルの値を採用（<b className="font-data-tabular">{selected.values?.FY27?.toLocaleString()}</b>）
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 rounded border border-amber-200 bg-white px-2.5 py-1.5 text-[12px]">
                    <input type="radio" name="mm" checked={mismatchChoice === 'dd'} onChange={() => setMismatchChoice('dd')} />
                    財務DDの値を採用（<b className="font-data-tabular">{selected.mismatch.other_value.toLocaleString()}</b>）
                  </label>
                </div>
              )}
              {selected.resolution_note && (
                <div className="mt-2 text-[11px] text-amber-800">解決メモ：{selected.resolution_note}</div>
              )}
            </div>
          )}

          {/* 根拠3点セット */}
          {selected.evidence && <EvidenceBlock evidence={selected.evidence} />}

          {selected.status === 'confirmed' && (
            <div className="mt-4 rounded bg-surface-container-low/60 px-3 py-2 text-[11px] text-outline">
              確定：{selected.confirmed_by === 'tanaka' ? '田中' : selected.confirmed_by === 'sato' ? '佐藤' : selected.confirmed_by === 'takahashi' ? '高橋' : selected.confirmed_by}
              {selected.confirmed_at && `　${new Date(selected.confirmed_at).toLocaleString('ja-JP')}`}
            </div>
          )}

          {/* この項目への指摘（審査相談） */}
          {full.findings.filter((f) => f.target_type === 'item' && f.target_key === selected.key).map((f) => (
            <div key={f.id} className="mt-4 rounded border border-amber-300 bg-amber-50 p-3 text-[12px]">
              <div className="flex items-center gap-1 font-bold text-amber-800">
                <Icon name="feedback" className="text-[14px]" /> 前回審査相談での指摘
              </div>
              <p className="mt-1 text-amber-900">{f.text}</p>
            </div>
          ))}
        </SlidePanel>
      )}
    </div>
  )
}
