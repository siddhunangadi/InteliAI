import { useState, useEffect } from 'react'
import { isAxiosError } from 'axios'
import { FileText, Trash2 } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { DocumentSummary, DocumentDetail } from '@/lib/types'
import { Card, Button, Input, ConfirmDialog, useToast } from '@/components/ui'

export default function Regulations() {
  const [docs, setDocs] = useState<DocumentSummary[]>([])
  const [filteredDocs, setFilteredDocs] = useState<DocumentSummary[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedDoc, setSelectedDoc] = useState<DocumentSummary | null>(null)
  const [detail, setDetail] = useState<DocumentDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>()
  const { addToast } = useToast()

  const pageSize = 20

  const load = () => {
    setLoading(true)
    apiClient.listDocuments().then((res) => {
      setDocs(res.documents || [])
      setFilteredDocs(res.documents || [])
      setLoading(false)
    }).catch(err => {
      console.error('Failed to load documents:', err)
      if (isAxiosError(err) && err.response?.status === 401) {
        setError('Your API key is missing or invalid. Add it in Settings to view regulations.')
      } else {
        setError('Unable to load regulations. Please try again later.')
      }
      setLoading(false)
    })
  }

  useEffect(load, [])

  useEffect(() => {
    const result = docs.filter((doc) => {
      const matchesSearch = !searchTerm || doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
      return matchesSearch
    })
    setFilteredDocs(result)
  }, [searchTerm, docs])

  useEffect(() => {
    if (!selectedDoc) {
      setDetail(null)
      return
    }
    setDetailLoading(true)
    apiClient.getDocument(selectedDoc.document_id)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false))
  }, [selectedDoc])

  const handleDelete = async () => {
    if (!selectedDoc) return
    setDeleting(true)
    try {
      await apiClient.deleteDocument(selectedDoc.document_id)
      addToast('success', `${selectedDoc.filename} deleted.`)
      setSelectedDoc(null)
      setConfirmDelete(false)
      load()
    } catch {
      addToast('error', 'Failed to delete document.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-display text-ink">Regulations & Compliance Documents</h1>
        <p className="text-ink-muted mt-1">Browse regulatory documents</p>
      </div>

      <Input
        placeholder="Search by filename..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
      />

      {error && (
        <Card className="bg-status-critical/10 border-status-critical/30">
          <p className="text-status-critical text-sm">{error}</p>
        </Card>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-paper-raised rounded-md" />
          ))}
        </div>
      ) : error ? null : (
        <Card>
          {filteredDocs.length === 0 ? (
            <p className="text-ink-muted text-center py-8">No documents found</p>
          ) : (
            <div className="space-y-1">
              {filteredDocs.slice(0, pageSize).map((doc) => (
                <button
                  key={doc.document_id}
                  onClick={() => setSelectedDoc(doc)}
                  className="w-full flex items-start gap-3 p-4 hover:bg-paper-raised rounded-sm transition-colors text-left"
                >
                  <FileText className="w-5 h-5 text-clay flex-shrink-0 mt-1" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-ink">{doc.filename}</p>
                    <p className="text-label text-ink-muted mt-1">{doc.chunk_count} chunks</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Detail view: real metadata + content preview from GET /documents/{id} */}
      {selectedDoc && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <Button onClick={() => setSelectedDoc(null)} variant="secondary">
              ← Back to List
            </Button>
            <Button variant="danger" icon={<Trash2 className="w-4 h-4" />} onClick={() => setConfirmDelete(true)}>
              Delete Document
            </Button>
          </div>
          <Card>
            <h2 className="text-title text-ink mb-4">{selectedDoc.filename}</h2>
            {detailLoading ? (
              <p className="text-ink-muted text-sm">Loading details...</p>
            ) : detail ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {[
                    detail.regulation && { label: 'Regulation', value: detail.regulation },
                    detail.jurisdiction && { label: 'Jurisdiction', value: detail.jurisdiction },
                    detail.risk_category && { label: 'Risk', value: detail.risk_category },
                    detail.document_type && { label: 'Type', value: detail.document_type },
                    detail.article && { label: 'Article', value: detail.article },
                    detail.section && { label: 'Section', value: detail.section },
                    detail.clause && { label: 'Clause', value: detail.clause },
                    detail.page && { label: 'Page', value: String(detail.page) },
                    detail.effective_date && { label: 'Effective', value: detail.effective_date },
                  ]
                    .filter(Boolean)
                    .map((m) => m && (
                      <span key={m.label} className="badge bg-paper-raised border border-rule text-ink-muted">
                        {m.label}: {m.value}
                      </span>
                    ))}
                </div>
                <div>
                  <p className="text-label text-ink-muted mb-1">Document ID</p>
                  <p className="text-mono-data text-ink-muted">{selectedDoc.document_id}</p>
                </div>
                <div>
                  <p className="text-label text-ink-muted mb-1">Chunks Indexed</p>
                  <p className="text-sm text-ink">{detail.chunk_count}</p>
                </div>
                <div>
                  <p className="text-label text-ink-muted mb-1">Content Preview</p>
                  <p className="text-mono-data text-ink bg-paper-raised border border-rule rounded-sm p-3 whitespace-pre-wrap">
                    {detail.content_preview}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-ink-muted text-sm">Unable to load document details.</p>
            )}
          </Card>
        </div>
      )}

      {!error && (
        <Card>
          <p className="text-sm text-ink-muted">
            Total: {filteredDocs.length} document{filteredDocs.length !== 1 ? 's' : ''} ({docs.reduce((sum, d) => sum + d.chunk_count, 0)} chunks)
          </p>
        </Card>
      )}

      <ConfirmDialog
        isOpen={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={handleDelete}
        title="Delete document?"
        description={`This permanently removes "${selectedDoc?.filename}" and all its indexed chunks from the search index. This cannot be undone.`}
        confirmText={deleting ? 'Deleting...' : 'Delete'}
        isDangerous
      />
    </div>
  )
}
