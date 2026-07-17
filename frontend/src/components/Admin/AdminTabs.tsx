import { useState } from 'react'
import { motion } from 'framer-motion'
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
      <div className="flex gap-2 border-b border-slate-700 mb-6 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.name}
            onClick={() => setActiveTab(tab.name)}
            className={clsx(
              'px-4 py-2 text-sm font-medium transition-all whitespace-nowrap',
              activeTab === tab.name
                ? 'text-white border-b-2 border-blue-500'
                : 'text-slate-400 hover:text-slate-300'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        {tabs.find(t => t.name === activeTab)?.component}
      </motion.div>
    </div>
  )
}
