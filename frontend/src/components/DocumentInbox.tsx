import { useEffect, useRef, useState } from 'react'
import { Icon } from './Icon'

export interface InboxSlot { key: string; label: string; required: boolean; accept: string }

interface StagedItem {
  id: string
  file: File
  slot: string | null
  suggested: boolean
  status: 'pending' | 'uploading' | 'error'
  error?: string
}

/** ファイル名・拡張子からスロット（資料種別）を推定する（決定的・LLM不使用） */
function suggestSlot(name: string): string | null {
  const lower = name.toLowerCase()
  if (/\.xlsx?$/.test(lower)) {
    if (lower.includes('sponsor') || name.includes('スポンサー')) return 'model_sponsor'
    if (lower.includes('base') || name.includes('ベース')) return 'model_base'
    return null
  }
  if (lower.endsWith('.pdf')) {
    if (lower.includes('business') || name.includes('事業')) return 'dd_business'
    if (lower.includes('financial') || name.includes('財務')) return 'dd_financial'
    if (lower.includes('legal') || name.includes('法務')) return 'dd_legal'
    if (lower.includes('tax') || name.includes('税務')) return 'dd_tax'
  }
  return null
}

function fileIcon(name: string): string {
  const lower = name.toLowerCase()
  if (/\.xlsx?$/.test(lower)) return 'table_view'
  if (lower.endsWith('.pdf')) return 'picture_as_pdf'
  return 'description'
}

let seq = 0

/** 資料インボックス：複数ファイルをドラッグ＆ドロップでまとめて入れ、
 *  種別（スロット）をタグ付けした順に自動でアップロード＆AI識別する。
 *  タグはファイル名から自動推定し、判定できないものだけ後から人間が選ぶ。 */
