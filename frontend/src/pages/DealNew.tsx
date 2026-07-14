import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Layout } from '../components/Layout'
import { Icon } from '../components/Icon'
import { LoadingOverlay } from '../components/LoadingOverlay'
import { useUser } from '../context/UserContext'

const SLOTS: { key: string; label: string; required: boolean; accept: string }[] = [
  { key: 'model_sponsor', label: '財務モデル：スポンサーケース', required: true, accept: '.xlsx' },
  { key: 'model_base', label: '財務モデル：ベースケース', required: true, accept: '.xlsx' },
  { key: 'dd_business', label: '事業DDレポート', required: true, accept: '.pdf' },
  { key: 'dd_financial', label: '財務DDレポート', required: true, accept: '.pdf' },
  { key: 'dd_legal', label: '法務DDレポート', required: true, accept: '.pdf' },
  { key: 'dd_tax', label: '税務DDレポート', required: false, accept: '.pdf' },
]

interface UploadedInfo {
  filename: string
  identified_company: string | null
  identified_label: string | null
  company_match: boolean
}

function Field({ label, required, children, className = '' }: {
  label: string; required?: boolean; children: React.ReactNode; className?: string
}) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 flex items-center gap-1.5 text-[12px] font-medium text-on-surface-variant">
        {label}
        {required && <span className="badge-base badge-error !px-1.5 !py-0 !text-[10px]">必須</span>}
      </span>
      {children}
    </label>
  )
}

