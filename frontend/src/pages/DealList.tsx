import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Layout } from '../components/Layout'
import { Icon } from '../components/Icon'
import { ReviewStatusBadge, WorkStatusBadge } from '../components/Badge'
import type { DealListItem } from '../types'

const REVIEW_TABS = ['すべて', '検討中', '再検討中', '推進', '保留', '見送り']
const WORK_FILTER = ['すべて', '資料解析中', '数値確定中', 'KPI確定中', 'シナリオ検討中', '出力済']

function fmtDate(iso: string | null): string {
  if (!iso) return '－'
  const d = new Date(iso)
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`
}

const OWNER_NAMES: Record<string, string> = { tanaka: '田中', sato: '佐藤', takahashi: '高橋' }

export function DealList() {
  const [deals, setDeals] = useState<DealListItem[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [tab, setTab] = useState('すべて')
  const [workFilter, setWorkFilter] = useState('すべて')
  const navigate = useNavigate()

  useEffect(() => {
    api.deals().then((d) => { setDeals(d.deals); setCounts(d.counts) })
  }, [])

  const filtered = deals.filter((d) =>
    (tab === 'すべて' || d.review_status === tab)
    && (workFilter === 'すべて' || d.work_status === workFilter))

  return (
    <Layout>
      <div className="mx-auto max-w-[1200px]">
        <div className="flex items-center justify-between">
          <h1 className="text-[24px] font-bold">案件一覧</h1>
          <button className="btn-primary" onClick={() => navigate('/deals/new')}>
            <Icon name="add" className="text-[18px]" /> 新規案件を登録
          </button>
        </div>

        <div className="mt-4 flex items-end justify-between border-b border-surface-container-high">
          <div className="flex gap-1">
            {REVIEW_TABS.map((t) => {
              const count = t === 'すべて' ? deals.length : (counts[t] ?? 0)
              return (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`border-b-2 px-3 pb-2 text-[13px] transition-colors ${
                    tab === t
                      ? 'border-primary-container font-bold text-primary-container'
                      : 'border-transparent text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  {t}（{count}）
                </button>
              )
            })}
          </div>
          <label className="mb-1.5 flex items-center gap-2 text-[12px] text-on-surface-variant">
            作業ステータス：
            <select
              className="input-base !w-40 !py-1"
              value={workFilter}
              onChange={(e) => setWorkFilter(e.target.value)}
            >
              {WORK_FILTER.map((w) => <option key={w}>{w}</option>)}
            </select>
          </label>
        </div>

        <div className="card mt-4 overflow-hidden">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-surface-container-high bg-surface-container-low text-left text-[11px] tracking-wide text-on-surface-variant">
                <th className="px-4 py-2.5 font-medium">案件名</th>
                <th className="px-4 py-2.5 font-medium">借入人（SPC）／対象会社</th>
                <th className="px-4 py-2.5 text-right font-medium">本行取組額</th>
                <th className="px-4 py-2.5 font-medium">検討ステータス</th>
                <th className="px-4 py-2.5 font-medium">作業ステータス</th>
                <th className="px-4 py-2.5 font-medium">担当者</th>
                <th className="px-4 py-2.5 font-medium">次回審査相談日</th>
                <th className="px-4 py-2.5 font-medium">最終更新日</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => (
                <tr key={d.id} className="border-b border-surface-container-low last:border-0 hover:bg-surface-container-low/50">
                  <td className="px-4 py-3">
                    <Link to={`/deals/${d.id}`} className="font-bold text-primary-container hover:underline">
                      {d.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <div>{d.borrower}</div>
                    {d.target !== d.borrower && (
                      <div className="text-[12px] text-outline">{d.target}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-data-tabular font-medium">
                      {d.our_commitment_mm != null ? `${(d.our_commitment_mm / 100).toLocaleString()}億円` : '－'}
                    </span>
                  </td>
                  <td className="px-4 py-3"><ReviewStatusBadge status={d.review_status} /></td>
                  <td className="px-4 py-3"><WorkStatusBadge status={d.work_status} /></td>
                  <td className="px-4 py-3">{OWNER_NAMES[d.owner ?? ''] ?? d.owner ?? '－'}</td>
                  <td className="px-4 py-3 font-data-tabular">{d.next_meeting_date?.replaceAll('-', '/') ?? '－'}</td>
                  <td className="px-4 py-3 font-data-tabular text-on-surface-variant">{fmtDate(d.updated_at)}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-outline">
                    該当する案件がありません
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  )
}
