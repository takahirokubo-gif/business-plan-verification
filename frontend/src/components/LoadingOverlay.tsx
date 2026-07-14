import { useEffect, useState } from 'react'

const DEFAULT_STEPS = [
  '資料を読み込んでいます…',
  '財務モデルのシート構造を解析しています…',
  'DDレポートから定性情報を抽出しています…',
  '抽出値に根拠を紐付けています…',
]

export function LoadingOverlay({ title, steps = DEFAULT_STEPS }: {
  title: string
  steps?: string[]
}) {
  const [step, setStep] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setStep((s) => Math.min(s + 1, steps.length - 1)), 900)
    return () => clearInterval(t)
  }, [steps.length])
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white/85 backdrop-blur-sm">
      <div className="h-12 w-12 animate-spin rounded-full border-4 border-surface-container-high border-t-primary-container" />
      <div className="mt-5 text-[16px] font-bold text-primary-container">{title}</div>
      <div className="mt-2 text-[13px] text-on-surface-variant">{steps[step]}</div>
    </div>
  )
}
