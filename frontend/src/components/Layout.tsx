import { Link, useLocation } from 'react-router-dom'
import { BarChart3, Upload, MessageCircle, BookOpen, History, Activity, Settings, ShieldCheck, Loader2 } from 'lucide-react'
import { ReactNode, useEffect, useState } from 'react'
import clsx from 'clsx'
import { useUploadJob } from '@/lib/uploadJob'
import { apiClient } from '@/lib/api'

interface LayoutProps {
  children: ReactNode
}

const navItems = [
  { href: '/', icon: BarChart3, label: 'Dashboard' },
  { href: '/upload', icon: Upload, label: 'Upload' },
  { href: '/chat', icon: MessageCircle, label: 'Ask' },
  { href: '/regulations', icon: BookOpen, label: 'Regulations' },
  { href: '/audit', icon: History, label: 'Audit' },
  { href: '/status', icon: Activity, label: 'Health' },
  { href: '/admin', icon: Settings, label: 'Admin' },
]

// Mobile gets a fixed set of icon-only quick links (DESIGN.md: bottom icon
// bar, not a hamburger drawer). Keep it to the primary workflows.
const mobileNavItems = navItems.filter((i) => ['/', '/upload', '/chat', '/audit'].includes(i.href))

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const isActive = (path: string) => location.pathname === path
  const { job } = useUploadJob()
  const [version, setVersion] = useState<string | null>(null)

  useEffect(() => {
    apiClient.getVersion().then((r) => setVersion(r.version)).catch(() => setVersion(null))
  }, [])

  return (
    <div className="flex h-screen bg-void">
      <aside className="w-60 border-r border-seam bg-void flex-col fixed inset-y-0 left-0 z-40 hidden md:flex">
        <div className="p-5 border-b border-seam flex items-center gap-3">
          <div className="w-8 h-8 flex items-center justify-center bg-signal rounded-sm">
            <ShieldCheck className="w-4.5 h-4.5 text-void" strokeWidth={2.25} />
          </div>
          <div>
            <h1 className="text-title text-ink">InteliAI</h1>
            <p className="text-label text-ink-muted">Enterprise</p>
          </div>
        </div>

        <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto scrollbar-thin">
          {navItems.map((item) => (
            <Link
              key={item.href}
              to={item.href}
              className={clsx(
                'relative flex items-center gap-3 px-4 py-2.5 rounded-sm text-label transition-colors',
                isActive(item.href) ? 'text-ink bg-panel' : 'text-ink-muted hover:text-ink hover:bg-panel'
              )}
            >
              {isActive(item.href) && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 bg-signal rounded-full" />
              )}
              <item.icon className="w-4 h-4" />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        {job?.status === 'processing' && (
          <div className="mx-3 mb-3 p-3 bg-panel border border-seam rounded-sm flex items-start gap-2">
            <Loader2 className="w-4 h-4 text-signal animate-spin flex-shrink-0 mt-0.5" />
            <div className="min-w-0">
              <p className="text-label text-ink">Indexing in background</p>
              <p className="text-label text-ink-muted truncate">
                {job.filenames.length} document{job.filenames.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
        )}

        <div className="p-4 border-t border-seam">
          <p className="text-label text-ink-muted">{version ? `Version ${version}` : ' '}</p>
        </div>
      </aside>

      <main className="flex-1 overflow-auto bg-void md:ml-60 pb-16 md:pb-0">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4 md:py-8">{children}</div>
      </main>

      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-void border-t border-seam flex items-stretch h-16">
        {mobileNavItems.map((item) => (
          <Link
            key={item.href}
            to={item.href}
            className={clsx(
              'flex-1 flex flex-col items-center justify-center gap-1 text-label',
              isActive(item.href) ? 'text-signal' : 'text-ink-muted'
            )}
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  )
}
