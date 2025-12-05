import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { kbApi, docApi, retrievalApi } from '../services/api';
import { ArrowLeft, Upload, FileText, Play, Trash2, Loader2 } from 'lucide-react';
import clsx from 'clsx';

export default function KnowledgeBaseDetail() {
    const { id } = useParams<{ id: string }>();
    const [kb, setKb] = useState<any>(null);
    const [activeTab, setActiveTab] = useState('documents');
    const [documents, setDocuments] = useState<any[]>([]);
    const [isUploading, setIsUploading] = useState(false);

    // Retrieval State
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [searchStrategy, setSearchStrategy] = useState('ann');
    const [isSearching, setIsSearching] = useState(false);

    // Chunk Viewer State
    const [selectedDoc, setSelectedDoc] = useState<any>(null);
    const [chunks, setChunks] = useState<any[]>([]);
    const [isLoadingChunks, setIsLoadingChunks] = useState(false);

    useEffect(() => {
        if (id) {
            loadKb();
            loadDocs();
        }
    }, [id]);

    const loadKb = async () => {
        try {
            const res = await kbApi.get(id!);
            setKb(res.data);
        } catch (err) {
            console.error(err);
        }
    };

    const loadDocs = async () => {
        try {
            const res = await docApi.list(id!);
            setDocuments(res.data);
        } catch (err) {
            console.error(err);
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;
        setIsUploading(true);
        try {
            // Default strategy size for now, can add UI to select
            await docApi.upload(id!, e.target.files[0], 'size');
            loadDocs();
        } catch (err) {
            console.error(err);
            alert('Upload failed');
        } finally {
            setIsUploading(false);
        }
    };

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;
        setIsSearching(true);
        try {
            const res = await retrievalApi.retrieve(id!, {
                query,
                top_k: 5,
                score_threshold: 0.0,
                strategy: searchStrategy
            });
            setResults(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setIsSearching(false);
        }
    };

    const handleViewChunks = async (doc: any) => {
        setSelectedDoc(doc);
        setIsLoadingChunks(true);
        try {
            const res = await docApi.getChunks(id!, doc.id);
            setChunks(res.data.chunks || []);
        } catch (err) {
            console.error(err);
            alert('Failed to load chunks');
        } finally {
            setIsLoadingChunks(false);
        }
    };

    const handleDeleteDocument = async (docId: string, e: React.MouseEvent) => {
        e.stopPropagation(); // Prevent triggering row click
        if (!confirm('Are you sure you want to delete this document?')) return;
        try {
            await docApi.delete(id!, docId);
            loadDocs();
        } catch (err) {
            console.error(err);
            alert('Failed to delete document');
        }
    };

    if (!kb) return <div className="container">Loading...</div>;

    return (
        <div className="container">
            <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', color: 'var(--text-secondary)', textDecoration: 'none', marginBottom: '1rem' }}>
                <ArrowLeft size={16} style={{ marginRight: '0.5rem' }} /> Back to Dashboard
            </Link>

            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ margin: '0 0 0.5rem 0' }}>{kb.name}</h1>
                <p style={{ color: 'var(--text-secondary)', margin: 0 }}>{kb.description}</p>
            </div>

            <div style={{ borderBottom: '1px solid var(--border)', marginBottom: '2rem' }}>
                <div style={{ display: 'flex', gap: '2rem' }}>
                    {['documents', 'testing', 'settings'].map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            style={{
                                padding: '0.75rem 0',
                                background: 'none',
                                border: 'none',
                                borderBottom: activeTab === tab ? '2px solid var(--primary)' : '2px solid transparent',
                                color: activeTab === tab ? 'var(--primary)' : 'var(--text-secondary)',
                                fontWeight: 500,
                                textTransform: 'capitalize',
                                fontSize: '1rem'
                            }}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
            </div>

            {activeTab === 'documents' && (
                <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                        <h3>Documents ({documents.length})</h3>
                        <div style={{ position: 'relative' }}>
                            <input
                                type="file"
                                id="file-upload"
                                style={{ display: 'none' }}
                                onChange={handleFileUpload}
                                disabled={isUploading}
                            />
                            <label htmlFor="file-upload" className="btn btn-primary" style={{ cursor: isUploading ? 'not-allowed' : 'pointer', opacity: isUploading ? 0.7 : 1 }}>
                                {isUploading ? <Loader2 className="animate-spin" size={20} /> : <Upload size={20} />}
                                {isUploading ? 'Uploading...' : 'Upload Document'}
                            </label>
                        </div>
                    </div>

                    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead style={{ background: '#f8fafc', borderBottom: '1px solid var(--border)' }}>
                                <tr>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Name</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Status</th>
                                    <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Date</th>
                                    <th style={{ padding: '1rem', textAlign: 'right', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {documents.map((doc) => (
                                    <tr
                                        key={doc.id}
                                        style={{
                                            borderBottom: '1px solid var(--border)',
                                            cursor: 'pointer',
                                            transition: 'background 0.2s'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.background = '#f8fafc'}
                                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                        onClick={() => handleViewChunks(doc)}
                                    >
                                        <td style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                            <FileText size={18} color="var(--text-secondary)" />
                                            {doc.filename}
                                        </td>
                                        <td style={{ padding: '1rem' }}>
                                            <span className={clsx(
                                                'badge',
                                                doc.status === 'completed' && 'badge-success',
                                                doc.status === 'processing' && 'badge-warning',
                                                doc.status === 'error' && 'badge-error'
                                            )}>
                                                {doc.status}
                                            </span>
                                        </td>
                                        <td style={{ padding: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                                            {new Date(doc.created_at).toLocaleDateString()}
                                        </td>
                                        <td style={{ padding: '1rem', textAlign: 'right' }}>
                                            <button
                                                className="btn"
                                                style={{ padding: '0.25rem', color: 'var(--danger)' }}
                                                onClick={(e) => handleDeleteDocument(doc.id, e)}
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                                {documents.length === 0 && (
                                    <tr>
                                        <td colSpan={4} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                            No documents uploaded yet.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {activeTab === 'testing' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '2rem' }}>
                    <div>
                        <div className="card" style={{ marginBottom: '1.5rem' }}>
                            <form onSubmit={handleSearch}>
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <input
                                        className="input"
                                        placeholder="Enter your query to test retrieval..."
                                        value={query}
                                        onChange={(e) => setQuery(e.target.value)}
                                    />
                                    <button type="submit" className="btn btn-primary" disabled={isSearching}>
                                        {isSearching ? <Loader2 className="animate-spin" /> : <Play size={20} />}
                                        Run
                                    </button>
                                </div>
                            </form>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            {results.map((result, idx) => (
                                <div key={idx} className="card">
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                        <span className="badge badge-success">Score: {result.score.toFixed(4)}</span>
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Chunk ID: {result.chunk_id}</span>
                                    </div>
                                    <p style={{ margin: 0, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{result.content}</p>
                                </div>
                            ))}
                            {results.length === 0 && !isSearching && (
                                <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                                    Run a query to see results.
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="card" style={{ height: 'fit-content' }}>
                        <h3 style={{ marginTop: 0 }}>Configuration</h3>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 500 }}>Search Strategy</label>
                            <select
                                className="input"
                                value={searchStrategy}
                                onChange={(e) => setSearchStrategy(e.target.value)}
                            >
                                <option value="ann">Vector Search (ANN)</option>
                                <option value="keyword">Keyword Search</option>
                                <option value="2-stage">2-Stage Retrieval</option>
                            </select>
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 500 }}>Top K</label>
                            <input type="number" className="input" defaultValue={5} />
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 500 }}>Score Threshold</label>
                            <input type="range" style={{ width: '100%' }} min="0" max="1" step="0.1" defaultValue="0.5" />
                        </div>
                    </div>
                </div>
            )}

            {activeTab === 'settings' && (
                <div className="card">
                    <h3>Knowledge Base Settings</h3>
                    <p>Settings implementation pending...</p>
                </div>
            )}

            {/* Chunk Viewer Modal */}
            {selectedDoc && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
                    padding: '2rem'
                }} onClick={() => setSelectedDoc(null)}>
                    <div className="card" style={{
                        width: '100%',
                        maxWidth: '900px',
                        maxHeight: '80vh',
                        overflow: 'auto'
                    }} onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1.5rem' }}>
                            <div>
                                <h2 style={{ margin: '0 0 0.5rem 0' }}>Document Chunks</h2>
                                <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                                    {selectedDoc.filename} - {chunks.length} chunks
                                </p>
                            </div>
                            <button
                                className="btn"
                                onClick={() => setSelectedDoc(null)}
                                style={{ padding: '0.5rem 1rem' }}
                            >
                                Close
                            </button>
                        </div>

                        {isLoadingChunks ? (
                            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                                <Loader2 className="animate-spin" style={{ margin: '0 auto 1rem' }} />
                                Loading chunks...
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                {chunks.map((chunk, idx) => (
                                    <div key={idx} style={{
                                        padding: '1rem',
                                        border: '1px solid var(--border)',
                                        borderRadius: '8px',
                                        background: '#fafafa'
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            marginBottom: '0.75rem',
                                            paddingBottom: '0.75rem',
                                            borderBottom: '1px solid var(--border)'
                                        }}>
                                            <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                                                Chunk {idx + 1}
                                            </span>
                                            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                                ID: {chunk.chunk_id}
                                            </span>
                                        </div>
                                        <p style={{
                                            margin: 0,
                                            lineHeight: 1.6,
                                            whiteSpace: 'pre-wrap',
                                            fontSize: '0.875rem'
                                        }}>
                                            {chunk.content}
                                        </p>
                                    </div>
                                ))}
                                {chunks.length === 0 && (
                                    <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                                        No chunks found for this document.
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
