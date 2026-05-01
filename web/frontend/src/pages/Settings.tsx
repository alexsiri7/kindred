import { useEffect, useState } from 'react'
import { api, type UserSettings } from '../api/client'

export function Settings() {
  const [settings, setSettings] = useState<UserSettings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api
      .get<UserSettings>('/settings')
      .then(setSettings)
      .catch((e: Error) => setError(e.message))
  }, [])

  const save = async (patch: Partial<UserSettings>) => {
    setSaving(true)
    try {
      const next = await api.patch<UserSettings>('/settings', patch)
      setSettings(next)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const exportData = async () => {
    const data = await api.get<unknown>('/export')
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'kindred-export.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const deleteAccount = async () => {
    if (
      !window.confirm(
        'Delete your account and all journal data? This cannot be undone.',
      )
    )
      return
    await api.delete('/account')
    window.location.href = '/login'
  }

  if (error) return <p className="text-red-700">{error}</p>
  if (!settings) return <p className="text-stone-500">Loading…</p>

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <section className="space-y-3 rounded border border-stone-200 bg-white p-4">
        <label className="block text-sm">
          Timezone
          <input
            type="text"
            value={settings.timezone ?? ''}
            onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
            onBlur={(e) => void save({ timezone: e.target.value })}
            placeholder="America/New_York"
            className="mt-1 block w-full rounded border border-stone-300 px-3 py-2"
          />
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={settings.transcript_enabled}
            onChange={(e) =>
              void save({ transcript_enabled: e.target.checked })
            }
          />
          Save full transcript with each entry
        </label>
        {saving && <p className="text-xs text-stone-500">Saving…</p>}
      </section>

      <section className="space-y-3 rounded border border-stone-200 bg-white p-4">
        <h2 className="font-semibold">Your data</h2>
        <button
          type="button"
          onClick={() => void exportData()}
          className="rounded bg-stone-900 px-4 py-2 text-white hover:bg-stone-800"
        >
          Export all data
        </button>
        <button
          type="button"
          onClick={() => void deleteAccount()}
          className="ml-3 rounded border border-red-700 px-4 py-2 text-red-700 hover:bg-red-50"
        >
          Delete account
        </button>
      </section>
    </div>
  )
}
