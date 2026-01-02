import React, { useState } from 'react';
import { Upload, FileText, Trash2 } from 'lucide-react';
import UploadDocumentModal from './UploadDocumentModal';

interface Document {
    id: string;
    filename: string;
    file_type: string;
    status: string;
    created_at: string;
    updated_at: string;
}

interface DocumentsTabProps {
    kbId: string;
    documents: Document[];
    onRefresh: () => void;
    onDeleteDocument: (docId: string) => void;
    onViewChunks: (doc: Document) => void;
    isOntology?: boolean;
}

export default function DocumentsTab({ kbId, documents, onRefresh, onDeleteDocument, onViewChunks }: DocumentsTabProps) {
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

    const getStatusBadge = (status: string) => {
        const statusMap: Record<string, { class: string; label: string }> = {
            completed: { class: 'badge-success', label: 'Completed' },
            processing: { class: 'badge-warning', label: 'Processing' },
            error: { class: 'badge-danger', label: 'Error' }
        };
        const config = statusMap[status] || { class: 'badge-secondary', label: status };
        return <span className={`badge ${config.class}`}>{config.label}</span>;
    };

    return (
        <>
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <div style={{
                    padding: '1.5rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    borderBottom: '1px solid var(--border)'
                }}>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Documents ({documents.length})</h3>
                    <button
                        className="btn btn-primary"
                        onClick={() => setIsUploadModalOpen(true)}
                        style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                    >
                        <Upload size={18} />
                        Upload Document
                    </button>
                </div>

                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border)', backgroundColor: 'rgba(0,0,0,0.02)' }}>
                                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Filename</th>
                                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Type</th>
                                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Status</th>
                                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Uploaded</th>
                                <th style={{ padding: '1rem', textAlign: 'left', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Updated</th>
                                <th style={{ padding: '1rem', textAlign: 'center', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {documents.length === 0 ? (
                                <tr>
                                    <td colSpan={6} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                        <FileText size={48} style={{ margin: '0 auto 1rem', opacity: 0.2 }} />
                                        <p style={{ margin: 0 }}>No documents uploaded yet</p>
                                    </td>
                                </tr>
                            ) : (
                                documents.map((doc) => (
                                    <tr
                                        key={doc.id}
                                        onClick={() => onViewChunks(doc)}
                                        style={{
                                            borderBottom: '1px solid var(--border)',
                                            cursor: 'pointer',
                                            transition: 'background-color 0.15s ease'
                                        }}
                                        className="hover:bg-gray-50"
                                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0.02)'}
                                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                    >
                                        <td style={{ padding: '1rem', fontWeight: 500 }}>{doc.filename}</td>
                                        <td style={{ padding: '1rem' }}>
                                            <span className="badge badge-secondary" style={{ fontSize: '0.75rem' }}>{doc.file_type.toUpperCase()}</span>
                                        </td>
                                        <td style={{ padding: '1rem' }}>{getStatusBadge(doc.status)}</td>
                                        <td style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                                            {new Date(doc.created_at).toLocaleString()}
                                        </td>
                                        <td style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                                            {doc.updated_at ? new Date(doc.updated_at).toLocaleString() : '-'}
                                        </td>
                                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                                            <button
                                                className="btn btn-icon danger"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onDeleteDocument(doc.id);
                                                }}
                                                title="Delete Document"
                                                style={{
                                                    color: 'var(--error)',
                                                    opacity: 0.7,
                                                    transition: 'opacity 0.2s',
                                                    padding: '0.5rem',
                                                    borderRadius: '4px'
                                                }}
                                                onMouseEnter={(e) => {
                                                    e.currentTarget.style.opacity = '1';
                                                    e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
                                                }}
                                                onMouseLeave={(e) => {
                                                    e.currentTarget.style.opacity = '0.7';
                                                    e.currentTarget.style.backgroundColor = 'transparent';
                                                }}
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <UploadDocumentModal
                isOpen={isUploadModalOpen}
                onClose={() => setIsUploadModalOpen(false)}
                kbId={kbId}
                onUploadComplete={onRefresh}
            />
        </>
    );
}
