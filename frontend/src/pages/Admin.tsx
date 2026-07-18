import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'
import { DiagnosticsResponse } from '@/lib/types'
import { Card } from '@/components/ui'
import AdminTabs from '@/components/Admin/AdminTabs'
import DiagnosticsPanel from '@/components/Admin/DiagnosticsPanel'

// DESIGN.md bans shipping "Coming soon" dead ends -- the old Overview tab
// had two permanently-disabled buttons (API key / user management) and a
// Configuration tab with two static fake info blocks not backed by any
// endpoint. Both removed; only Overview (real copy) and Diagnostics (real
// GET /diagnostics data) remain.
export default function Admin() {
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    apiClient.getDiagnostics()
      .then(setDiagnostics)
      .finally(() => setLoading(false))
  }, [])

  const adminTabs = [
    {
      name: 'overview',
      label: 'Overview',
      component: (
        <Card>
          <h3 className="text-title text-ink mb-3">Administration Panel</h3>
          <p className="text-ink-muted text-sm">
            Manage system configuration, API keys, and monitor system health. Administrative
            actions are logged and audited for compliance.
          </p>
        </Card>
      ),
    },
    {
      name: 'diagnostics',
      label: 'Diagnostics',
      component: <DiagnosticsPanel diagnostics={diagnostics} loading={loading} />,
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-display text-ink">Administration</h1>
        <p className="text-ink-muted mt-1">System configuration and monitoring</p>
      </div>

      <AdminTabs tabs={adminTabs} activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  )
}
