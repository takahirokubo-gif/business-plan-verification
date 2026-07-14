const REVIEW_STATUS_CLASS: Record<string, string> = {
  検討中: 'badge-info',
  再検討中: 'badge-warning',
  推進: 'badge-success',
  保留: 'badge-neutral',
  見送り: 'badge-neutral',
}

export function ReviewStatusBadge({ status }: { status: string }) {
  return <span className={`badge-base ${REVIEW_STATUS_CLASS[status] ?? 'badge-neutral'}`}>{status}</span>
}

export function WorkStatusBadge({ status }: { status: string }) {
  return <span className="badge-base badge-neutral">{status}</span>
}

const ORIGIN_LABEL: Record<string, string> = {
  model: 'モデル数式',
  dd: 'DD由来',
  manual: '手動追加',
}

/** 出典バッジ。色情報は警告系に限定する方針のため、グレー系で統一。 */
export function OriginBadge({ origin }: { origin: string }) {
  return (
    <span className="badge-base badge-neutral">
      出典 {ORIGIN_LABEL[origin] ?? origin}
    </span>
  )
}

export function Badge({ kind, children }: { kind: 'success' | 'warning' | 'error' | 'neutral' | 'info' | 'ai'; children: React.ReactNode }) {
  return <span className={`badge-base badge-${kind}`}>{children}</span>
}
