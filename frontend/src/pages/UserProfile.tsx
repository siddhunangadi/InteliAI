import { useState } from 'react'
import { Card, Button } from '@/components/ui'

// Real /settings page. The old version (and the deleted duplicate at
// pages/Settings.tsx) shipped a theme toggle, notification checkboxes, and a
// "default search behavior" select that saved nothing and did nothing --
// DESIGN.md bans shipping fake-looking UI as if finished. API key storage is
// the one setting this app actually persists (see lib/api.ts request
// interceptor), so it's the only thing here.
export default function UserProfile() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('apiKey') || '')
  const [saved, setSaved] = useState(false)

  const saveApiKey = () => {
    localStorage.setItem('apiKey', apiKey)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-display text-ink">Settings</h1>
        <p className="text-ink-muted mt-1">Manage your API access</p>
      </div>

      <Card>
        <h3 className="text-title text-ink mb-4">API Access</h3>
        <p className="text-ink-muted text-sm mb-4">
          Enter the API key your administrator issued to authenticate requests to this deployment.
        </p>
        <div className="flex gap-2">
          <input
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder="API key"
            className="input flex-1"
          />
          <Button onClick={saveApiKey}>{saved ? 'Saved' : 'Save'}</Button>
        </div>
      </Card>
    </div>
  )
}
