import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Icon } from './Icon'
import { useUser } from '../context/UserContext'
import type { ChatDiff } from '../types'

interface Message {
  role: 'user' | 'ai'
  text: string
  diff?: ChatDiff | null
  diffState?: 'pending' | 'applied' | 'discarded'
}

/**
 * ステージ2・3の右側常駐チャットパネル。
 * AIの提案は必ず「変更差分プレビュー → 適用」を挟む（直接反映しない）。
 */
export function ChatPanel({ dealId, context, suggestions, renderDiff, onApply, title }: {
  dealId: number
  context: 'kpi' | 'scenario'
  suggestions: string[]
  renderDiff: (diff: ChatDiff) => React.ReactNode
  onApply: (diff: ChatDiff) => Promise<void>
  title: string
}) {
  const { userKey } = useUser()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [suggestionIdx, setSuggestionIdx] = useState(0)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  const placeholder = suggestions.length
    ? suggestions[suggestionIdx % suggestions.length]
    : '修正したい内容を入力…'

  const send = async (text?: string) => {
    const message = (text ?? input).trim() || placeholder
    if (!message || busy) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: message }])
    setBusy(true)
    try {
      const res = await api.chat(dealId, context, message, userKey)
      setMessages((m) => [...m, {
        role: 'ai', text: res.reply, diff: res.diff,
        diffState: res.diff ? 'pending' : undefined,
      }])
      setSuggestionIdx((i) => i + 1)
    } catch (e) {
      setMessages((m) => [...m, { role: 'ai', text: `エラー：${(e as Error).message}` }])
    } finally {
      setBusy(false)
    }
  }

  const applyDiff = async (idx: number) => {
    const msg = messages[idx]
    if (!msg.diff || msg.diffState !== 'pending') return
    try {
      await onApply(msg.diff)
      setMessages((m) => m.map((x, i) => (i === idx ? { ...x, diffState: 'applied' } : x)))
    } catch (e) {
      setMessages((m) => [...m, { role: 'ai', text: `適用エラー：${(e as Error).message}` }])
    }
  }

  const discardDiff = (idx: number) => {
    setMessages((m) => m.map((x, i) => (i === idx ? { ...x, diffState: 'discarded' } : x)))
  }

  return (
    <div className="card flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-surface-container-high px-4 py-3">
        <Icon name="smart_toy" className="text-[18px] text-primary-container" />
        <span className="text-[13px] font-bold">{title}</span>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-3">
        {messages.length === 0 && (
          <div className="rounded bg-surface-container-low/70 p-3 text-[12px] leading-relaxed text-on-surface-variant">
            自然言語で修正を指示できます。AIの提案は差分プレビューで確認してから適用されます。
            <div className="mt-2 space-y-1">
              {suggestions.map((s) => (
                <button
                  key={s}
                  className="block w-full rounded border border-surface-container-high bg-white px-2.5 py-1.5 text-left text-[12px] text-primary-container hover:border-primary-container"
                  onClick={() => send(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'flex justify-end' : ''}>
            <div className={`max-w-[92%] rounded px-3 py-2 text-[12px] leading-relaxed ${
              m.role === 'user'
                ? 'bg-primary-container text-white'
                : 'border border-surface-container-high bg-surface-container-low/50'
            }`}
            >
              {m.text}
              {m.diff && (
                <div className="mt-2">
                  <div className={`rounded border p-2.5 ${
                    m.diffState === 'applied' ? 'border-green-300 bg-green-50'
                      : m.diffState === 'discarded' ? 'border-surface-container-high bg-surface-container-low opacity-60'
                        : 'border-green-300 bg-green-50'
                  }`}
                  >
                    <div className="mb-1.5 flex items-center gap-1 text-[11px] font-bold text-green-800">
                      <Icon name="difference" className="text-[14px]" /> 変更差分プレビュー
                    </div>
                    {renderDiff(m.diff)}
                  </div>
                  {m.diffState === 'pending' && (
                    <div className="mt-2 flex gap-2">
                      <button className="btn-primary !py-1 !text-[12px]" onClick={() => applyDiff(i)}>
                        <Icon name="check" className="text-[14px]" /> 適用
                      </button>
                      <button className="btn-secondary !py-1 !text-[12px]" onClick={() => discardDiff(i)}>破棄</button>
                    </div>
                  )}
                  {m.diffState === 'applied' && (
                    <div className="mt-1.5 flex items-center gap-1 text-[11px] font-medium text-green-700">
                      <Icon name="check_circle" className="text-[14px]" fill /> 適用しました
                    </div>
                  )}
                  {m.diffState === 'discarded' && (
                    <div className="mt-1.5 text-[11px] text-outline">破棄しました</div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-[12px] text-outline">
            <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-surface-container-high border-t-primary-container" />
            AIが検討しています…
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-surface-container-high p-3">
        <div className="flex gap-2">
          <input
            className="input-base !text-[12px]"
            placeholder={placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) send() }}
          />
          <button className="btn-primary !px-3" onClick={() => send()} disabled={busy}>
            <Icon name="send" className="text-[16px]" />
          </button>
        </div>
        <div className="mt-1.5 text-[10px] text-outline">
          Enterで送信。空欄のまま送信するとプレースホルダーの文言を送ります。
        </div>
      </div>
    </div>
  )
}
