import React from 'react';

interface HorizontalConfigProps {
    searchStrategy: string;
    setSearchStrategy: (value: string) => void;
    topK: number;
    setTopK: (value: number) => void;
    scoreThreshold: number;
    setScoreThreshold: (value: number) => void;
    useReranker: boolean;
    setUseReranker: (value: boolean) => void;
    rerankerTopK: number;
    setRerankerTopK: (value: number) => void;
    rerankerThreshold: number;
    setRerankerThreshold: (value: number) => void;
    useLLMReranker: boolean;
    setUseLLMReranker: (value: boolean) => void;
    llmChunkStrategy: string;
    setLlmChunkStrategy: (value: string) => void;
    useNER: boolean;
    setUseNER: (value: boolean) => void;
    enableGraphSearch: boolean;
    setEnableGraphSearch: (value: boolean) => void;
    graphHops: number;
    setGraphHops: (value: number) => void;
    useLLMKeywordExtraction: boolean;
    setUseLLMKeywordExtraction: (value: boolean) => void;
    enableGraphRag: boolean;
    useBruteForce: boolean;
    setUseBruteForce: (value: boolean) => void;
    bruteForceTopK: number;
    setBruteForceTopK: (value: number) => void;
    bruteForceThreshold: number;
    setBruteForceThreshold: (value: number) => void;
}