export function DealNew() {
  const navigate = useNavigate()
  const { users, userKey } = useUser()
  const [form, setForm] = useState({
    name: '', deal_type: 'LBO', borrower: '', target: '', industry: '', sponsor: '',
    close_date: '', next_meeting_date: '', ev_mm: '', senior_mm: '',
    our_commitment_mm: '', equity_mm: '', tenor_years: '7', sponsor_ebitda_mm: '',
    summary: '', owner: '',
  })
  const [dealId, setDealId] = useState<number | null>(null)
  const [uploads, setUploads] = useState<Record<string, UploadedInfo>>({})
  const [uploading, setUploading] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const fileInputs = useRef<Record<string, HTMLInputElement | null>>({})

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value })

  // 初期レバレッジ・LTV（入力値からの自動算出＝四則演算のみ）
  const leverage = useMemo(() => {
    const s = Number(form.senior_mm); const e = Number(form.sponsor_ebitda_mm)
    return s > 0 && e > 0 ? (s / e).toFixed(1) : null
  }, [form.senior_mm, form.sponsor_ebitda_mm])
  const ltv = useMemo(() => {
    const s = Number(form.senior_mm); const ev = Number(form.ev_mm)
    return s > 0 && ev > 0 ? Math.round((s / ev) * 100) : null
  }, [form.senior_mm, form.ev_mm])

  const canRegister = form.name && form.borrower && form.target
  const requiredUploaded = SLOTS.filter((s) => s.required).every((s) => uploads[s.key])
  const uploadedCount = Object.keys(uploads).length

  const register = async () => {
    setError('')
    try {
      const body: Record<string, unknown> = {
        name: form.name, deal_type: form.deal_type, borrower: form.borrower,
        target: form.target, industry: form.industry || null, sponsor: form.sponsor || null,
        close_date: form.close_date || null, next_meeting_date: form.next_meeting_date || null,
        ev_mm: form.ev_mm ? Number(form.ev_mm) : null,
        senior_mm: form.senior_mm ? Number(form.senior_mm) : null,
        our_commitment_mm: form.our_commitment_mm ? Number(form.our_commitment_mm) : null,
        equity_mm: form.equity_mm ? Number(form.equity_mm) : null,
        tenor_years: form.tenor_years ? Number(form.tenor_years) : null,
        sponsor_ebitda_mm: form.sponsor_ebitda_mm ? Number(form.sponsor_ebitda_mm) : null,
        summary: form.summary || null, user: form.owner || userKey,
      }
      const deal = await api.createDeal(body)
      setDealId(deal.id)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const upload = async (slot: string, file: File) => {
    if (!dealId) return
    setUploading(slot)
    setError('')
    try {
      const res = await api.uploadDocument(dealId, slot, file, userKey)
      setUploads((u) => ({
        ...u,
        [slot]: {
          filename: file.name,
          identified_company: res.identified_company,
          identified_label: res.identified_label,
          company_match: res.company_match,
        },
      }))
    } catch (e) {
      setError(`${file.name}: ${(e as Error).message}`)
    } finally {
      setUploading(null)
    }
  }

  const analyze = async () => {
    if (!dealId) return
    setAnalyzing(true)
    try {
      await api.analyze(dealId, userKey)
      navigate(`/deals/${dealId}?tab=numbers&analyzed=1`)
    } catch (e) {
      setError((e as Error).message)
      setAnalyzing(false)
    }
  }

  return (
    <Layout breadcrumb={<><span className="text-outline-variant">/</span><span className="font-medium">新規案件を登録</span></>}>
      {analyzing && <LoadingOverlay title="資料を解析しています…" />}
      <div className="mx-auto max-w-[960px]">
        <h1 className="text-[24px] font-bold">案件登録</h1>
        <p className="mt-1 text-[13px] text-on-surface-variant">
          案件の基礎情報と資料を登録し、事実（財務データ）の整理を開始します。
        </p>

        {/* ---- 案件基本情報 ---- */}
        <section className="card mt-5">
          <div className="border-b border-surface-container-high px-5 py-3 text-[14px] font-bold">
            案件基本情報
          </div>
          <div className="grid grid-cols-3 gap-4 p-5">
            <Field label="案件名" required className="col-span-2">
              <input className="input-base" value={form.name} onChange={set('name')}
                placeholder="例：オートスタッフ中部 LBOファイナンス" disabled={!!dealId} />
            </Field>
            <Field label="担当者">
              <select className="input-base" value={form.owner || userKey} onChange={set('owner')} disabled={!!dealId}>
                {users.map((u) => <option key={u.key} value={u.key}>{u.display}</option>)}
              </select>
            </Field>
            <Field label="案件種別" required>
              <select className="input-base" value={form.deal_type} onChange={set('deal_type')} disabled={!!dealId}>
                {['LBO', 'MBO', '事業承継', 'リファイナンス'].map((t) => <option key={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="借入人（SPC）" required>
              <input className="input-base" value={form.borrower} onChange={set('borrower')}
                placeholder="株式会社ASホールディングス" disabled={!!dealId} />
            </Field>
            <Field label="対象会社" required>
              <input className="input-base" value={form.target} onChange={set('target')}
                placeholder="株式会社オートスタッフ中部" disabled={!!dealId} />
            </Field>
            <Field label="対象会社の業種">
              <input className="input-base" value={form.industry} onChange={set('industry')}
                placeholder="自動車製造派遣（東海地盤）" disabled={!!dealId} />
            </Field>
            <Field label="スポンサー">
              <input className="input-base" value={form.sponsor} onChange={set('sponsor')}
                placeholder="日本橋キャピタルパートナーズ株式会社" disabled={!!dealId} />
            </Field>
            <Field label="クローズ予定日">
              <input type="date" className="input-base" value={form.close_date} onChange={set('close_date')} disabled={!!dealId} />
            </Field>
            <Field label="審査相談予定日">
              <input type="date" className="input-base" value={form.next_meeting_date} onChange={set('next_meeting_date')} disabled={!!dealId} />
            </Field>
          </div>

          <div className="mx-5 mb-5 rounded border border-surface-container-high bg-surface-container-low/50 p-4">
            <div className="flex items-center justify-between">
              <div className="text-[12px] font-bold text-on-surface-variant">資金調達構造（百万円）</div>
              <div className="text-[12px] text-on-surface-variant">
                {leverage && ltv ? (
                  <>初期レバレッジ <b className="font-data-tabular text-primary-container">{leverage}x</b>
                    ／LTV <b className="font-data-tabular text-primary-container">{ltv}%</b>（自動計算）</>
                ) : '（シニア・EV・EBITDAを入力すると自動計算）'}
              </div>
            </div>
            <div className="mt-3 grid grid-cols-5 gap-3">
              <Field label="買収総額（EV）">
                <input type="number" className="input-base font-data-tabular" value={form.ev_mm} onChange={set('ev_mm')} placeholder="12,000" disabled={!!dealId} />
              </Field>
              <Field label="シニアローン総額">
                <input type="number" className="input-base font-data-tabular" value={form.senior_mm} onChange={set('senior_mm')} placeholder="6,500" disabled={!!dealId} />
              </Field>
              <Field label="うち本行取組額">
                <input type="number" className="input-base font-data-tabular !border-primary-container/40 !bg-primary-fixed/20" value={form.our_commitment_mm} onChange={set('our_commitment_mm')} placeholder="2,500" disabled={!!dealId} />
              </Field>
              <Field label="エクイティ">
                <input type="number" className="input-base font-data-tabular" value={form.equity_mm} onChange={set('equity_mm')} placeholder="5,500" disabled={!!dealId} />
              </Field>
              <Field label="提示EBITDA（速報）">
                <input type="number" className="input-base font-data-tabular" value={form.sponsor_ebitda_mm} onChange={set('sponsor_ebitda_mm')} placeholder="1,585" disabled={!!dealId} />
              </Field>
            </div>
          </div>

          <div className="px-5 pb-5">
            <Field label="案件概要">
              <textarea className="input-base h-20" value={form.summary} onChange={set('summary')}
                placeholder="案件の背景・ストラクチャーの概要" disabled={!!dealId} />
            </Field>
          </div>
        </section>

        {/* ---- 案件資料 ---- */}
        <section className={`card mt-5 ${!dealId ? 'opacity-50' : ''}`}>
          <div className="flex items-center justify-between border-b border-surface-container-high px-5 py-3">
            <span className="text-[14px] font-bold">案件資料</span>
            <span className="badge-base badge-info">{uploadedCount}/6 アップロード済</span>
          </div>
          {!dealId && (
            <div className="px-5 pt-3 text-[12px] text-outline">
              基本情報を登録すると資料をアップロードできます。
            </div>
          )}
          <div className="grid grid-cols-3 gap-3 p-5">
            {SLOTS.map((slot) => {
              const up = uploads[slot.key]
              return (
                <div
                  key={slot.key}
                  className={`rounded border p-3 ${up ? 'border-green-300 bg-green-50/40' : 'border-dashed border-outline-variant'} ${dealId ? 'cursor-pointer hover:border-primary-container' : ''}`}
                  onClick={() => dealId && fileInputs.current[slot.key]?.click()}
                >
                  <div className="flex items-start justify-between">
                    <div className="text-[12px] font-bold">{slot.label}</div>
                    <span className={`badge-base !text-[10px] !px-1.5 !py-0 ${slot.required ? 'badge-error' : 'badge-neutral'}`}>
                      {slot.required ? '必須' : '任意'}
                    </span>
                  </div>
                  <input
                    ref={(el) => { fileInputs.current[slot.key] = el }}
                    type="file" accept={slot.accept} className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0]
                      if (f) upload(slot.key, f)
                      e.target.value = ''
                    }}
                  />
                  <div className="mt-2 min-h-[40px]">
                    {uploading === slot.key ? (
                      <div className="flex items-center gap-2 text-[12px] text-primary-container">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-surface-container-high border-t-primary-container" />
                        識別しています…
                      </div>
                    ) : up ? (
                      <div className="text-[12px]">
                        <div className="flex items-center gap-1 text-green-700">
                          <Icon name="check_circle" className="text-[16px]" fill />
                          <span className="truncate">{up.filename}</span>
                        </div>
                        <div className="mt-0.5 text-[11px] text-outline">
                          {up.identified_label}
                          {up.identified_company && !up.company_match && (
                            <span className="badge-base badge-warning ml-1 !px-1.5 !py-0 !text-[10px]">
                              社名不一致：{up.identified_company}
                            </span>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-[11px] text-outline">
                        <Icon name="upload_file" className="text-[16px]" />
                        クリックしてファイルを選択
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        {error && (
          <div className="mt-4 flex items-center gap-2 rounded border border-error/30 bg-error-container/40 px-4 py-2.5 text-[13px] text-on-error-container">
            <Icon name="error" className="text-[18px]" /> {error}
          </div>
        )}

        <div className="mt-5 flex justify-end gap-3 pb-10">
          {!dealId ? (
            <button className="btn-primary" disabled={!canRegister} onClick={register}>
              登録して資料アップロードへ <Icon name="arrow_forward" className="text-[16px]" />
            </button>
          ) : (
            <>
              <span className="self-center text-[12px] text-outline">
                {requiredUploaded ? '必須資料が揃いました。解析を実行してください。' : '必須資料をアップロードしてください。'}
              </span>
              <button className="btn-primary" disabled={!requiredUploaded} onClick={analyze}>
                <Icon name="neurology" className="text-[18px]" /> AI解析を実行
              </button>
            </>
          )}
        </div>
      </div>
    </Layout>
  )
}
