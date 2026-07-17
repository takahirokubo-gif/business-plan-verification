import { useEffect, useState } from 'react'
import { api } from '../api'
import type { ExtractorMode } from '../api'
import { Icon } from './Icon'

const OPTIONS = [
  {
    mode: 'mock' as const,
    icon: 'smart_toy',
    title: 'モックモード',
    desc: 'サンプルファイル専用のデモモード。APIキー不要で、用意済みの解析結果を数秒で返します。',
  },
  {
    mode: 'anthropic' as const,
    icon: 'neurology',
    title: 'AIモード',
    desc: 'Anthropic API（claude-sonnet-4-6）で任意の資料を実際に解析します。AI解析は数分かかります。',
  },
]

/** 抽出エンジンの切替（設定モーダル用のカード型ボタン）。
 *  APIキーはサーバー側 backend/.env の ANTHROPIC_API_KEY から読み込まれる。 */
export function ModeToggle() {
  const [state, setState] = useState<ExtractorMode | null>(null)
  const [error, setError] = useState('')
  const [switching, setSwitching] = useState(false)

  useEffect(() => {
    api.getMode().then(setState).catch(() => setError('設定の取得に失敗しました'))
  }, [])

  const switchTo = async (mode: 'mock' | 'anthropic') => {
    if (!state || state.mode === mode || switching) return
    setSwitching(true)
    setError('')
    try {
      setState(await api.setMode(mode))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSwitching(false)
    }
  }

  const switchModel = async (model: string) => {
    if (!state || state.model === model || switching) return
    setSwitching(true)
    setError('')
    try {
      setState(await api.setModel(model))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSwitching(false)
    }
  }

  if (!state && !error) {
    return (
      <div className="flex items-center gap-2 py-4 text-[13px] text-on-surface-variant">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-surface-container-high border-t-primary-container" />
        設定を読み込んでいます…
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      {state && (
        <div className="grid grid-cols-2 gap-3">
          {OPTIONS.map((opt) => {
            const active = state.mode === opt.mode
            const disabled = opt.mode === 'anthropic' && !state.anthropic_available
            return (
              <button
                key={opt.mode}
                disabled={disabled || switching}
                onClick={() => switchTo(opt.mode)}
                title={disabled ? 'AIモードには backend/.env に ANTHROPIC_API_KEY の設定が必要です' : undefined}
                className={`relative rounded border p-4 text-left transition-colors ${
                  active
                    ? 'border-2 border-primary-container bg-primary-fixed/30'
                    : disabled
                      ? 'cursor-not-allowed border-surface-container-high opacity-50'
                      : 'cursor-pointer border-surface-container-high hover:border-primary-container/60 hover:bg-surface-container-low'
                } ${switching ? 'opacity-70' : ''}`}
              >
                <span
                  className={`absolute right-3 top-3 flex items-center gap-1 text-[11px] font-bold ${
                    active ? 'text-primary-container' : 'text-outline-variant'
                  }`}
                >
                  <Icon name={active ? 'check_circle' : 'radio_button_unchecked'} className="text-[16px]" fill={active} />
                  {active && '使用中'}
                </span>
                <span className="mb-1.5 flex items-center gap-2">
                  <span
                    className={`flex h-8 w-8 items-center justify-center rounded-full ${
                      active ? 'bg-primary-container text-white' : 'bg-surface-container text-on-surface-variant'
                    }`}
                  >
                    <Icon name={opt.icon} className="text-[18px]" fill={active} />
                  </span>
                  <span className={`text-[14px] font-bold ${active ? 'text-primary-container' : ''}`}>{opt.title}</span>
                </span>
                <span className="block text-[12px] leading-relaxed text-on-surface-variant">{opt.desc}</span>
                {disabled && (
                  <span className="mt-1.5 flex items-center gap-1 text-[11px] text-error">
                    <Icon name="key_off" className="text-[14px]" />
                    backend/.env に ANTHROPIC_API_KEY の設定が必要です
                  </span>
                )}
              </button>
            )
          })}
        </div>
      )}
      {/* AIモデルの選択（AIモード時に使用。一覧はAnthropic APIから動的取得） */}
      {state && (
        <div className="flex flex-wrap items-center gap-2 rounded border border-surface-container-high bg-surface-container-low/50 px-3 py-2.5">
          <span className="flex items-center gap-1.5 text-[12px] font-bold">
            <Icon name="tune" className="text-[16px] text-primary-container" />
            AIモデル
          </span>
          <select
            className="input-base !w-auto min-w-[240px] !py-1 !text-[12px]"
            value={state.model}
            disabled={!state.anthropic_available || switching}
            title={state.model}
            onChange={(e) => switchModel(e.target.value)}
          >
            {state.models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.display_name}
              </option>
            ))}
          </select>
          <span className="text-[11px] text-on-surface-variant">
            {state.anthropic_available
              ? 'AIモード時の解析に使用（モックモードでは使用されません）'
              : 'APIキー設定後に選択できます'}
          </span>
        </div>
      )}
      {switching && (
        <p className="flex items-center gap-1.5 text-[11px] text-on-surface-variant">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-surface-container-high border-t-primary-container" />
          切り替えています…
        </p>
      )}
      {error && (
        <p className="flex items-center gap-1.5 rounded border border-error/30 bg-error-container/40 px-3 py-2 text-[12px] text-on-error-container">
          <Icon name="error" className="text-[16px]" /> {error}
        </p>
      )}
    </div>
  )
}
