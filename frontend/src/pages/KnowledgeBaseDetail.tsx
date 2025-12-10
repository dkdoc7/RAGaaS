import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { kbApi, docApi, retrievalApi } from '../services/api';
import { ArrowLeft, Upload, FileText, Play, Trash2, Loader2, ChevronRight, ChevronDown, ArrowUpDown } from 'lucide-react';
import clsx from 'clsx';
import ConfirmDialog from '../components/ConfirmDialog';

import UploadDocumentModal from '../components/UploadDocumentModal';

export default function KnowledgeBaseDetail() {
    const { id } = useParams<{ id: string }>();
    const [kb, setKb] = useState<any>(null);
    const [activeTab, setActiveTab] = useState('documents');
    const [documents, setDocuments] = useState<any[]>([]);
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

    // Retrieval State
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [searchStrategy, setSearchStrategy] = useState('ann');
    const [isSearching, setIsSearching] = useState(false);
    const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
    const [scoreThreshold, setScoreThreshold] = useState(0.5);
    const [topK, setTopK] = useState(5);
    const [searchDuration, setSearchDuration] = useState<number | null>(null);

    // Reranker State
    const [useReranker, setUseReranker] = useState(false);
    const [rerankerTopK, setRerankerTopK] = useState(5);
    const [rerankerThreshold, setRerankerThreshold] = useState(0.0);
    const [useLLMReranker, setUseLLMReranker] = useState(false);
    const [llmChunkStrategy, setLlmChunkStrategy] = useState('full');

    // NER State
    const [useNER, setUseNER] = useState(false);

    // Graph RAG State
    const [useGraphSearch, setUseGraphSearch] = useState(false);
    const [vectorWeight, setVectorWeight] = useState<number>(0.6);
    const [graphWeight, setGraphWeight] = useState<number>(0.4);
    const [maxHops, setMaxHops] = useState<number>(2);
    const [graphMergeStrategy, setGraphMergeStrategy] = useState<string>('hybrid');

    // Chunk Viewer State
    const [selectedDoc, setSelectedDoc] = useState<any>(null);
    const [chunks, setChunks] = useState<any[]>([]);
    const [isLoadingChunks, setIsLoadingChunks] = useState(false);
    const [expandedParents, setExpandedParents] = useState<Record<string, boolean>>({});
    const [expandedChunks, setExpandedChunks] = useState<Record<number, boolean>>({});

    // Delete confirmation modal state
    const [deleteDocId, setDeleteDocId] = useState<string | null>(null);

    useEffect(() => {
        if (id) {
            loadKb();
            loadDocs();

            // Load saved retrieval settings
            const saved = localStorage.getItem('retrievalSettings');
            if (saved) {
                try {
                    const settings = JSON.parse(saved);
                    setSearchStrategy(settings.searchStrategy || 'ann');
                    setTopK(settings.topK || 5);
                    setScoreThreshold(settings.scoreThreshold || 0.5);
                    setUseReranker(settings.useReranker || false);
                    setRerankerTopK(settings.rerankerTopK || 5);
                    setRerankerThreshold(settings.rerankerThreshold || 0.0);
                    setUseLLMReranker(settings.useLLMReranker || false);
                    setLlmChunkStrategy(settings.llmChunkStrategy || 'full');
                    setUseNER(settings.useNER || false);
                } catch (e) {
                    console.error('Failed to load settings:', e);
                }
            }

            // WebSocket connection
            const ws = new WebSocket(`ws://localhost:8000/api/ws/${id}`);

            ws.onopen = () => {
                console.log('Connected to WebSocket');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'document_status_update') {
                    setDocuments((prevDocs) =>
                        prevDocs.map((doc) =>
                            doc.id === data.doc_id
                                ? { ...doc, status: data.status }
                                : doc
                        )
                    );
                }
            };

            ws.onclose = () => {
                console.log('Disconnected from WebSocket');
            };

            return () => {
                ws.close();
            };
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



    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;
        setIsSearching(true);
        const startTime = performance.now();

        // Save settings to localStorage
        const settings = {
            searchStrategy,
            topK,
            scoreThreshold,
            useReranker,
            rerankerTopK,
            rerankerThreshold,
            useLLMReranker,
            llmChunkStrategy,
            useNER
        };
        localStorage.setItem('retrievalSettings', JSON.stringify(settings));

        try {
            const res = await retrievalApi.retrieve(id!, {
                query,
                top_k: topK,
                score_threshold: scoreThreshold,
                strategy: searchStrategy,
                use_reranker: useReranker && searchStrategy !== '2-stage',
                reranker_top_k: rerankerTopK,
                reranker_threshold: rerankerThreshold,
                use_llm_reranker: useLLMReranker,
                llm_chunk_strategy: llmChunkStrategy,
                use_ner: useNER,
                use_graph_search: useGraphSearch && kb?.enable_graph_rag,
                vector_weight: vectorWeight,
                graph_weight: graphWeight,
                max_hops: maxHops,
                merge_strategy: graphMergeStrategy
            });
            const endTime = performance.now();
            setSearchDuration(endTime - startTime);
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

    const handleDeleteDocument = (docId: string, e: React.MouseEvent) => {
        e.stopPropagation(); // Prevent triggering row click
        setDeleteDocId(docId); // Open confirmation modal
    };

    const confirmDelete = async () => {
        if (!deleteDocId) return;
        try {
            await docApi.delete(id!, deleteDocId);
            loadDocs();
        } catch (err) {
            console.error(err);
            alert('Failed to delete document');
        } finally {
            setDeleteDocId(null); // Close modal
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
                <p style={{ color: 'var(--text-secondary)', margin: '0 0 1rem 0' }}>{kb.description}</p>

                <div className="card" style={{ padding: '1rem', background: '#f8fafc' }}>
                    <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Configuration</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                        <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Chunking Strategy</div>
                            <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                                {kb.chunking_strategy === 'size' && 'Fixed Size'}
                                {kb.chunking_strategy === 'parent_child' && 'Parent-Child'}
                                {kb.chunking_strategy === 'context_aware' && 'Context Aware'}
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Graph RAG</div>
                            <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                                {kb.enable_graph_rag ? '✓ Enabled' : 'Disabled'}
                            </div>
                        </div>
                        {kb.chunking_strategy === 'size' && (
                            <>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Chunk Size</div>
                                    <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{kb.chunking_config.chunk_size || 1000}</div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Overlap</div>
                                    <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{kb.chunking_config.overlap || 200}</div>
                                </div>
                            </>
                        )}
                        {kb.chunking_strategy === 'parent_child' && (
                            <>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Parent Size</div>
                                    <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{kb.chunking_config.parent_size || 2000}</div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Child Size</div>
                                    <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{kb.chunking_config.child_size || 500}</div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Parent Overlap</div>
                                    <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{kb.chunking_config.parent_overlap ?? 0}</div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Child Overlap</div>
                                    <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{kb.chunking_config.child_overlap || 100}</div>
                                </div>
                            </>
                        )}
                        {kb.chunking_strategy === 'context_aware' && (
                            <>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Mode</div>
                                    <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                                        {kb.chunking_config.semantic_mode ? 'Semantic Split (LLM)' : 'Split by Headers'}
                                    </div>
                                </div>
                                {!kb.chunking_config.semantic_mode ? (
                                    <>
                                        <div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Headers</div>
                                            <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                                                {[
                                                    kb.chunking_config.h1 && 'H1',
                                                    kb.chunking_config.h2 && 'H2',
                                                    kb.chunking_config.h3 && 'H3'
                                                ].filter(Boolean).join(', ') || 'None'}
                                            </div>
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Buffer Size</div>
                                            <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{kb.chunking_config.buffer_size || 1}</div>
                                        </div>
                                        <div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Breakpoint Type</div>
                                            <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                                                {kb.chunking_config.breakpoint_type === 'percentile' ? 'Percentile' :
                                                    kb.chunking_config.breakpoint_type === 'standard_deviation' ? 'Std Deviation' :
                                                        kb.chunking_config.breakpoint_type === 'interquartile' ? 'Interquartile' : 'Gradient'}
                                            </div>
                                        </div>
                                        <div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Breakpoint Amount</div>
                                            <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{kb.chunking_config.breakpoint_amount || 95}</div>
                                        </div>
                                    </>
                                )}
                            </>
                        )}
                    </div>
                </div>
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
                            <button
                                className="btn btn-primary"
                                onClick={() => setIsUploadModalOpen(true)}
                            >
                                <Upload size={20} />
                                Upload Document
                            </button>
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
                                            transition: 'background 0.2s'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.background = '#f8fafc'}
                                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                    >
                                        <td
                                            style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}
                                            onClick={() => handleViewChunks(doc)}
                                        >
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

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                            <h3 style={{ margin: 0 }}>Results ({results.length})
                                {searchDuration !== null && (
                                    <span style={{ fontSize: '0.875rem', fontWeight: 'normal', color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>
                                        ({(searchDuration / 1000).toFixed(2)}s)
                                    </span>
                                )}
                            </h3>
                            {results.length > 0 && (
                                <button
                                    className="btn"
                                    onClick={() => setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc')}
                                    style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem' }}
                                >
                                    <ArrowUpDown size={16} />
                                    Sort by Score ({sortOrder === 'desc' ? 'High to Low' : 'Low to High'})
                                </button>
                            )}
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            {[...results]
                                .sort((a, b) => sortOrder === 'desc' ? b.score - a.score : a.score - b.score)
                                .map((result, idx) => {
                                    // Build score breakdown string
                                    const breakdownParts = [];
                                    if (result.metadata?._ner_original) {
                                        breakdownParts.push(`NER: ${result.metadata._ner_original.toFixed(4)} → ${result.score.toFixed(4)}`);
                                    }
                                    if (result.metadata?._reranker_score) {
                                        breakdownParts.push(`Reranker: ${result.metadata._reranker_score.toFixed(4)}`);
                                    }
                                    if (result.metadata?._llm_reranker_score !== undefined) {
                                        breakdownParts.push(`LLM: ${result.metadata._llm_reranker_score.toFixed(4)}`);
                                    }
                                    // Graph RAG Hybrid Breakdown
                                    if (result.metadata?.vector_score !== undefined && result.metadata?.graph_score !== undefined && result.metadata?.applied_weights) {
                                        const vScore = result.metadata.vector_score;
                                        const gScore = result.metadata.graph_score;
                                        const vWeight = result.metadata.applied_weights.vector;
                                        const gWeight = result.metadata.applied_weights.graph;
                                        const vContrib = vScore * vWeight;
                                        const gContrib = gScore * gWeight;
                                        breakdownParts.push(`= v(${vContrib.toFixed(4)}) + g(${gContrib.toFixed(4)})`);
                                    }

                                    const breakdownStr = breakdownParts.length > 0 ? ` (${breakdownParts.join(', ')})` : '';

                                    // Graph RAG info
                                    const source = result.metadata?.source || result.source;
                                    const hasGraphInfo = source || result.metadata?.vector_score !== undefined;

                                    return (
                                        <div key={idx} className="card">
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                                                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                                                    <span className="badge badge-success">
                                                        Score: {result.score.toFixed(4)}{breakdownStr}
                                                    </span>
                                                    {hasGraphInfo && source && (
                                                        <span className={`badge ${source === 'hybrid' ? 'badge-warning' : source === 'graph' ? '' : ''}`}
                                                            style={{
                                                                background: source === 'hybrid' ? '#10b981' : source === 'graph' ? '#8b5cf6' : '#3b82f6',
                                                                color: 'white'
                                                            }}>
                                                            {source === 'hybrid' ? '🔀 Hybrid' : source === 'graph' ? '🕸️ Graph' : '📊 Vector'}
                                                        </span>
                                                    )}
                                                    {result.metadata?.graph_distance !== undefined && (
                                                        <span className="badge" style={{ background: '#f3f4f6', color: '#6b7280' }}>
                                                            {result.metadata.graph_distance}-hop
                                                        </span>
                                                    )}
                                                </div>
                                                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Chunk: {result.chunk_id}</span>
                                            </div>
                                            {hasGraphInfo && (result.metadata?.vector_score !== undefined || result.metadata?.graph_score !== undefined) && (
                                                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.75rem', padding: '0.5rem', background: '#f8fafc', borderRadius: '4px' }}>
                                                    {result.metadata?.vector_score !== undefined && `Vector: ${result.metadata.vector_score.toFixed(4)}`}
                                                    {result.metadata?.vector_score !== undefined && result.metadata?.graph_score !== undefined && ' | '}
                                                    {result.metadata?.graph_score !== undefined && `Graph: ${result.metadata.graph_score.toFixed(4)}`}
                                                    {result.metadata?.applied_weights && ` (weights: ${result.metadata.applied_weights.vector.toFixed(2)}/${result.metadata.applied_weights.graph.toFixed(2)})`}
                                                </div>
                                            )}
                                            <p style={{ margin: 0, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{result.content}</p>
                                        </div>
                                    );
                                })}
                            {results.length === 0 && !isSearching && (
                                <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
                                    Run a query to see results.
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="card" style={{ height: 'fit-content' }}>
                        <h3 style={{ marginTop: 0 }}>Retrieval Pipeline Configuration</h3>
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
                                <option value="hybrid">Hybrid (ANN + BM25)</option>
                            </select>
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 500 }}>Top K</label>
                            <input
                                type="number"
                                className="input"
                                value={topK}
                                onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
                                min={1}
                                max={20}
                            />
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500 }}>
                                    Score Threshold (Cosine Similarity)
                                </label>
                                <input
                                    type="number"
                                    style={{
                                        width: '60px',
                                        fontSize: '0.875rem',
                                        textAlign: 'center',
                                        padding: '0.25rem',
                                        border: '1px solid var(--border)',
                                        borderRadius: '4px'
                                    }}
                                    value={scoreThreshold}
                                    onChange={(e) => setScoreThreshold(parseFloat(e.target.value) || 0)}
                                    step={0.05}
                                    min={0}
                                    max={1}
                                />
                            </div>
                            <input
                                type="range"
                                style={{ width: '100%' }}
                                min="0"
                                max="1"
                                step="0.05"
                                value={scoreThreshold}
                                onChange={(e) => setScoreThreshold(parseFloat(e.target.value))}
                            />
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                                All results are scored using cosine similarity (0 = unrelated, 1 = identical).
                                {searchStrategy === '2-stage' && ' For 2-stage, Cross-Encoder scores are already 0-1 normalized.'}
                            </div>
                        </div>

                        {/* Reranker Configuration */}
                        {searchStrategy !== '2-stage' && (
                            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem', marginTop: '1rem' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', cursor: 'pointer' }}>
                                    <input
                                        type="checkbox"
                                        checked={useReranker}
                                        onChange={(e) => setUseReranker(e.target.checked)}
                                        style={{ cursor: 'pointer' }}
                                    />
                                    <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                                        Use Reranker (Cross-Encoder)
                                    </span>
                                </label>

                                {useReranker && (
                                    <div style={{ paddingLeft: '1.5rem' }}>
                                        <div style={{ marginBottom: '0.75rem' }}>
                                            <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)' }}>
                                                Reranker Top-K
                                            </label>
                                            <input
                                                type="number"
                                                className="input"
                                                style={{ fontSize: '0.875rem' }}
                                                value={rerankerTopK}
                                                onChange={(e) => setRerankerTopK(parseInt(e.target.value) || 5)}
                                                min={1}
                                                max={20}
                                            />
                                        </div>

                                        <div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                                <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                                    Reranker Score Threshold
                                                </label>
                                                <span style={{ fontSize: '0.75rem', fontWeight: 500 }}>
                                                    {rerankerThreshold.toFixed(2)}
                                                </span>
                                            </div>
                                            <input
                                                type="range"
                                                style={{ width: '100%' }}
                                                min="0"
                                                max="1"
                                                step="0.05"
                                                value={rerankerThreshold}
                                                onChange={(e) => setRerankerThreshold(parseFloat(e.target.value))} />
                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                                                Filters reranked results by minimum score
                                            </div>
                                        </div>

                                        {/* LLM Reranker Option */}
                                        <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)' }}>
                                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                                <input
                                                    type="checkbox"
                                                    checked={useLLMReranker}
                                                    onChange={(e) => setUseLLMReranker(e.target.checked)}
                                                    style={{ cursor: 'pointer' }}
                                                />
                                                <span style={{ fontSize: '0.75rem', fontWeight: 500 }}>
                                                    Use LLM for Reranking
                                                </span>
                                            </label>
                                            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: '0.25rem', marginLeft: '1.5rem' }}>
                                                Uses GPT-3.5 for more accurate entity-aware evaluation (slower, requires API key)
                                            </div>

                                            {useLLMReranker && (
                                                <div style={{ marginTop: '0.0rem', paddingLeft: '1.5rem' }}>
                                                    <label style={{ fontSize: '0.7rem', display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)' }}>
                                                        Chunk Strategy
                                                    </label>
                                                    <select
                                                        className="input"
                                                        value={llmChunkStrategy}
                                                        onChange={(e) => setLlmChunkStrategy(e.target.value)}
                                                        style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                                                    >
                                                        <option value="full">Full (최정확, 느림, 비용↑)</option>
                                                        <option value="smart">Smart (엔티티 중심)</option>
                                                        <option value="limited">Limited (1500자, 빠름)</option>
                                                    </select>
                                                    <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                                                        {llmChunkStrategy === 'full' && 'Sends entire chunk to LLM (most accurate)'}
                                                        {llmChunkStrategy === 'smart' && 'Sends entity-relevant snippets (balanced)'}
                                                        {llmChunkStrategy === 'limited' && 'Sends first 1500 chars (fastest, cheapest)'}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* NER Filter */}
                        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem', marginTop: '1rem' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={useNER}
                                    onChange={(e) => setUseNER(e.target.checked)}
                                    style={{ cursor: 'pointer' }}
                                />
                                <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                                    Use NER Filter (Entity Matching)
                                </span>
                            </label>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.25rem', marginLeft: '1.5rem' }}>
                                Penalizes results that don't contain entities found in the query (names, places, etc.)
                            </div>
                        </div>

                        {/* Graph RAG */}
                        {kb?.enable_graph_rag && (
                            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem', marginTop: '1rem', background: '#f8fafc', margin: '1rem -1.5rem -1.5rem', padding: '1.5rem', borderRadius: '0 0 8px 8px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginBottom: '1rem' }}>
                                    <input
                                        type="checkbox"
                                        checked={useGraphSearch}
                                        onChange={(e) => setUseGraphSearch(e.target.checked)}
                                        style={{ cursor: 'pointer' }}
                                    />
                                    <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                                        Use Graph RAG Search
                                    </span>
                                </label>
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '1rem', marginLeft: '1.5rem' }}>
                                    Combines vector search with knowledge graph traversal for entity-aware retrieval
                                </div>

                                {useGraphSearch && (
                                    <div style={{ paddingLeft: '1rem', background: 'white', padding: '1rem', borderRadius: '6px', border: '1px solid var(--border)' }}>
                                        {graphMergeStrategy === 'hybrid' && (
                                            <div style={{ marginBottom: '1rem' }}>
                                                <div style={{ fontSize: '0.75rem', fontWeight: 500, marginBottom: '0.5rem' }}>Search Weight Balance</div>
                                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.5rem' }}>
                                                    <div>
                                                        <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
                                                            Vector Weight: {vectorWeight.toFixed(2)}
                                                        </label>
                                                        <input
                                                            type="range"
                                                            min="0"
                                                            max="1"
                                                            step="0.1"
                                                            value={vectorWeight}
                                                            onChange={(e) => {
                                                                const v = parseFloat(e.target.value);
                                                                setVectorWeight(v);
                                                                setGraphWeight(1 - v);
                                                            }}
                                                            style={{ width: '100%' }}
                                                        />
                                                    </div>
                                                    <div>
                                                        <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
                                                            Graph Weight: {graphWeight.toFixed(2)}
                                                        </label>
                                                        <input
                                                            type="range"
                                                            min="0"
                                                            max="1"
                                                            step="0.1"
                                                            value={graphWeight}
                                                            onChange={(e) => {
                                                                const g = parseFloat(e.target.value);
                                                                setGraphWeight(g);
                                                                setVectorWeight(1 - g);
                                                            }}
                                                            style={{ width: '100%' }}
                                                        />
                                                    </div>
                                                </div>
                                                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', textAlign: 'center' }}>
                                                    Vector: semantic similarity | Graph: entity relationships
                                                </div>
                                            </div>
                                        )}

                                        <div style={{ marginBottom: '1rem' }}>
                                            <div style={{ fontSize: '0.75rem', fontWeight: 500, marginBottom: '0.5rem' }}>Merge Strategy</div>
                                            <select
                                                className="input"
                                                value={graphMergeStrategy}
                                                onChange={(e) => setGraphMergeStrategy(e.target.value)}
                                                style={{ fontSize: '0.875rem' }}
                                            >
                                                <option value="hybrid">Graph + Vector Hybrid</option>
                                                <option value="graph_only">Graph Only</option>
                                            </select>
                                            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                                                Hybrid: Weighted sum of both scores. Only: Pure graph traversal results.
                                            </div>
                                        </div>

                                        <div style={{ marginBottom: '0.5rem' }}>
                                            <div style={{ fontSize: '0.75rem', fontWeight: 500, marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between' }}>
                                                <span>Max Graph Hops</span>
                                                <span>{maxHops}</span>
                                            </div>
                                            <input
                                                type="range"
                                                min="1"
                                                max="3"
                                                step="1"
                                                value={maxHops}
                                                onChange={(e) => setMaxHops(parseInt(e.target.value))}
                                                style={{ width: '100%' }}
                                            />
                                            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                                                1: Direct relations • 2: Neighbor of neighbor • 3: Far fetch
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
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
                                {(() => {
                                    // Group by parent_id if available
                                    const hasParents = chunks.some(c => c.metadata && c.metadata.parent_id !== undefined);

                                    if (hasParents) {
                                        const grouped: Record<string, { content: string, children: any[] }> = {};

                                        chunks.forEach(chunk => {
                                            const parentId = chunk.metadata?.parent_id;
                                            if (parentId !== undefined) {
                                                if (!grouped[parentId]) {
                                                    grouped[parentId] = {
                                                        content: chunk.metadata.parent_content || `Parent Chunk ${parentId}`,
                                                        children: []
                                                    };
                                                }
                                                grouped[parentId].children.push(chunk);
                                            } else {
                                                // Handle orphans if any (shouldn't happen with parent-child strategy)
                                                if (!grouped['orphans']) {
                                                    grouped['orphans'] = { content: 'Other Chunks', children: [] };
                                                }
                                                grouped['orphans'].children.push(chunk);
                                            }
                                        });

                                        return Object.entries(grouped).map(([parentId, parent]) => (
                                            <div key={parentId} style={{
                                                border: '1px solid var(--border)',
                                                borderRadius: '8px',
                                                background: '#fff',
                                                overflow: 'hidden'
                                            }}>
                                                <div
                                                    onClick={() => setExpandedParents(prev => ({ ...prev, [parentId]: !prev[parentId] }))}
                                                    style={{
                                                        padding: '1rem',
                                                        background: '#f8fafc',
                                                        cursor: 'pointer',
                                                        display: 'flex',
                                                        alignItems: 'start',
                                                        gap: '0.75rem',
                                                        borderBottom: expandedParents[parentId] ? '1px solid var(--border)' : 'none'
                                                    }}
                                                >
                                                    {expandedParents[parentId] ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                                                    <div style={{ flex: 1 }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                                            <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                                                                {parentId === 'orphans' ? 'Other Chunks' : `Parent Chunk ${parseInt(parentId) + 1}`}
                                                            </span>
                                                            <span className="badge">
                                                                {parent.children.length} children
                                                            </span>
                                                        </div>
                                                        <p style={{
                                                            margin: 0,
                                                            fontSize: '0.875rem',
                                                            color: 'var(--text-secondary)',
                                                            display: '-webkit-box',
                                                            WebkitLineClamp: expandedParents[parentId] ? undefined : 2,
                                                            WebkitBoxOrient: 'vertical',
                                                            overflow: 'hidden'
                                                        }}>
                                                            {parent.content}
                                                        </p>
                                                    </div>
                                                </div>

                                                {expandedParents[parentId] && (
                                                    <div style={{ padding: '1rem', background: '#fafafa', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                                        {parent.children.map((chunk, idx) => (
                                                            <div key={idx} style={{
                                                                padding: '0.75rem',
                                                                border: '1px solid var(--border)',
                                                                borderRadius: '6px',
                                                                background: '#fff'
                                                            }}>
                                                                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                                                                    Child Chunk {idx + 1} (ID: {chunk.chunk_id})
                                                                </div>
                                                                <p style={{ margin: 0, fontSize: '0.875rem', lineHeight: 1.5 }}>
                                                                    {chunk.content}
                                                                </p>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ));
                                    } else {
                                        // Flat list with collapsible content
                                        return chunks.map((chunk, idx) => (
                                            <div key={idx} style={{
                                                border: '1px solid var(--border)',
                                                borderRadius: '8px',
                                                background: '#fff',
                                                overflow: 'hidden'
                                            }}>
                                                <div
                                                    onClick={() => setExpandedChunks(prev => ({ ...prev, [idx]: !prev[idx] }))}
                                                    style={{
                                                        padding: '1rem',
                                                        background: '#f8fafc',
                                                        cursor: 'pointer',
                                                        display: 'flex',
                                                        alignItems: 'start',
                                                        gap: '0.75rem',
                                                        borderBottom: expandedChunks[idx] ? '1px solid var(--border)' : 'none'
                                                    }}
                                                >
                                                    {expandedChunks[idx] ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                                                    <div style={{ flex: 1 }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                                            <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                                                                Chunk {idx + 1}
                                                            </span>
                                                            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                                                ID: {chunk.chunk_id}
                                                            </span>
                                                        </div>
                                                        <p style={{
                                                            margin: 0,
                                                            fontSize: '0.875rem',
                                                            color: 'var(--text-secondary)',
                                                            display: '-webkit-box',
                                                            WebkitLineClamp: expandedChunks[idx] ? undefined : 2,
                                                            WebkitBoxOrient: 'vertical',
                                                            overflow: 'hidden'
                                                        }}>
                                                            {chunk.content}
                                                        </p>
                                                    </div>
                                                </div>

                                                {expandedChunks[idx] && (
                                                    <div style={{ padding: '1rem', background: '#fafafa' }}>
                                                        <p style={{
                                                            margin: 0,
                                                            lineHeight: 1.6,
                                                            whiteSpace: 'pre-wrap',
                                                            fontSize: '0.875rem'
                                                        }}>
                                                            {chunk.content}
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        ));
                                    }
                                })()}

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

            {/* Delete Confirmation Modal */}
            <ConfirmDialog
                isOpen={!!deleteDocId}
                title="Delete Document"
                message="Are you sure you want to delete this document? This action cannot be undone."
                onConfirm={confirmDelete}
                onCancel={() => setDeleteDocId(null)}
                confirmText="Delete"
                isDestructive={true}
            />

            <UploadDocumentModal
                isOpen={isUploadModalOpen}
                onClose={() => setIsUploadModalOpen(false)}
                kbId={id!}
                onUploadComplete={loadDocs}
            />
        </div>
    );
}
