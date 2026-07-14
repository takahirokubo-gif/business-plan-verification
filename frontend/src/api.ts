import type {
  ChatResult, DealFull, DealListItem, ExportPreview, User,
} from './types'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: options?.body instanceof FormData
      ? undefined
      : { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch { /* noop */ }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  users: () => request<User[]>('/api/users'),

  deals: () => request<{ deals: DealListItem[]; counts: Record<string, number>; total: number }>('/api/deals'),

  createDeal: (body: Record<string, unknown>) =>
    request<{ id: number }>('/api/deals', { method: 'POST', body: JSON.stringify(body) }),

  dealFull: (id: number) => request<DealFull>(`/api/deals/${id}/full`),

  uploadDocument: (dealId: number, slot: string, file: File, user: string) => {
    const fd = new FormData()
    fd.append('slot', slot)
    fd.append('user', user)
    fd.append('file', file)
    return request<{ id: number; company_match: boolean; identified_company: string | null; identified_label: string | null }>(
      `/api/deals/${dealId}/documents`, { method: 'POST', body: fd })
  },

  analyze: (dealId: number, user: string) =>
    request<{ items: number }>(`/api/deals/${dealId}/analyze?user=${encodeURIComponent(user)}`, { method: 'POST' }),

  itemAction: (dealId: number, itemId: number, body: Record<string, unknown>) =>
    request<{ item: unknown; deal: unknown }>(`/api/deals/${dealId}/items/${itemId}/action`, {
      method: 'POST', body: JSON.stringify(body),
    }),

  kpiConfirm: (dealId: number, user: string) =>
    request(`/api/deals/${dealId}/kpi/confirm`, { method: 'POST', body: JSON.stringify({ user }) }),

  kpiClearStale: (dealId: number, user: string) =>
    request(`/api/deals/${dealId}/kpi/clear-stale`, { method: 'POST', body: JSON.stringify({ user }) }),

  kpiApply: (dealId: number, diff: unknown, user: string) =>
    request(`/api/deals/${dealId}/kpi/apply`, { method: 'POST', body: JSON.stringify({ diff, user }) }),

  chat: (dealId: number, context: 'kpi' | 'scenario', message: string, user: string, target?: string) =>
    request<ChatResult>(`/api/deals/${dealId}/chat`, {
      method: 'POST', body: JSON.stringify({ context, message, user, target: target ?? null }),
    }),

  createDraft: (user: string) =>
    request<{ id: number }>('/api/deals/draft', { method: 'POST', body: JSON.stringify({ user }) }),

  updateDeal: (dealId: number, body: Record<string, unknown>) =>
    request<{ id: number }>(`/api/deals/${dealId}`, { method: 'PATCH', body: JSON.stringify(body) }),

  deleteDeal: (dealId: number) =>
    request<{ deleted: number }>(`/api/deals/${dealId}`, { method: 'DELETE' }),

  extractDealInfo: (dealId: number, user: string) =>
    request<{ fields: Record<string, unknown>; sources: Record<string, string>; note: string }>(
      `/api/deals/${dealId}/extract-info?user=${encodeURIComponent(user)}`, { method: 'POST' }),

  scenarioAdopt: (dealId: number, key: string, adopted: boolean, user: string, rejectionNote?: string) =>
    request(`/api/deals/${dealId}/scenarios/${key}/adopt`, {
      method: 'POST',
      body: JSON.stringify({ adopted, user, rejection_note: rejectionNote ?? null }),
    }),

  scenarioClearStale: (dealId: number, key: string, user: string) =>
    request(`/api/deals/${dealId}/scenarios/${key}/clear-stale`, {
      method: 'POST', body: JSON.stringify({ user }),
    }),

  scenariosApply: (dealId: number, diff: unknown, user: string) =>
    request(`/api/deals/${dealId}/scenarios/apply`, {
      method: 'POST', body: JSON.stringify({ diff, user }),
    }),

  exportPreview: (dealId: number) => request<ExportPreview>(`/api/deals/${dealId}/export/preview`),

  exportExcel: (dealId: number, user: string) => downloadExport(`/api/deals/${dealId}/export`, user),

  exportPdf: (dealId: number, user: string) => downloadExport(`/api/deals/${dealId}/export/pdf`, user),

  createMemo: (dealId: number, body: Record<string, unknown>) =>
    request<{ memo: unknown; status_changed: unknown }>(`/api/deals/${dealId}/memos`, {
      method: 'POST', body: JSON.stringify(body),
    }),
}

async function downloadExport(url: string, user: string): Promise<string> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `HTTP ${res.status}`)
  }
  const blob = await res.blob()
  const disposition = res.headers.get('content-disposition') ?? ''
  const m = disposition.match(/filename\*=UTF-8''(.+)$/)
  const filename = m ? decodeURIComponent(m[1]) : 'export'
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = filename
  a.click()
  URL.revokeObjectURL(objectUrl)
  return filename
}
