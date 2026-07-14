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

const EXTRACT_STEPS = [
  '資料の表紙・シート構造を確認しています…',
  '案件スキーム・当事者を特定しています…',
  'ストラクチャー（EV・ローン・エクイティ）を読み取っています…',
  '案件概要を要約しています…',
]

interface UploadedInfo {
  filename: string
  identified_label: string | null
}

function Field({ label, required, children, className = '', hint }: {
  label: string; required?: boolean; children: React.ReactNode; className?: string; hint?: string
}) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 flex items-center gap-1.5 text-[12px] font-medium text-on-surface-variant">
        {label}
        {required && <span className="badge-base badge-error !px-1.5 !py-0 !text-[10px]">必須</span>}
        {hint && <span className="text-[10px] text-outline">{hint}</span>}
      </span>
      {children}
    </label>
  )
}

const EMPTY_FORM = {
  name: '', deal_type: 'LBO', borrower: '', target: '', industry: '', sponsor: '',
  close_date: '', next_meeting_date: '', ev_mm: '', senior_mm: '',
  our_commitment_mm: '', equity_mm: '', tenor_years: '7', sponsor_ebitda_mm: '',
  summary: '', owner: '',
}

export function DealNew() {
  const navigate = useNavigate()
  const { users, userKey } = useUser()
  const [form, setForm] = useState({ ...EMPTY_FORM })
  const [dealId, setDealId] = useState<number | null>(null)
  const [uploads, setUploads] = useState<Record<string, UploadedInfo>>({})
  const [uploading, setUploading] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [extracting, setExtracting] = useState(false)
  const [extracted, setExtracted] = useState(false)
  const [sources, setSources] = useState<Record<string, string>>({})
  const [extractNote, setExtractNote] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const fileInputs = useRef<Record<string, HTMLInputElement | null>>({})

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value })

  const leverage = useMemo(() => {
    const s = Number(form.senior_mm); const e = Number(form.sponsor_ebitda_mm)
    return s > 0 && e > 0 ? (s / e).toFixed(1) : null
  }, [form.senior_mm, form.sponsor_ebitda_mm])
  const ltv = useMemo(() => {
    const s = Number(form.senior_mm); const ev = Number(form.ev_mm)
    return s > 0 && ev > 0 ? Math.round((s / ev) * 100) : null
  }, [form.senior_mm, form.ev_mm])

  const requiredUploaded = SLOTS.filter((s) => s.required).every((s) => uploads[s.key])
  const uploadedCount = Object.keys(uploads).length
  const canRegister = form.name && form.borrower && form.target && requiredUploaded

  const ensureDraft = async (): Promise<number> => {
    if (dealId) return dealId
    const d = await api.createDraft(userKey)
    setDealId(d.id)
    return d.id
  }

  const upload = async (slot: string, file: File) => {
    setUploading(slot)
    setError('')
    try {
      const id = await ensureDraft()
      await api.uploadDocument(id, slot, file, userKey)
      setUploads((u) => ({
        ...u,
        [slot]: { filename: file.name, identified_label: null },
      }))
    } catch (e) {
      setError(`${file.name}: ${(e as Error).message}`)
    } finally {
      setUploading(null)
    }
  }

  const extractInfo = async () => {
    if (!dealId) return
    setExtracting(true)
    setError('')
    try {
      const res = await api.extractDealInfo(dealId, userKey)
      const f = res.fields as Record<string, unknown>
      setForm((prev) => ({
        ...prev,
        name: String(f.name ?? prev.name),
        deal_type: String(f.deal_type ?? prev.deal_type),
        borrower: String(f.borrower ?? prev.borrower),
        target: String(f.target ?? prev.target),
        industry: String(f.industry ?? ''),
        sponsor: String(f.sponsor ?? ''),
        close_date: String(f.close_date ?? ''),
        ev_mm: f.ev_mm != null ? String(f.ev_mm) : prev.ev_mm,
        senior_mm: f.senior_mm != null ? String(f.senior_mm) : prev.senior_mm,
        equity_mm: f.equity_mm != null ? String(f.equity_mm) : prev.equity_mm,
        tenor_years: f.tenor_years != null ? String(f.tenor_years) : prev.tenor_years,
        sponsor_ebitda_mm: f.sponsor_ebitda_mm != null ? String(f.sponsor_ebitda_mm) : prev.sponsor_ebitda_mm,
        summary: String(f.summary ?? ''),
      }))
      setSources(res.sources)
      setExtractNote(res.note)
      setExtracted(true)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setExtracting(false)
    }
  }

  const registerAndAnalyze = async () => {
    if (!dealId) return
    setAnalyzing(true)
    setError('')
    try {
      await api.updateDeal(dealId, {
        name: form.name, deal_type: form.deal_type, borrower: form.borrower,
        target: form.target, industry: form.industry || null, sponsor: form.sponsor || null,
        close_date: form.close_date || null, next_meeting_date: form.next_meeting_date || null,
        ev_mm: form.ev_mm ? Number(form.ev_mm) : null,
        senior_mm: form.senior_mm ? Number(form.senior_mm) : null,
        our_commitment_mm: form.our_commitment_mm ? Number(form.our_commitment_mm) : null,
        equity_mm: form.equity_mm ? Number(form.equity_mm) : null,
        tenor_years: form.tenor_years ? Number(form.tenor_years) : null,
        sponsor_ebitda_mm: form.sponsor_ebitda_mm ? Number(form.sponsor_ebitda_mm) : null,
        summary: form.summary || null, owner: form.owner || userKey, user: userKey,
      })
      await api.analyze(dealId, userKey)
      navigate(`/deals/${dealId}?tab=numbers`)
    } catch (e) {
      setError((e as Error).message)
      setAnalyzing(false)
    }
  }

  const cancelDraft = async () => {
    if (dealId) {
      try { await api.deleteDeal(dealId) } catch { /* noop */ }
    }
    navigate('/')
  }

  return (
    <Layout breadcrumb={<><span className="text-outline-variant">/</span><span className="font-medium">新規案件を登録</span></>}>
      {extracting && <LoadingOverlay title="案件情報を読み取っています…" steps={EXTRACT_STEPS} />}
      {analyzing && <LoadingOverlay title="資料を解析しています…" />}
      <div className="mx-auto max-w-[960px]">
        <h1 className="text-[24px] font-bold">案件登録</h1>
        <p className="mt-1 text-[13px] text-on-surface-variant">
          資料をアップロードすると、AIが案件の基本情報を読み取ってフォームに自動入力します。
          内容を確認・修正して登録を確定してください。
        </p>

        {/* ---- STEP1 案件資料 ---- */}
        <section className="card mt-5">
          <div className="flex items-center justify-between border-b border-surface-container-high px-5 py-3">
            <span className="flex items-center gap-2 text-[14px] font-bold">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary-container text-[11px] font-bold text-white">1</span>
              案件資料をアップロード
            </span>
            <span className="badge-base badge-neutral">{uploadedCount}/6 アップロード済</span>
          </div>
          <div className="grid grid-cols-3 gap-3 p-5">
            {SLOTS.map((slot) => {
              const up = uploads[slot.key]
              return (
                <div
                  key={slot.key}
                  className={`cursor-pointer rounded border p-3 hover:border-primary-container ${up ? 'border-green-300 bg-green-50/40' : 'border-dashed border-outline-variant'}`}
                  onClick={() => fileInputs.current[slot.key]?.click()}
                >
                  <div className="flex items-start justify-between">
                    <div className="text-[12px] font-bold">{slot.label}</div>
                    <span className={`badge-base !px-1.5 !py-0 !text-[10px] ${slot.required ? 'badge-error' : 'badge-neutral'}`}>
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
                  <div className="mt-2 min-h-[24px]">
                    {uploading === slot.key ? (
                      <div className="flex items-center gap-2 text-[12px] text-primary-container">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-surface-container-high border-t-primary-container" />
                        アップロード中…
                      </div>
                    ) : up ? (
                      <div className="flex items-center gap-1 text-[12px] text-green-700">
                        <Icon name="check_circle" className="text-[16px]" fill />
                        <span className="truncate">{up.filename}</span>
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
          <div className="flex items-center justify-between border-t border-surface-container-low px-5 py-3">
            <span className="text-[12px] text-outline">
              {uploadedCount === 0
                ? '資料をアップロードするとAI読み取りが使えます。'
                : extracted
                  ? '読み取り済み。資料を追加した場合は再度読み取りできます。'
                  : '資料から案件の基本情報を自動入力できます。'}
            </span>
            <button
              className="btn-primary !py-1.5 !text-[12px]"
              disabled={uploadedCount === 0 || !!uploading}
              onClick={extractInfo}
            >
              <Icon name="neurology" className="text-[16px]" />
              {extracted ? '案件情報を再読み取り' : 'アップロード資料から案件情報を読み取る'}
            </button>
          </div>
        </section>

        {/* ---- STEP2 案件基本情報 ---- */}
        <section className="card mt-5">
          <div className="flex items-center justify-between border-b border-surface-container-high px-5 py-3">
            <span className="flex items-center gap-2 text-[14px] font-bold">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary-container text-[11px] font-bold text-white">2</span>
              案件基本情報を確認・修正
            </span>
            {extracted && (
              <span className="badge-base badge-neutral">
                <Icon name="smart_toy" className="text-[12px]" /> AIが資料から読み取った値（編集可）
              </span>
            )}
          </div>
          {extracted && extractNote && (
            <div className="mx-5 mt-3 rounded bg-surface-container-low/70 px-3 py-2 text-[11px] text-on-surface-variant">
              {extractNote}
            </div>
          )}
          <div className="grid grid-cols-3 gap-4 p-5">
            <Field label="案件名" required className="col-span-2" hint={sources.name && `出典：${sources.name}`}>
              <input className="input-base" value={form.name} onChange={set('name')}
                placeholder="例：オートスタッフ中部 LBOファイナンス" />
            </Field>
            <Field label="担当者" hint="行内情報">
              <select className="input-base" value={form.owner || userKey} onChange={set('owner')}>
                {users.map((u) => <option key={u.key} value={u.key}>{u.display}</option>)}
              </select>
            </Field>
            <Field label="案件種別" required hint={sources.deal_type && `出典：${sources.deal_type}`}>
              <select className="input-base" value={form.deal_type} onChange={set('deal_type')}>
                {['LBO', 'MBO', '事業承継', 'リファイナンス'].map((t) => <option key={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="借入人（SPC）" required hint={sources.borrower && `出典：${sources.borrower}`}>
              <input className="input-base" value={form.borrower} onChange={set('borrower')} />
            </Field>
            <Field label="対象会社" required hint={sources.target && `出典：${sources.target}`}>
              <input className="input-base" value={form.target} onChange={set('target')} />
            </Field>
            <Field label="対象会社の業種" hint={sources.industry && `出典：${sources.industry}`}>
              <input className="input-base" value={form.industry} onChange={set('industry')} />
            </Field>
            <Field label="スポンサー" hint={sources.sponsor && `出典：${sources.sponsor}`}>
              <input className="input-base" value={form.sponsor} onChange={set('sponsor')} />
            </Field>
            <Field label="クローズ予定日" hint={sources.close_date && `出典：${sources.close_date}`}>
              <input type="date" className="input-base" value={form.close_date} onChange={set('close_date')} />
            </Field>
            <Field label="審査相談予定日" hint="行内情報">
              <input type="date" className="input-base" value={form.next_meeting_date} onChange={set('next_meeting_date')} />
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
              <Field label="買収総額（EV）" hint={sources.ev_mm && `出典：${sources.ev_mm}`}>
                <input type="number" className="input-base font-data-tabular" value={form.ev_mm} onChange={set('ev_mm')} />
              </Field>
              <Field label="シニアローン総額" hint={sources.senior_mm && `出典：${sources.senior_mm}`}>
                <input type="number" className="input-base font-data-tabular" value={form.senior_mm} onChange={set('senior_mm')} />
              </Field>
              <Field label="うち本行取組額" hint="行内情報・要入力">
                <input type="number" className="input-base font-data-tabular !border-primary-container/40 !bg-primary-fixed/20" value={form.our_commitment_mm} onChange={set('our_commitment_mm')} placeholder="2,500" />
              </Field>
              <Field label="エクイティ" hint={sources.equity_mm && `出典：${sources.equity_mm}`}>
                <input type="number" className="input-base font-data-tabular" value={form.equity_mm} onChange={set('equity_mm')} />
              </Field>
              <Field label="提示EBITDA（速報）" hint={sources.sponsor_ebitda_mm && `出典：${sources.sponsor_ebitda_mm}`}>
                <input type="number" className="input-base font-data-tabular" value={form.sponsor_ebitda_mm} onChange={set('sponsor_ebitda_mm')} />
              </Field>
            </div>
          </div>

          <div className="px-5 pb-5">
            <Field label="案件概要" hint={sources.summary && `出典：${sources.summary}`}>
              <textarea className="input-base h-20" value={form.summary} onChange={set('summary')}
                placeholder="案件の背景・ストラクチャーの概要" />
            </Field>
          </div>
        </section>

        {error && (
          <div className="mt-4 flex items-center gap-2 rounded border border-error/30 bg-error-container/40 px-4 py-2.5 text-[13px] text-on-error-container">
            <Icon name="error" className="text-[18px]" /> {error}
          </div>
        )}

        <div className="mt-5 flex items-center justify-end gap-3 pb-10">
          <button className="btn-secondary" onClick={cancelDraft}>キャンセル（下書きを破棄）</button>
          <span className="text-[12px] text-outline">
            {!requiredUploaded ? '必須資料をアップロードしてください。'
              : !canRegister ? '案件名・借入人・対象会社を入力してください。'
                : '登録の確定と同時に資料のAI解析を実行します。'}
          </span>
          <button className="btn-primary" disabled={!canRegister || analyzing} onClick={registerAndAnalyze}>
            <Icon name="check" className="text-[18px]" /> この内容で登録し、AI解析を実行
          </button>
        </div>
      </div>
    </Layout>
  )
}
