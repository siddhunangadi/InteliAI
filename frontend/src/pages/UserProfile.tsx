import { useState } from 'react'
import { motion } from 'framer-motion'
import { Card, Button } from '@/components/ui'

export default function UserProfile() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('apiKey') || '')
  const [saved, setSaved] = useState(false)

  const saveApiKey = () => {
    localStorage.setItem('apiKey', apiKey)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-slate-400 mt-1">Manage your preferences and account</p>
      </div>

      <Card>
        <h3 className="font-semibold mb-4">API Access</h3>
        <p className="text-slate-400 text-sm mb-4">
          Enter the API key your administrator issued to authenticate requests to this deployment.
        </p>
        <div className="flex gap-2">
          <input
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder="API key"
            className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
          />
          <Button onClick={saveApiKey}>{saved ? 'Saved' : 'Save'}</Button>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Appearance</h3>
        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="radio" name="theme" value="dark" defaultChecked className="rounded" />
            <span className="text-sm">Dark Mode (Default)</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="radio" name="theme" value="light" className="rounded" />
            <span className="text-sm">Light Mode</span>
          </label>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Notifications</h3>
        <div className="space-y-3">
          <label className="flex items-center justify-between">
            <span className="text-sm">Regulatory Updates</span>
            <input type="checkbox" defaultChecked className="rounded" />
          </label>
          <label className="flex items-center justify-between">
            <span className="text-sm">System Alerts</span>
            <input type="checkbox" defaultChecked className="rounded" />
          </label>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Default Search Behavior</h3>
        <select className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm">
          <option>Hybrid (Full-Text + Semantic)</option>
          <option>Full-Text Only</option>
          <option>Semantic Only</option>
        </select>
      </Card>

      <Button>Save Changes</Button>
    </motion.div>
  )
}
