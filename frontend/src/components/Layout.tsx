import { useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { Icon } from './Icon'
import { ModeToggle } from './ModeToggle'
import { useUser } from '../context/UserContext'

function SidebarLink({ to, icon, label, end = false, collapsed = false }: {
  to: string; icon: string; label: string; end?: boolean; collapsed?: boolean
}) {
  return (
    <NavLink
      to={to}
      end={end}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        `relative flex items-center gap-3 py-2.5 text-[13px] transition-colors ${
          collapsed ? 'justify-center px-0' : 'px-5'
        } ${
          isActive
            ? 'bg-primary-fixed/60 font-bold text-primary-container'
            : 'text-on-surface-variant hover:bg-surface-container-low'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && <span className="absolute left-0 top-0 h-full w-1 bg-primary-container" />}
          <Icon name={icon} className="text-[20px]" fill={isActive} />
          {!collapsed && label}
        </>
      )}
    </NavLink>
  )
}

function UserSwitcher() {
  const { users, current, setCurrent } = useUser()
  const [open, setOpen] = useState(false)
  if (!current) return null
  return (
    <div className="relative">
      <button
        className="flex items-center gap-2 rounded px-2 py-1 text-[13px] hover:bg-surface-container-low"
        onClick={() => setOpen(!open)}
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-container text-[12px] font-bold text-white">
          {current.name[0]}
        </span>
        <span className="font-medium">{current.name}</span>
        <span className="text-outline">{current.role}</span>
        <Icon name="expand_more" className="text-[18px] text-outline" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="card absolute right-0 z-20 mt-1 w-56 py-1">
            <div className="px-3 py-1.5 text-[11px] text-outline">操作ユーザーを切替</div>
            {users.map((u) => (
              <button
                key={u.key}
                className={`flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] hover:bg-surface-container-low ${
                  u.key === current.key ? 'font-bold text-primary-container' : ''
                }`}
                onClick={() => { setCurrent(u); setOpen(false) }}
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-surface-container text-[11px] font-bold">
                  {u.name[0]}
                </span>
                {u.display}
                {u.key === current.key && <Icon name="check" className="ml-auto text-[16px]" />}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

/** 設定モーダル：抽出エンジン（モック / AI）の切替。 */
function SettingsModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="card relative w-[min(640px,95vw)] shadow-xl">
        <div className="flex items-center justify-between border-b border-surface-container-high px-5 py-3">
          <span className="flex items-center gap-2 text-[15px] font-bold">
            <Icon name="settings" className="text-[20px] text-primary-container" />
            設定
          </span>
          <button
            className="rounded-full p-1.5 text-on-surface-variant hover:bg-surface-container-low"
            onClick={onClose}
          >
            <Icon name="close" className="text-[20px]" />
          </button>
        </div>
        <div className="p-5">
          <div className="text-[13px] font-bold">解析エンジン</div>
          <p className="mb-3 mt-0.5 text-[12px] text-on-surface-variant">
            資料の解析（案件情報読取・抽出・KPI提案・シナリオ生成）に使うエンジンをボタンで切り替えます。
          </p>
          <ModeToggle />
          <p className="mt-4 border-t border-surface-container-high pt-3 text-[11px] text-on-surface-variant">
            どちらのエンジンでも、AIの役割は「資料のどこに何が書いてあるか」の特定と定性推定のみです。
            数値の再計算・判定はシステム側では行いません。
          </p>
        </div>
      </div>
    </div>
  )
}

const SIDEBAR_KEY = 'bpv.sidebarCollapsed'

export function Layout({ children, breadcrumb }: {
  children: React.ReactNode
  breadcrumb?: React.ReactNode
}) {
  const [settingsOpen, setSettingsOpen] = useState(false)
  // サイドバーの開閉はページ遷移・再読込をまたいで保持する
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(SIDEBAR_KEY) === '1',
  )
  const toggleSidebar = () => {
    setCollapsed((prev) => {
      localStorage.setItem(SIDEBAR_KEY, prev ? '0' : '1')
      return !prev
    })
  }
  return (
    <div className="flex min-h-screen">
      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
      {/* 固定サイドバー（折りたたみ可） */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex flex-col border-r border-surface-container-high bg-white transition-[width] duration-200 ${
          collapsed ? 'w-14' : 'w-sidebar-width'
        }`}
      >
        <div className={`flex items-center border-b border-surface-container-high py-4 ${
          collapsed ? 'justify-center px-0' : 'gap-2.5 px-5'
        }`}>
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-primary-container text-white">
            <Icon name="account_balance" className="text-[22px]" />
          </span>
          {!collapsed && (
            <div>
              <div className="text-[15px] font-bold leading-tight text-primary-container">融資管理システム</div>
              <div className="text-[11px] text-outline">事業計画検証</div>
            </div>
          )}
        </div>
        <nav className="flex-1 py-3">
          <SidebarLink to="/" icon="list_alt" label="案件一覧" end collapsed={collapsed} />
          <SidebarLink to="/deals/new" icon="post_add" label="新規案件登録" collapsed={collapsed} />
        </nav>
        <div className="border-t border-surface-container-high py-3">
          <button
            className={`flex w-full items-center gap-3 py-2.5 text-[13px] text-on-surface-variant hover:bg-surface-container-low ${
              collapsed ? 'justify-center px-0' : 'px-5'
            }`}
            onClick={() => setSettingsOpen(true)}
            title={collapsed ? '設定' : undefined}
          >
            <Icon name="settings" className="text-[20px]" /> {!collapsed && '設定'}
          </button>
          <button
            className={`flex w-full items-center gap-3 py-2.5 text-[13px] text-on-surface-variant hover:bg-surface-container-low ${
              collapsed ? 'justify-center px-0' : 'px-5'
            }`}
            onClick={toggleSidebar}
            title={collapsed ? 'サイドバーを開く' : 'サイドバーをしまう'}
          >
            <Icon name={collapsed ? 'chevron_right' : 'chevron_left'} className="text-[20px]" />
            {!collapsed && 'サイドバーをしまう'}
          </button>
        </div>
      </aside>

      {/* メイン */}
      <div className={`flex-1 transition-[margin] duration-200 ${collapsed ? 'ml-14' : 'ml-sidebar-width'}`}>
        <header className="sticky top-0 z-20 flex h-12 items-center justify-between border-b border-surface-container-high bg-white px-6">
          <div className="flex items-center gap-2 text-[12px] text-on-surface-variant">
            <button
              className="-ml-2 rounded p-1 text-outline hover:bg-surface-container-low hover:text-on-surface"
              onClick={toggleSidebar}
              title={collapsed ? 'サイドバーを開く' : 'サイドバーをしまう'}
            >
              <Icon name="menu" className="text-[18px]" />
            </button>
            <Link to="/" className="font-medium text-primary-container hover:underline">案件一覧</Link>
            <span className="text-outline-variant">/</span>
            <span>事業計画検証</span>
            {breadcrumb}
          </div>
          <div className="flex items-center gap-3">
            <Icon name="notifications" className="text-[20px] text-outline" />
            <UserSwitcher />
          </div>
        </header>
        <main className="p-6">{children}</main>
      </div>
    </div>
  )
}