export function DocumentInbox({ slots, onUpload }: {
  slots: InboxSlot[]
  onUpload: (slot: string, file: File) => Promise<void>
}) {
  const [items, setItems] = useState<StagedItem[]>([])
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const busyRef = useRef(false)

  const addFiles = (files: FileList | File[] | null) => {
    if (!files) return
    const list = Array.from(files).filter((f) => /\.(xlsx?|pdf)$/i.test(f.name))
    setItems((prev) => [
      ...prev,
      ...list.map((file) => {
        const slot = suggestSlot(file.name)
        return { id: `doc-${++seq}`, file, slot, suggested: slot !== null, status: 'pending' as const }
      }),
    ])
  }

  // タグ（スロット）が決まった資料から順に、1件ずつアップロード＆AI識別する
  useEffect(() => {
    if (busyRef.current) return
    const next = items.find((it) => it.status === 'pending' && it.slot)
    if (!next) return
    busyRef.current = true
    setItems((prev) => prev.map((it) => (it.id === next.id ? { ...it, status: 'uploading' } : it)))
    onUpload(next.slot!, next.file)
      .then(() => {
        setItems((prev) => prev.filter((it) => it.id !== next.id))
      })
      .catch((e) => {
        setItems((prev) =>
          prev.map((it) =>
            it.id === next.id ? { ...it, status: 'error', error: (e as Error).message } : it,
          ),
        )
      })
      .finally(() => {
        busyRef.current = false
        // 次の待機アイテムを拾うために再レンダリングを促す
        setItems((prev) => [...prev])
      })
  }, [items, onUpload])

  const setSlot = (id: string, slot: string) => {
    setItems((prev) =>
      prev.map((it) =>
        it.id === id ? { ...it, slot, suggested: false, status: 'pending', error: undefined } : it,
      ),
    )
  }

  const remove = (id: string) => setItems((prev) => prev.filter((it) => it.id !== id))

  const untagged = items.filter((it) => !it.slot).length

  return (
    <div
      className="flex flex-col gap-3"
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files) }}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".xlsx,.xls,.pdf"
        className="hidden"
        onChange={(e) => { addFiles(e.target.files); e.target.value = '' }}
      />

      {/* まとめてインプットするドロップゾーン */}
      <div
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded border-2 border-dashed transition-colors ${
          items.length === 0 ? 'p-8' : 'p-3'
        } ${dragging ? 'border-primary-container bg-primary-fixed/40' : 'border-outline-variant bg-surface-container-low/50 hover:bg-surface-container-low'}`}
      >
        {items.length === 0 ? (
          <>
            <Icon name="cloud_upload" className="mb-2 text-[40px] text-primary-container" fill />
            <div className="text-[14px] font-bold">資料をまとめてアップロード</div>
            <div className="mt-1 text-center text-[12px] text-on-surface-variant">
              ドラッグ＆ドロップ、またはクリックして選択（複数可）。
              <br />
              種類はファイル名から自動判定し、判定できないものだけ後からタグ付けできます。
            </div>
            <div className="mt-2 flex gap-1.5">
              {['Excel (.xlsx)', 'PDF'].map((t) => (
                <span key={t} className="badge-base badge-neutral !text-[10px]">{t}</span>
              ))}
            </div>
          </>
        ) : (
          <div className="flex items-center gap-2 text-[12px] text-on-surface-variant">
            <Icon name="add" className="text-[18px]" />
            資料を追加（ドラッグ＆ドロップ可・複数可）
          </div>
        )}
      </div>

      {/* タグ付け待ち・処理中の資料一覧 */}
      {items.length > 0 && (
        <div className="overflow-hidden rounded border border-surface-container-high">
          <div className="flex items-center justify-between border-b border-surface-container-high bg-surface-container-low/60 px-3 py-2">
            <span className="flex items-center gap-1.5 text-[12px] font-bold">
              <Icon name="inbox" className="text-[16px] text-primary-container" />
              インプット済みの資料（{items.length}件）
            </span>
            {untagged > 0 && (
              <span className="text-[11px] font-bold text-[#b45309]">タグ未設定が{untagged}件あります</span>
            )}
          </div>
          <ul className="divide-y divide-surface-container-high">
            {items.map((it) => (
              <li
                key={it.id}
                className={`flex flex-wrap items-center gap-3 px-3 py-2 ${
                  it.status === 'error'
                    ? 'border-l-4 border-l-error bg-error-container/20'
                    : !it.slot
                      ? 'border-l-4 border-l-[#f59e0b] bg-amber-50/60'
                      : 'border-l-4 border-l-transparent'
                }`}
              >
                <Icon name={fileIcon(it.file.name)} className="text-[20px] text-on-surface-variant" fill />
                <div className="min-w-[160px] flex-1">
                  <div className="max-w-[300px] truncate text-[12px] font-medium">{it.file.name}</div>
                  <div className="text-[11px] text-on-surface-variant">
                    {(it.file.size / 1024).toFixed(1)} KB
                    {it.slot && it.suggested && '・種類はファイル名から自動判定'}
                    {!it.slot && <span className="font-bold text-[#b45309]">・何の資料かタグ付けしてください</span>}
                    {it.status === 'error' && <span className="block text-error">{it.error}</span>}
                  </div>
                </div>
                <select
                  className="input-base !w-56 !py-1 !text-[12px]"
                  value={it.slot ?? ''}
                  disabled={it.status === 'uploading'}
                  onChange={(e) => setSlot(it.id, e.target.value)}
                >
                  <option value="" disabled>種類を選択…</option>
                  {slots.map((s) => (
                    <option key={s.key} value={s.key}>{s.label}</option>
                  ))}
                </select>
                <div className="w-32 text-[11px]">
                  {it.status === 'uploading' ? (
                    <span className="flex items-center gap-1.5 text-primary-container">
                      <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-surface-container-high border-t-primary-container" />
                      AI識別中…
                    </span>
                  ) : it.status === 'error' ? (
                    <button className="font-bold text-primary-container hover:underline"
                      onClick={() => setItems((prev) => prev.map((p) => (p.id === it.id ? { ...p, status: 'pending', error: undefined } : p)))}>
                      再試行
                    </button>
                  ) : it.slot ? (
                    <span className="text-outline">待機中…</span>
                  ) : (
                    <span className="text-outline">—</span>
                  )}
                </div>
                <button
                  className="rounded p-1 text-on-surface-variant hover:text-error"
                  title="一覧から削除"
                  disabled={it.status === 'uploading'}
                  onClick={() => remove(it.id)}
                >
                  <Icon name="delete" className="text-[18px]" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
