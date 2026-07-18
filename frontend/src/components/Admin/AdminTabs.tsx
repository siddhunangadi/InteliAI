import { useState } from 'react'
import { clsx } from 'clsx'

interface Tab {
  name: string
  label: string
  component: React.ReactNode
}

interface AdminTabsProps {
  tabs: Tab[]
  activeTab?: string
  onTabChange?: (name: string) => void
}

export default function AdminTabs({ tabs, activeTab: controlledTab, onTabChange }: AdminTabsProps) {
  const [internalTab, setInternalTab] = useState(tabs[0]?.name || '')
  const activeTab = controlledTab ?? internalTab
  const setActiveTab = onTabChange ?? setInternalTab

  return (
    <div>
      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-rule mb-6 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.name}
            onClick={() => setActiveTab(tab.name)}
            className={clsx(
              'px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap',
              activeTab === tab.name ? 'text-ink border-b-2 border-clay' : 'text-ink-muted hover:text-ink'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content -- switching tabs is an instant state change, not an
          entrance to animate. */}
      <div>{tabs.find(t => t.name === activeTab)?.component}</div>
    </div>
  )
}
