import { useEffect, useState } from 'react'
import { api } from '../../api'
import { Icon } from '../../components/Icon'
import { Badge } from '../../components/Badge'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { useUser } from '../../context/UserContext'
import type { DealFull, ExportPreview } from '../../types'

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-surface-container-high bg-surface-container-low/50 px-3 py-2 text-center">
      <div className="text-[10px] tracking-wide text-outline">{label}</div>
      <div className="font-data-tabular text-[17px] font-bold text-primary-container">{value}</div>
    </div>
  )
}

export function ExportTab({ full, refresh, dealId }: {
  full: DealFull
  refresh: () => Promise<void>
  dealId: number
}) {
  const { userKey } = useUser()
  const [preview, setPreview] = useState<ExportPreview | null>(null)
  const [confirmHeld, setConfirmHeld] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState('')
  const deal = full.deal
  const confirmedItem = (key: string) => full.items.find((i) => i.key === key && i.status === 'confirmed')

  useEffect(() => {
    api.exportPreview(dealId).then(setPreview)
  }, [dealId, full])

  const [format, setFormat] = useState<'xlsx' | 'pdf'>('xlsx')

  const doExport = async (fmt: 'xlsx' | 'pdf' = format) => {
    setDownloading(true)
    setError('')
    try {
      if (fmt === 'pdf') await api.exportPdf(dealId, userKey)
      else await api.exportExcel(dealId, userKey)
      await refresh()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setDownloading(false)
    }
  }

  const onExportClick = (fmt: 'xlsx' | 'pdf') => {
    setFormat(fmt)
    if (preview && preview.held_items.length > 0) setConfirmHeld(true)
    else doExport(fmt)
  }

  const starred = full.kpi_nodes.filter((n) => n.star)
  const adopted = full.scenarios.filter((s) => s.adopted)
  const finRows: { label: string; keys: [string, string] }[] = [
    { label: '売上高', keys: ['act_revenue', 'base_revenue'] },
    { label: 'EBITDA', keys: ['act_ebitda', 'base_ebitda'] },
    { label: 'FCF', keys: ['act_fcf', 'base_fcf'] },
  ]
  const previewYears = ['FY26', 'FY27', 'FY28', 'FY29']

  return (
    <div className="grid grid-cols-[1fr_320px] gap-4">
      {/* ---- 資料プレビュー ---- */}
      <div className="card p-6">
        <div className="border-b-2 border-primary-container pb-3">
          <div className="text-[11px] tracking-widest text-outline">審査相談資料（確定データのみ）</div>
          <div className="mt-1 text-[18px] font-bold">{deal.name}</div>
          <div className="mt-1 text-[11px] text-outline">
            作成日 {new Date().toLocaleDateString('ja-JP')}／{userKey === 'tanaka' ? '田中' : userKey === 'sato' ? '佐藤' : '高橋'}
          </div>
        </div>

        <div className="mt-4">
          <div className="text-[12px] font-bold text-primary-container">01｜案件概要</div>
          <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-[12px]">
            <div><span className="text-outline">案件スキーム：</span>{deal.deal_type}</div>
            <div><span className="text-outline">スポンサー：</span>{deal.sponsor ?? '－'}</div>
            <div><span className="text-outline">対象会社：</span>{deal.target}</div>
            <div><span className="text-outline">業種：</span>{deal.industry ?? '－'}</div>
          </div>
          <div className="mt-3 grid grid-cols-4 gap-3">
            <Stat label="EV" value={deal.ev_mm != null ? `${(deal.ev_mm / 100).toLocaleString()}億円` : '－'} />
            <Stat label="Senior（本行）" value={deal.senior_mm != null ? `${(deal.senior_mm / 100).toLocaleString()}億(${((deal.our_commitment_mm ?? 0) / 100).toLocaleString()}億)` : '－'} />
            <Stat label="Leverage" value={deal.initial_leverage != null ? `${deal.initial_leverage}x` : '－'} />
            <Stat label="LTV" value={deal.ltv_pct != null ? `${deal.ltv_pct}%` : '－'} />
          </div>
          {deal.summary && <p className="mt-3 text-[12px] leading-relaxed text-on-surface-variant">{deal.summary}</p>}
        </div>

        <div className="mt-5">
          <div className="text-[12px] font-bold text-primary-container">02｜確定財務ハイライト（百万円）</div>
          <table className="mt-2 w-full text-[12px]">
            <thead>
              <tr className="border-b border-surface-container-high text-[11px] text-outline">
                <th className="py-1.5 text-left font-medium">項目</th>
                {previewYears.map((y) => <th key={y} className="py-1.5 text-right font-medium">{y}{y === 'FY26' ? '実' : ' B'}</th>)}
              </tr>
            </thead>
            <tbody>
              {finRows.map(({ label, keys }) => {
                const act = confirmedItem(keys[0])
                const plan = confirmedItem(keys[1])
                return (
                  <tr key={label} className="border-b border-surface-container-low">
                    <td className="py-1.5 font-medium">{label}</td>
                    {previewYears.map((y) => {
                      const src = y === 'FY26' ? act : plan
                      const v = src?.effective_values?.[y]
                      return (
                        <td key={y} className="font-data-tabular py-1.5 text-right">
                          {v != null ? v.toLocaleString() : <span className="text-outline-variant">保留</span>}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-5">
          <div className="text-[12px] font-bold text-primary-container">03｜重要KPI（★）</div>
          <div className="mt-2 grid grid-cols-3 gap-3">
            {starred.map((n) => (
              <div key={n.node_id} className="rounded border border-surface-container-high px-3 py-2">
                <div className="flex items-center gap-1 text-[11px] text-outline">
                  <Icon name="star" className="text-[12px] text-amber-500" fill />{n.label}
                </div>
                <div className="font-data-tabular text-[14px] font-bold">{n.value_text}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-5">
          <div className="flex items-center gap-2 text-[12px] font-bold text-primary-container">
            04｜ストレスシナリオ（採用{adopted.length}件）
            <Badge kind="neutral">AI推定・モデル再計算なし</Badge>
          </div>
          <div className="mt-2 space-y-2">
            {adopted.map((s) => (
              <div key={s.key} className="rounded border border-surface-container-high px-3 py-2 text-[12px]">
                <div className="font-bold">S{s.key}：{s.title}</div>
                <div className="mt-0.5 text-on-surface-variant">{s.change_text}</div>
                <div className="mt-0.5 text-[11.5px] text-on-surface-variant">{s.impact}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-5">
          <div className="text-[12px] font-bold text-primary-container">05｜前提・定性情報（確定済み）</div>
          <div className="mt-2 space-y-1.5">
            {full.items.filter((i) => i.status === 'confirmed' && i.unit === 'テキスト').map((i) => (
              <div key={i.key} className="text-[12px]">
                <span className="font-medium">{i.label}：</span>
                <span className="text-on-surface-variant">{i.effective_text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-5">
          <div className="text-[12px] font-bold text-primary-container">
            06｜審査相談の記録（{full.memos.length}件）
          </div>
          <div className="mt-2 space-y-1 text-[12px] text-on-surface-variant">
            {full.memos.map((m) => (
              <div key={m.id}>
                {m.meeting_date.replaceAll('-', '/')}　結論：{m.conclusion}
                {m.findings.length > 0 && `（指摘${m.findings.length}件）`}
              </div>
            ))}
          </div>
          <div className="mt-3 text-[10px] text-outline">
            ※ 出力ファイルには、各数値の出典（参照ファイル・箇所）、KPI構造の参照元、
            不採用シナリオ（参考）、審査相談メモの全文が収録されます。
          </div>
        </div>
      </div>

      {/* ---- 出力設定 ---- */}
      <div className="space-y-3">
        {preview && preview.held_items.length > 0 && (
          <div className="rounded border border-amber-300 bg-amber-50 p-3 text-[12px]">
            <div className="flex items-center gap-1.5 font-bold text-amber-800">
              <Icon name="warning" className="text-[16px]" /> 保留が{preview.held_items.length}項目あります
            </div>
            <p className="mt-1 text-amber-900">保留項目を除いて出力されます。</p>
            <ul className="mt-1.5 list-inside list-disc text-amber-900">
              {preview.held_items.map((h) => <li key={h.key}>{h.label}</li>)}
            </ul>
          </div>
        )}
        {preview?.stale_warnings && (
          <div className="rounded border border-amber-300 bg-amber-50 p-3 text-[12px] text-amber-900">
            <Icon name="warning" className="mr-1 align-middle text-[15px]" />
            上流変更の警告が残っています。内容を再確認してから出力することを推奨します。
          </div>
        )}

        <div className="card p-4">
          <div className="text-[13px] font-bold">出力するコンテンツ</div>
          <div className="mt-2 space-y-1.5 text-[12px]">
            {['案件基礎情報', '確定財務数値', '確定KPI構造', '採用シナリオ（AI推定注記付き）'].map((c) => (
              <label key={c} className="flex items-center gap-2">
                <input type="checkbox" checked readOnly /> {c}
              </label>
            ))}
          </div>
          <button
            className="btn-primary mt-4 w-full justify-center"
            disabled={!preview?.can_export || downloading}
            onClick={() => onExportClick('xlsx')}
          >
            <Icon name="download" className="text-[18px]" />
            {downloading ? '生成中…' : 'Excelをダウンロード（.xlsx）'}
          </button>
          <button
            className="btn-secondary mt-2 w-full justify-center"
            disabled={!preview?.can_export || downloading}
            onClick={() => onExportClick('pdf')}
          >
            <Icon name="picture_as_pdf" className="text-[18px]" /> PDFをダウンロード（補助）
          </button>
          {!preview?.can_export && (
            <div className="mt-2 text-[11px] text-error">
              {!preview?.required_confirmed && '必須項目の確定が完了していません。'}
              {preview && !preview.kpi_confirmed && 'KPI構造が確定されていません。'}
            </div>
          )}
          {error && <div className="mt-2 text-[11px] text-error">{error}</div>}
          <div className="mt-2 text-[10px] leading-relaxed text-outline">
            ※ 行内標準フォーマットに準拠したテンプレートへ確定値のみを転記します。
            AIによる推定値には注記が付きます。
          </div>
        </div>

        <div className="card p-4">
          <div className="text-[13px] font-bold">出力履歴</div>
          <div className="mt-2 space-y-2">
            {full.exports.slice().reverse().map((e) => (
              <div key={e.id} className="flex items-start gap-2 border-b border-surface-container-low pb-2 text-[11px] last:border-0">
                <Icon name="table_chart" className="mt-0.5 text-[16px] text-green-700" />
                <div className="min-w-0">
                  <div className="truncate font-medium">{e.filename}</div>
                  <div className="text-outline">
                    {e.at ? new Date(e.at).toLocaleString('ja-JP') : ''}
                    {e.excluded_held > 0 && `・保留${e.excluded_held}件除外`}
                  </div>
                </div>
              </div>
            ))}
            {full.exports.length === 0 && <div className="text-[11px] text-outline">まだ出力されていません</div>}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmHeld}
        title={`保留${preview?.held_items.length ?? 0}項目を除いて出力します`}
        confirmLabel="出力する"
        onConfirm={() => { setConfirmHeld(false); doExport(format) }}
        onCancel={() => setConfirmHeld(false)}
      >
        保留中の項目（{preview?.held_items.map((h) => h.label).join('、')}）は出力に含まれません。
        よろしいですか？
      </ConfirmDialog>
    </div>
  )
}
