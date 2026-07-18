import { Link, useLocation } from 'react-router-dom'
import { BarChart3, Upload, MessageCircle, BookOpen, History, Activity, Settings, ChevronRight, Menu, X, ShieldCheck, Loader2 } from 'lucide-react'
import { ReactNode, useState } from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'
import { useUploadJob } from '@/lib/uploadJob'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const isActive = (path: string) => location.pathname === path
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const { job } = useUploadJob()

  const navItems = [
    { href: '/', icon: BarChart3, label: 'Dashboard' },
    { href: '/upload', icon: Upload, label: 'Upload' },
    { href: '/chat', icon: MessageCircle, label: 'AI Assistant' },
    { href: '/regulations', icon: BookOpen, label: 'Regulations' },
    { href: '/audit', icon: History, label: 'Audit' },
    { href: '/status', icon: Activity, label: 'Health' },
    { href: '/admin', icon: Settings, label: 'Admin' },
  ]

  return (
    <div className="flex h-screen bg-slate-950">
      {mobileNavOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      <aside
        className={clsx(
          'w-64 border-r border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 flex flex-col',
          'fixed inset-y-0 left-0 z-40 transition-transform duration-200 md:static md:translate-x-0',
          mobileNavOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="p-6 border-b border-slate-800/50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 flex items-center justify-center bg-blue-600 rounded-lg ring-1 ring-inset ring-white/10 shadow-lg shadow-blue-950/50">
              <ShieldCheck className="w-5 h-5 text-white" strokeWidth={2.25} />
            </div>
            <div>
              <h1 className="font-semibold tracking-tight text-white">Compliance AI</h1>
              <p className="text-xs text-slate-400">Enterprise Edition</p>
            </div>
          </div>
          <button
            className="md:hidden text-slate-400 hover:text-slate-100"
            onClick={() => setMobileNavOpen(false)}
            aria-label="Close navigation"
          >
            <X className="w-5 h-5" />
          </button>
        </motion.div>

        <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto scrollbar-thin">
          {navItems.map((item, idx) => (
            <motion.div
              key={item.href}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
            >
              <Link
                to={item.href}
                onClick={() => setMobileNavOpen(false)}
                className={clsx(
                  'flex items-center justify-between gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 group',
                  isActive(item.href)
                    ? 'bg-blue-600/90 text-white font-medium shadow-lg'
                    : 'text-slate-300 hover:bg-slate-800/50 hover:text-slate-100'
                )}
              >
                <div className="flex items-center gap-3">
                  <item.icon className={clsx('w-4 h-4', isActive(item.href) ? 'text-white' : 'text-slate-400')} />
                  <span className="text-sm">{item.label}</span>
                </div>
                {isActive(item.href) && <ChevronRight className="w-3 h-3 opacity-70" />}
              </Link>
            </motion.div>
          ))}
        </nav>

        {job?.status === 'processing' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mx-3 mb-3 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg flex items-start gap-2"
          >
            <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0 mt-0.5" />
            <div className="min-w-0">
              <p className="text-xs font-medium text-blue-300">Indexing in background</p>
              <p className="text-xs text-slate-400 truncate">
                {job.filenames.length} document{job.filenames.length !== 1 ? 's' : ''}
              </p>
            </div>
          </motion.div>
        )}

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="p-4 border-t border-slate-800/50 space-y-2 bg-slate-900/50">
          <p className="text-xs text-slate-400">Build: 1.0.0</p>
          <p className="text-xs text-slate-500">© 2026 Financial Compliance AI</p>
        </motion.div>
      </aside>

      <main className="flex-1 overflow-auto bg-slate-950">
        <button
          className="md:hidden m-4 p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-slate-100"
          onClick={() => setMobileNavOpen(true)}
          aria-label="Open navigation"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4 md:py-8">{children}</div>
      </main>
    </div>
  )
}
