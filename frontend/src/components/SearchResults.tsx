import React from 'react';

interface SearchResultsProps {
    chunks: any[];
}

export default function SearchResults({ chunks }: SearchResultsProps) {
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

    const topChunk = chunks[0];
    const graphMetadata = topChunk?.graph_metadata;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', height: '100%' }}>
            {/* Graph RAG Metadata */}
            {graphMetadata && (
                <div className="card" style={{ background: '#f0f9ff', borderLeft: '4px solid var(--primary)' }}>
                    <h4 style={{ margin: 0, marginBottom: '1rem', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        🔍 Graph RAG Search Details
                    </h4>

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
                                    const formatValue = (val: string) => {
                                        try {
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
                                            <span style={{ color: '#0284c7', fontWeight: 600 }}>{formatValue(triple.subject)}</span>
                                            <span style={{ color: '#94a3b8' }}>→</span>
                                            <span style={{ color: '#7c3aed' }}>{formatValue(triple.predicate)}</span>
                                            <span style={{ color: '#94a3b8' }}>→</span>
                                            <span style={{ color: '#0284c7', fontWeight: 600 }}>{formatValue(triple.object)}</span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* SPARQL Query */}
                    <div>
                        <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                            SPARQL Query:
                        </div>
                        <pre style={{
                            background: 'white',
                            padding: '1rem',
                            borderRadius: '6px',
                            overflow: 'auto',
                            fontSize: '0.75rem',
                            lineHeight: '1.5',
                            margin: 0,
                            maxHeight: '200px',
                            border: '1px solid #e0f2fe',
                            color: '#334155'
                        }}>
                            {graphMetadata.sparql_query}
                        </pre>
                    </div>
                </div>
            )}

            {/* Chunks List */}
            <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '300px' }}>
                <h4 style={{ margin: 0, marginBottom: '1rem', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)' }}>
                    Retrieved Chunks ({chunks.length})
                </h4>
                <div style={{ flex: 1, overflowY: 'auto', paddingRight: '0.5rem' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {chunks.map((chunk, idx) => (
                            <div
                                key={idx}
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
                                    <span style={{ fontWeight: 600 }}>Chunk {idx + 1}</span>
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
                </div>
            </div>
        </div>
    );
}
