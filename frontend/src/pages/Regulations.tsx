import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FileText } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { DocumentSummary } from '@/lib/types'
import { Card, Button, Input } from '@/components/ui'

export default function Regulations() {
  const [docs, setDocs] = useState<DocumentSummary[]>([])
  const [filteredDocs, setFilteredDocs] = useState<DocumentSummary[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedDoc, setSelectedDoc] = useState<DocumentSummary | null>(null)
  const [loading, setLoading] = useState(true)

  const pageSize = 20

  useEffect(() => {
    apiClient.listDocuments().then((res) => {
      setDocs(res.documents || [])
      setFilteredDocs(res.documents || [])
      setLoading(false)
    }).catch(err => {
      console.error('Failed to load documents:', err)
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    const result = docs.filter((doc) => {
      const matchesSearch = !searchTerm || doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
      return matchesSearch
    })
    setFilteredDocs(result)
  }, [searchTerm, docs])

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold">Regulations & Compliance Documents</h1>
        <p className="text-slate-400 mt-1">Browse regulatory documents</p>
      </motion.div>

      {/* Search */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
        <div className="flex gap-3">
          <Input
            placeholder="Search by filename..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1"
          />
        </div>
      </motion.div>

      {/* Documents List */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-slate-800/50 rounded animate-pulse" />
          ))}
        </div>
      ) : (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
          <Card>
            {filteredDocs.length === 0 ? (
              <p className="text-slate-400 text-center py-8">No documents found</p>
            ) : (
              <div className="space-y-2">
                {filteredDocs.slice(0, pageSize).map((doc, idx) => (
                  <motion.button
                    key={doc.document_id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    onClick={() => setSelectedDoc(doc)}
                    className="w-full flex items-start gap-3 p-4 hover:bg-slate-800/50 rounded-lg transition-colors text-left"
                  >
                    <FileText className="w-5 h-5 text-blue-400 flex-shrink-0 mt-1" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-white">{doc.filename}</p>
                      <p className="text-xs text-slate-400 mt-1">{doc.chunk_count} chunks</p>
                    </div>
                  </motion.button>
                ))}
              </div>
            )}
          </Card>
        </motion.div>
      )}

      {/* Detail View */}
      {selectedDoc && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <Button onClick={() => setSelectedDoc(null)} variant="secondary" className="mb-4">
            ← Back to List
          </Button>
          <Card>
            <h2 className="text-2xl font-bold mb-4">{selectedDoc.filename}</h2>
            <div className="space-y-4 text-sm text-slate-300">
              <div>
                <p className="font-semibold text-white">Document ID</p>
                <p className="text-xs font-mono text-slate-400 mt-1">{selectedDoc.document_id}</p>
              </div>
              <div>
                <p className="font-semibold text-white">Chunks Indexed</p>
                <p className="mt-1">{selectedDoc.chunk_count}</p>
              </div>
            </div>
          </Card>
        </motion.div>
      )}

      {/* Summary */}
      <Card>
        <p className="text-sm text-slate-400">
          Total: {filteredDocs.length} document{filteredDocs.length !== 1 ? 's' : ''} ({docs.reduce((sum, d) => sum + d.chunk_count, 0)} chunks)
        </p>
      </Card>
    </div>
  )
}
