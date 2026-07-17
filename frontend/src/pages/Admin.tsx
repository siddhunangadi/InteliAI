import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api'
import { DiagnosticsResponse } from '@/lib/types'
import { Card, Button } from '@/components/ui'
import AdminTabs from '@/components/Admin/AdminTabs'
import DiagnosticsPanel from '@/components/Admin/DiagnosticsPanel'

export default function Admin() {
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null)
  const [loading, setLoading] = useState(true)

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
        <div className="space-y-6">
          <Card>
            <h3 className="font-semibold mb-3">Administration Panel</h3>
            <p className="text-slate-300 text-sm">
              Manage system configuration, API keys, and monitor system health. Administrative
              actions are logged and audited for compliance.
            </p>
          </Card>

          <Card>
            <h3 className="font-semibold mb-3">Quick Actions</h3>
            <div className="flex gap-2 flex-wrap">
              <Button variant="secondary">Manage API Keys</Button>
              <Button variant="secondary">Configuration</Button>
              <Button variant="secondary">User Management</Button>
            </div>
          </Card>
        </div>
      ),
    },
    {
      name: 'configuration',
      label: 'Configuration',
      component: (
        <Card>
          <h3 className="font-semibold mb-4">System Configuration</h3>
          <p className="text-slate-400 text-sm mb-4">Configuration settings are managed securely.</p>
          <div className="space-y-3">
            <div className="p-3 bg-slate-800/50 rounded">
              <p className="text-sm font-medium">Regulations Update Frequency</p>
              <p className="text-xs text-slate-400 mt-1">Automatic: Every 24 hours</p>
            </div>
            <div className="p-3 bg-slate-800/50 rounded">
              <p className="text-sm font-medium">Retention Policy</p>
              <p className="text-xs text-slate-400 mt-1">Compliance queries: 7 years</p>
            </div>
          </div>
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
    <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Administration</h1>
        <p className="text-slate-400 mt-1">System configuration and monitoring</p>
      </div>

      <AdminTabs tabs={adminTabs} />
    </motion.div>
  )
}