export default function HorizontalConfig({
    searchStrategy,
    setSearchStrategy,
    topK,
    setTopK,
    scoreThreshold,
    setScoreThreshold,
    useReranker,
    setUseReranker,
    rerankerTopK,
    setRerankerTopK,
    rerankerThreshold,
    setRerankerThreshold,
    useLLMReranker,
    setUseLLMReranker,
    llmChunkStrategy,
    setLlmChunkStrategy,
    useNER,
    setUseNER,
    enableGraphSearch,
    setEnableGraphSearch,
    graphHops,
    setGraphHops,
    useLLMKeywordExtraction,
    setUseLLMKeywordExtraction,
    enableGraphRag,
    useBruteForce,
    setUseBruteForce,
    bruteForceTopK,
    setBruteForceTopK,
    bruteForceThreshold,
    setBruteForceThreshold
}: HorizontalConfigProps) {
    return (
        <div className="card" style={{ padding: '1rem' }}>
            <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.1rem', fontWeight: 600 }}>Search Configuration</h3>

            <div style={{ display: 'grid', gridTemplateColumns: enableGraphRag ? '240px 260px 160px 240px 200px' : '240px 260px 160px 240px', gap: '3rem' }}>
                {/* Column 1: Core Search Settings */}
                <div>
                    <div style={{ marginBottom: '0.7rem' }}>
                        <label style={{ display: 'block', marginBottom: '3px', fontSize: '0.85rem', fontWeight: 600 }}>
                            Search Strategy
                        </label>
                        <select
                            className="input"
                            value={searchStrategy}
                            onChange={(e) => setSearchStrategy(e.target.value)}
                            style={{ width: '100%' }}
                        >
                            <option value="ann">Vector Search (ANN)</option>
                            <option value="keyword">Keyword Search (BM25)</option>
                        </select>
                        {searchStrategy === 'keyword' && (
                            <div style={{ marginTop: '5px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                                    <input
                                        type="checkbox"
                                        checked={useLLMKeywordExtraction}
                                        onChange={(e) => setUseLLMKeywordExtraction(e.target.checked)}
                                    />
                                    Extract Entity by LLM
                                </label>
                            </div>
                        )}
                    </div>

                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <div style={{ flex: 1 }}>
                            <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px', fontSize: '0.85rem', fontWeight: 600 }}>
                                <span>Top K</span>
                                <span>{topK}</span>
                            </label>
                            <input
                                type="range"
                                min="1"
                                max="20"
                                value={topK}
                                onChange={(e) => setTopK(Number(e.target.value))}
                                className="input"
                                style={{ width: '100%', padding: 0 }}
                            />
                        </div>

                        <div style={{ flex: 1 }}>
                            <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px', fontSize: '0.85rem', fontWeight: 600 }}>
                                <span>Threshold</span>
                                <span>{scoreThreshold.toFixed(2)}</span>
                            </label>
                            <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.05"
                                value={scoreThreshold}
                                onChange={(e) => setScoreThreshold(Number(e.target.value))}
                                className="input"
                                style={{ width: '100%', padding: 0 }}
                            />
                        </div>
                    </div>
                </div>

                {/* Column 2: Reranker Settings */}
                <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: '2rem' }}>
                    <div style={{ marginBottom: '0.5rem' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem' }}>
                            <input
                                type="checkbox"
                                checked={useReranker}
                                onChange={(e) => setUseReranker(e.target.checked)}
                            />
                            Use Reranker
                        </label>
                    </div>

                    <div style={{ paddingLeft: '0.5rem', opacity: useReranker ? 1 : 0.5, transition: 'opacity 0.2s' }}>
                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <div style={{ flex: 1 }}>
                                <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    <span>Top K</span>
                                    <span>{rerankerTopK}</span>
                                </label>
                                <input
                                    type="range"
                                    min="1"
                                    max="20"
                                    value={rerankerTopK}
                                    onChange={(e) => setRerankerTopK(Number(e.target.value))}
                                    disabled={!useReranker}
                                    style={{ width: '100%', cursor: useReranker ? 'pointer' : 'not-allowed' }}
                                />
                            </div>

                            <div style={{ flex: 1 }}>
                                <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    <span>Threshold</span>
                                    <span>{rerankerThreshold.toFixed(2)}</span>
                                </label>
                                <input
                                    type="range"
                                    min="0"
                                    max="1"
                                    step="0.05"
                                    value={rerankerThreshold}
                                    onChange={(e) => setRerankerThreshold(Number(e.target.value))}
                                    disabled={!useReranker}
                                    style={{ width: '100%', cursor: useReranker ? 'pointer' : 'not-allowed' }}
                                />
                            </div>
                        </div>

                        <div style={{ marginTop: '0.7rem' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: useReranker ? 'pointer' : 'not-allowed', fontWeight: 600, fontSize: '0.85rem' }}>
                                <input
                                    type="checkbox"
                                    checked={useLLMReranker}
                                    onChange={(e) => setUseLLMReranker(e.target.checked)}
                                    disabled={!useReranker}
                                />
                                Use LLM Reranker
                            </label>

                            <div style={{
                                marginTop: '0.5rem',
                                paddingLeft: '1.5rem',
                                opacity: useLLMReranker ? 1 : 0.5,
                                transition: 'opacity 0.2s'
                            }}>
                                <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)' }}>
                                    Chunk Strategy
                                </label>
                                <select
                                    className="input"
                                    value={llmChunkStrategy}
                                    onChange={(e) => setLlmChunkStrategy(e.target.value)}
                                    disabled={!useReranker || !useLLMReranker}
                                    style={{
                                        fontSize: '0.8rem',
                                        padding: '0.25rem',
                                        cursor: (useReranker && useLLMReranker) ? 'pointer' : 'not-allowed'
                                    }}
                                >
                                    <option value="full">Full Context</option>
                                    <option value="limited">Limited Context</option>
                                    <option value="smart">Smart Selection</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Column 3: NER Filter */}
                <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: '2rem' }}>
                    <div style={{ marginBottom: '1.2rem' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem' }}>
                            <input
                                type="checkbox"
                                checked={useNER}
                                onChange={(e) => setUseNER(e.target.checked)}
                            />
                            NER Filter
                        </label>
                        <p style={{ margin: '0.25rem 0 0 1.5rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            Penalizes results that don't contain entities found in the query
                        </p>
                    </div>
                </div>

                {/* Column 4: Brute Force */}
                <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: '2rem' }}>
                    <div style={{ marginBottom: '0.7rem' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem' }}>
                            <input
                                type="radio"
                                name="advancedMode"
                                checked={useBruteForce}
                                onClick={() => {
                                    if (useBruteForce) {
                                        setUseBruteForce(false);
                                    } else {
                                        setUseBruteForce(true);
                                        setEnableGraphSearch(false);
                                    }
                                }}
                                readOnly
                            />
                            Flat Index (L2)
                        </label>
                        <p style={{ margin: '0.25rem 0 0 1.5rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            Exact nearest neighbor search using L2 distance (Lower is better)
                        </p>
                    </div>

                    <div style={{ display: 'flex', gap: '1rem', opacity: useBruteForce ? 1 : 0.5, transition: 'opacity 0.2s' }}>
                        <div style={{ flex: 1 }}>
                            <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                <span>Top K</span>
                                <span>{bruteForceTopK}</span>
                            </label>
                            <input
                                type="range"
                                min="1"
                                max="3"
                                value={bruteForceTopK}
                                onChange={(e) => setBruteForceTopK(Number(e.target.value))}
                                disabled={!useBruteForce}
                                style={{ width: '100%', cursor: useBruteForce ? 'pointer' : 'not-allowed' }}
                            />
                        </div>

                        <div style={{ flex: 1 }}>
                            <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                <span>Threshold</span>
                                <span>{bruteForceThreshold.toFixed(2)}</span>
                            </label>
                            <input
                                type="range"
                                min="0"
                                max="2"
                                step="0.1"
                                value={bruteForceThreshold}
                                onChange={(e) => setBruteForceThreshold(Number(e.target.value))}
                                disabled={!useBruteForce}
                                style={{ width: '100%', cursor: useBruteForce ? 'pointer' : 'not-allowed' }}
                            />
                        </div>
                    </div>
                </div>

                {/* Column 4: Graph Search */}
                {enableGraphRag && (
                    <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: '2rem' }}>
                        <div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem' }}>
                                <input
                                    type="radio"
                                    name="advancedMode"
                                    checked={enableGraphSearch}
                                    onClick={() => {
                                        if (enableGraphSearch) {
                                            setEnableGraphSearch(false);
                                        } else {
                                            setEnableGraphSearch(true);
                                            setUseBruteForce(false);
                                        }
                                    }}
                                    readOnly
                                />
                                Use Graph Search
                            </label>
                            <p style={{ margin: '0.25rem 0 0 1.5rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                Augments retrieval with relationships from the knowledge graph
                            </p>

                            <div style={{ marginTop: '0.7rem', paddingLeft: '1.5rem', opacity: enableGraphSearch ? 1 : 0.5, transition: 'opacity 0.2s' }}>
                                <label style={{ fontSize: '0.8rem', fontWeight: 500, display: 'flex', justifyContent: 'space-between', marginBottom: '3px', color: 'var(--text-secondary)' }}>
                                    <span>Graph Hops</span>
                                    <span style={{
                                        fontWeight: 600,
                                        color: graphHops >= 4 ? 'tomato' : 'inherit'
                                    }}>
                                        {graphHops}
                                    </span>
                                </label>
                                <input
                                    type="range"
                                    min="1"
                                    max="5"
                                    step="1"
                                    value={graphHops}
                                    onChange={(e) => setGraphHops(Number(e.target.value))}
                                    disabled={!enableGraphSearch}
                                    style={{
                                        width: '100%',
                                        height: '6px',
                                        borderRadius: '3px',
                                        appearance: 'auto',
                                        background: 'linear-gradient(to right, #e2e8f0 0%, #e2e8f0 75%, tomato 75%, tomato 100%)',
                                        accentColor: graphHops >= 4 ? 'tomato' : undefined,
                                        cursor: enableGraphSearch ? 'pointer' : 'not-allowed'
                                    }}
                                />
                                {graphHops >= 3 && (
                                    <div style={{ fontSize: '0.7rem', color: 'tomato', marginTop: '0.25rem', lineHeight: '1.2' }}>
                                        ⚠️ Performance may degrade
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
