import React, { useState } from 'react';

interface SearchResultsProps {
    chunks: any[];
}

export default function SearchResults({ chunks }: SearchResultsProps) {
    const [activeTab, setActiveTab] = useState<'graph' | 'chunks'>('chunks');

    // Reset tab to chunks when new results arrive
    React.useEffect(() => {
        setActiveTab('chunks');
    }, [chunks]);

    if (!chunks || chunks.length === 0) {
        return (
            <div style={{
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-secondary)',
                border: '1px dashed var(--border)',
                borderRadius: '8px',
                padding: '2rem',
                textAlign: 'center'
            }}>
                <p>Retrieved chunks and graph details will appear here after your search.</p>
            </div>
        );
    }

    // Search ALL chunks for metadata (not just the first one)
    // This is needed because chunks may be filtered/reordered after API response
    let graphMetadata = null;
    let extractedKeywords = null;

    for (const chunk of chunks) {
        if (!graphMetadata && chunk.graph_metadata) {
            graphMetadata = chunk.graph_metadata;
        }
        if (!extractedKeywords && chunk.metadata?.extracted_keywords && chunk.metadata.extracted_keywords.length > 0) {
            extractedKeywords = chunk.metadata.extracted_keywords;
        }
        // Stop early if both are found
        if (graphMetadata && extractedKeywords) break;
    }

    // Debug: Log the data to verify it's being received correctly
    console.log('[SearchResults] chunks count:', chunks.length);
    console.log('[SearchResults] graphMetadata:', graphMetadata);
    console.log('[SearchResults] extractedKeywords:', extractedKeywords);
    console.log('[SearchResults] Show Retrieval Tab:', graphMetadata || (extractedKeywords && extractedKeywords.length > 0));

    // Tab styles
    const tabStyle = (isActive: boolean) => ({
        padding: '0.75rem 1.5rem',
        cursor: 'pointer',
        borderBottom: isActive ? '3px solid var(--primary)' : '3px solid transparent',
        fontWeight: isActive ? 600 : 400,
        color: isActive ? 'var(--primary)' : 'var(--text-secondary)',
        transition: 'all 0.2s',
        background: isActive ? 'var(--bg-secondary)' : 'transparent'
    });

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Tab Headers */}
            <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', marginBottom: '1rem' }}>
                <div
                    style={tabStyle(activeTab === 'chunks')}
                    onClick={() => setActiveTab('chunks')}
                >
                    📄 Retrieved Chunks ({chunks.length})
                </div>
                {(graphMetadata || (extractedKeywords && extractedKeywords.length > 0)) && (
                    <div
                        style={tabStyle(activeTab === 'graph')}
                        onClick={() => setActiveTab('graph')}
                    >
                        🔍 Retrieval Details
                    </div>
                )}
            </div>

            {/* Tab Content */}
            <div style={{ flex: 1, overflowY: 'auto' }}>
                {/* Chunks Tab */}
                {activeTab === 'chunks' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {chunks.map((chunk, idx) => (
                            <div
                                key={idx}
                                className="card"
                                style={{
                                    padding: '1rem',
                                    background: '#f8fafc',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border)',
                                    borderLeft: '4px solid var(--primary)'
                                }}
                            >
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    marginBottom: '0.5rem',
                                    fontSize: '0.75rem',
                                    color: 'var(--text-secondary)'
                                }}>
                                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                        <span style={{ fontWeight: 600 }}>Chunk {idx + 1}</span>
                                        {chunk.chunk_id && (
                                            <span className="badge" style={{ fontSize: '0.65rem', backgroundColor: '#f1f5f9', color: '#475569' }}>
                                                ID: {chunk.chunk_id}
                                            </span>
                                        )}
                                    </div>
                                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                        {chunk.metadata?.source === 'graph' && (
                                            <span className="badge" style={{ fontSize: '0.65rem', backgroundColor: '#dcfce7', color: '#166534' }}>
                                                Graph
                                            </span>
                                        )}
                                        <span className="badge badge-secondary" style={{ fontSize: '0.7rem' }}>
                                            Score: {chunk.score?.toFixed(4)}
                                            {chunk.l2_score != null && ` (L2: ${chunk.l2_score.toFixed(4)})`}
                                        </span>
                                    </div>
                                </div>
                                <div style={{
                                    fontSize: '0.9rem',
                                    lineHeight: '1.6',
                                    color: 'var(--text-primary)',
                                    whiteSpace: 'pre-wrap'
                                }}>
                                    {chunk.content}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Retrieval Details Tab (Graph + Keyword) */}
                {activeTab === 'graph' && (graphMetadata || (extractedKeywords && extractedKeywords.length > 0)) && (
                    <div className="card" style={{
                        background: '#f0f9ff',
                        borderLeft: '4px solid var(--primary)'
                    }}>
                        {/* Extracted Keywords Section */}
                        {extractedKeywords && extractedKeywords.length > 0 && (
                            <div style={{ marginBottom: '1.5rem' }}>
                                <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                                    🔑 Extracted Keywords (Hybrid/BM25):
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                    {extractedKeywords.map((kw: string, idx: number) => (
                                        <span key={idx} className="badge" style={{ fontSize: '0.8rem', background: '#fffbeb', border: '1px solid #fcd34d', color: '#b45309' }}>
                                            {kw}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {graphMetadata && (
                            <>

                                {/* Extracted Entities */}
                                <div style={{ marginBottom: '1.5rem' }}>
                                    <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                                        Extracted Entities:
                                    </div>
                                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                        {graphMetadata.extracted_entities && graphMetadata.extracted_entities.length > 0 ? (
                                            graphMetadata.extracted_entities.map((entity: string, idx: number) => (
                                                <span key={idx} className="badge" style={{ fontSize: '0.8rem', background: 'white', border: '1px solid #bae6fd', color: '#0369a1' }}>
                                                    {entity}
                                                </span>
                                            ))
                                        ) : (
                                            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>None detected</span>
                                        )}
                                    </div>
                                </div>

                                {/* Rewritten Query */}
                                {graphMetadata.rewritten_query && (
                                    <div style={{ marginBottom: '1.5rem', padding: '0.75rem', background: '#fef3c7', borderRadius: '6px', border: '1px solid #fcd34d' }}>
                                        <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem', color: '#92400e' }}>
                                            🔄 Query Understanding:
                                        </div>
                                        <div style={{ fontSize: '0.75rem', color: '#78350f', marginBottom: '0.5rem' }}>
                                            <strong>Rewritten:</strong> {graphMetadata.rewritten_query.rewritten_query_text || 'N/A'}
                                        </div>
                                        {graphMetadata.rewritten_query.query_type && (
                                            <div style={{ fontSize: '0.7rem', color: '#78350f', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                                                <span className="badge" style={{ fontSize: '0.65rem', backgroundColor: '#fef3c7', color: '#92400e', border: '1px solid #fcd34d' }}>
                                                    Type: {graphMetadata.rewritten_query.query_type}
                                                </span>
                                                {graphMetadata.rewritten_query.hops && (
                                                    <span className="badge" style={{ fontSize: '0.65rem', backgroundColor: '#fef3c7', color: '#92400e', border: '1px solid #fcd34d' }}>
                                                        Hops: {graphMetadata.rewritten_query.hops}
                                                    </span>
                                                )}
                                                {graphMetadata.rewritten_query.start_entity && (
                                                    <span className="badge" style={{ fontSize: '0.65rem', backgroundColor: '#fef3c7', color: '#92400e', border: '1px solid #fcd34d' }}>
                                                        Start: {graphMetadata.rewritten_query.start_entity}
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Triples */}
                                {graphMetadata.triples && graphMetadata.triples.length > 0 && (
                                    <div style={{ marginBottom: '1.5rem' }}>
                                        <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                                            Knowledge Graph Triples ({graphMetadata.triples.length}):
                                        </div>
                                        <div style={{
                                            maxHeight: '200px',
                                            overflowY: 'auto',
                                            background: 'white',
                                            padding: '0.75rem',
                                            borderRadius: '6px',
                                            fontSize: '0.8rem',
                                            border: '1px solid #e0f2fe'
                                        }}>
                                            {graphMetadata.triples.map((triple: any, idx: number) => {
                                                let s = 'Unknown';
                                                let p = 'Unknown';
                                                let o = 'Unknown';

                                                // Handle string format "(Subject) -[Predicate]-> (Object)"
                                                if (typeof triple === 'string') {
                                                    const match = triple.match(/\((.*?)\)\s-\[(.*?)\]->\s\((.*?)\)/);
                                                    if (match) {
                                                        s = match[1];
                                                        p = match[2];
                                                        o = match[3];
                                                    } else {
                                                        // Fallback for raw strings
                                                        s = triple;
                                                        p = '';
                                                        o = '';
                                                    }
                                                } else {
                                                    // Handle object format
                                                    s = triple.subject;
                                                    p = triple.predicate;
                                                    o = triple.object;
                                                }

                                                const formatValue = (val: string) => {
                                                    try {
                                                        if (!val) return '';
                                                        let text = val;
                                                        if (text.startsWith('http')) {
                                                            const parts = text.split('/');
                                                            text = parts[parts.length - 1];
                                                        }
                                                        return decodeURIComponent(text).replace(/_/g, ' ');
                                                    } catch (e) {
                                                        return val;
                                                    }
                                                };

                                                return (
                                                    <div key={idx} style={{
                                                        padding: '0.5rem',
                                                        marginBottom: '0.5rem',
                                                        background: '#f8fafc',
                                                        borderRadius: '4px',
                                                        fontFamily: 'monospace',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        flexWrap: 'wrap',
                                                        gap: '0.25rem'
                                                    }}>
                                                        <span style={{ color: '#0284c7', fontWeight: 600 }}>{formatValue(s)}</span>
                                                        {p && (
                                                            <>
                                                                <span style={{ color: '#94a3b8' }}>→</span>
                                                                <span style={{ color: '#7c3aed' }}>{formatValue(p)}</span>
                                                                <span style={{ color: '#94a3b8' }}>→</span>
                                                                <span style={{ color: '#0284c7', fontWeight: 600 }}>{formatValue(o)}</span>
                                                            </>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}

                                {/* Graph Search Results Summary */}
                                {graphMetadata.total_chunks_found !== undefined && (
                                    <div style={{ marginBottom: '1.5rem', padding: '1rem', background: '#f0fdf4', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
                                        <div style={{ fontWeight: 600, marginBottom: '0.75rem', color: '#166534', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                            📊 Graph Search Results
                                            <span className="badge" style={{ fontSize: '0.7rem', backgroundColor: '#dcfce7', color: '#166534' }}>
                                                {graphMetadata.total_chunks_found} chunk{graphMetadata.total_chunks_found !== 1 ? 's' : ''} found
                                            </span>
                                        </div>
                                        <div style={{ fontSize: '0.75rem', color: '#166534', marginBottom: '0.5rem' }}>
                                            Graph traversal discovered <strong>{graphMetadata.total_chunks_found}</strong> related chunk{graphMetadata.total_chunks_found !== 1 ? 's' : ''} through entity relationships.
                                            {chunks.filter((c: any) => c.metadata?.source === 'graph').length > 0 && (
                                                <> Retrieved <strong>{chunks.filter((c: any) => c.metadata?.source === 'graph').length}</strong> for display.</>
                                            )}
                                        </div>
                                        {graphMetadata.total_chunks_found > 0 && (
                                            <div style={{ marginTop: '0.75rem' }}>
                                                <div style={{ fontSize: '0.7rem', fontWeight: 600, marginBottom: '0.5rem', color: '#15803d' }}>
                                                    Chunk IDs discovered by graph:
                                                </div>
                                                <div style={{
                                                    maxHeight: '120px',
                                                    overflowY: 'auto',
                                                    background: 'white',
                                                    padding: '0.5rem',
                                                    borderRadius: '4px',
                                                    fontSize: '0.7rem',
                                                    border: '1px solid #d1fae5',
                                                    display: 'flex',
                                                    flexWrap: 'wrap',
                                                    gap: '0.25rem'
                                                }}>
                                                    {chunks.filter((c: any) => c.chunk_id && c.metadata?.source === 'graph').length > 0 ? (
                                                        chunks.filter((c: any) => c.chunk_id && c.metadata?.source === 'graph').map((chunk: any, idx: number) => (
                                                            <span key={idx} className="badge" style={{ fontSize: '0.65rem', backgroundColor: '#f0fdf4', color: '#15803d', border: '1px solid #d1fae5' }}>
                                                                {chunk.chunk_id}
                                                            </span>
                                                        ))
                                                    ) : (
                                                        <span style={{ color: '#9ca3af', fontStyle: 'italic' }}>Chunk IDs not available in current view</span>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Query Display */}
                                {graphMetadata.sparql_query && (
                                    <div style={{ marginBottom: '1rem', padding: '1rem', background: '#f1f5f9', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
                                        <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: '#334155' }}>
                                            {graphMetadata.graph_backend === 'neo4j' ? 'Cypher Query:' : 'SPARQL Query:'}
                                        </div>
                                        <pre style={{
                                            background: '#1e293b',
                                            color: '#e2e8f0',
                                            padding: '1rem',
                                            borderRadius: '6px',
                                            overflow: 'auto',
                                            fontSize: '0.75rem',
                                            lineHeight: 1.5,
                                            margin: 0,
                                            whiteSpace: 'pre-wrap',
                                            wordBreak: 'break-word',
                                            maxHeight: '300px'
                                        }}>
                                            {graphMetadata.sparql_query}
                                        </pre>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
