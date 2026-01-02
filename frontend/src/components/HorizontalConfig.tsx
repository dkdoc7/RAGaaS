import React from 'react';

interface HorizontalConfigProps {
    // Search Strategy
    searchStrategy: string;
    setSearchStrategy: (value: string) => void;

    // BM25 Settings
    bm25TopK: number;
    setBm25TopK: (value: number) => void;
    bm25Tokenizer: 'llm' | 'morpho';
    setBm25Tokenizer: (value: 'llm' | 'morpho') => void;
    useMultiPOS: boolean;
    setUseMultiPOS: (value: boolean) => void;

    // ANN Settings
    annTopK: number;
    setAnnTopK: (value: number) => void;
    annThreshold: number;
    setAnnThreshold: (value: number) => void;
    useParallelSearch?: boolean;
    setUseParallelSearch?: (value: boolean) => void;

    // Reranker
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

    // NER Filter
    useNER: boolean;
    setUseNER: (value: boolean) => void;

    // Graph/Ontology
    enableGraphSearch: boolean;
    setEnableGraphSearch: (value: boolean) => void;
    graphHops: number;
    setGraphHops: (value: number) => void;
    enableInverseSearch?: boolean;
    setEnableInverseSearch?: (value: boolean) => void;
    inverseExtractionMode?: 'always' | 'auto';
    setInverseExtractionMode?: (value: 'always' | 'auto') => void;

    // 2-Stage (Brute Force)
    bruteForceTopK: number;
    setBruteForceTopK: (value: number) => void;
    bruteForceThreshold: number;
    setBruteForceThreshold: (value: number) => void;

    // Graph Relation Filter (Neo4j only)
    useRelationFilter?: boolean;
    setUseRelationFilter?: (value: boolean) => void;

    // KB Info
    chunkingStrategy?: string;
    graphBackend?: string;
}

// Styles
const columnStyle: React.CSSProperties = {
    borderLeft: '1px solid var(--border)',
    paddingLeft: '1rem',
    maxWidth: '200px',
    boxSizing: 'border-box'
};

const labelStyle: React.CSSProperties = {
    fontSize: '0.85rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: '0.3rem',
    display: 'block'
};

const descStyle: React.CSSProperties = {
    fontSize: '0.8rem',
    color: 'var(--text-secondary)',
    marginTop: '0.2rem',
    lineHeight: 1.3,
    opacity: 0.9
};

export default function HorizontalConfig({
    searchStrategy,
    setSearchStrategy,
    bm25TopK,
    setBm25TopK,
    bm25Tokenizer,
    setBm25Tokenizer,
    useMultiPOS,
    setUseMultiPOS,
    annTopK,
    setAnnTopK,
    annThreshold,
    setAnnThreshold,
    useParallelSearch,
    setUseParallelSearch,
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
    setEnableGraphSearch,
    graphHops,
    setGraphHops,
    enableInverseSearch,
    setEnableInverseSearch,
    inverseExtractionMode,
    setInverseExtractionMode,
    bruteForceTopK,
    setBruteForceTopK,
    bruteForceThreshold,
    setBruteForceThreshold,
    useRelationFilter,
    setUseRelationFilter,
    chunkingStrategy: _chunkingStrategy,  // Reserved for future use
    graphBackend
}: HorizontalConfigProps) {

    // Determine available strategies based on RAG type
    const isGraphRAG = graphBackend === 'neo4j' || graphBackend === 'ontology';

    // Define strategy options
    const standardStrategies = [
        { value: 'ann', label: 'Vector (ANN)' },
        { value: 'keyword', label: 'Keyword (BM25)' },
        { value: 'hybrid', label: 'Hybrid (BM25→ANN)' },
        { value: '2-stage', label: '2 Stage (ANN→Brute Force)' }
    ];

    const graphStrategies = [
        { value: 'ann', label: 'Vector (ANN)' },
        { value: 'keyword', label: 'Keyword (BM25)' },
        { value: 'hybrid_graph', label: graphBackend === 'neo4j' ? 'Hybrid (Graph→ANN)' : 'Hybrid (Ontology→ANN)' }
    ];

    const strategies = isGraphRAG ? graphStrategies : standardStrategies;

    // Determine which sections to show
    const usesBM25 = searchStrategy === 'keyword' || searchStrategy === 'hybrid';
    const usesANN = searchStrategy === 'ann' || searchStrategy === 'hybrid' || searchStrategy === '2-stage' || searchStrategy === 'hybrid_graph';
    const usesGraph = searchStrategy === 'hybrid_graph';
    const uses2Stage = searchStrategy === '2-stage';
    const showReranker = !usesGraph;
    const showNER = !usesGraph;

    const handleStrategyChange = (newStrategy: string) => {
        setSearchStrategy(newStrategy);

        // Auto-configure based on strategy
        if (newStrategy === 'hybrid_graph') {
            setEnableGraphSearch(true);
        } else {
            setEnableGraphSearch(false);
        }
    };

    return (
        <div className="card" style={{ padding: '1rem' }}>
            <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.1rem', fontWeight: 600 }}>
                Search Configuration
            </h3>

            <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>

                {/* Column 1: Search Strategy (Radio Buttons) */}
                <div style={{ maxWidth: '240px' }}>
                    <label style={{ ...labelStyle, marginBottom: '0.2rem' }}>Search Strategy</label>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                        {strategies.map((s) => (
                            <label
                                key={s.value}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.4rem',
                                    fontSize: '0.85rem',
                                    cursor: 'pointer',
                                    padding: '0.15rem 0.4rem',
                                    borderRadius: '3px',
                                    backgroundColor: searchStrategy === s.value ? 'var(--bg-secondary)' : 'transparent',
                                    border: searchStrategy === s.value ? '1px solid var(--primary)' : '1px solid transparent',
                                    transition: 'all 0.15s'
                                }}
                            >
                                <input
                                    type="radio"
                                    name="searchStrategy"
                                    value={s.value}
                                    checked={searchStrategy === s.value}
                                    onChange={() => handleStrategyChange(s.value)}
                                    style={{ accentColor: 'var(--primary)' }}
                                />
                                {s.label}
                            </label>
                        ))}
                    </div>
                </div>

                {/* Column 2-0: Graph Settings (if Graph/Ontology) */}
                {usesGraph && (
                    <div style={columnStyle}>
                        <label style={labelStyle}>
                            {graphBackend === 'neo4j' ? 'Graph Settings' : 'Ontology Settings'}
                        </label>

                        <div style={{ marginTop: 0 }}>
                            <label style={{ fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem', color: 'var(--text-secondary)' }}>
                                <span>Graph Hops</span>
                                <span style={{ fontWeight: 600, color: graphHops >= 3 ? 'tomato' : 'inherit' }}>{graphHops}</span>
                            </label>
                            <input
                                type="range"
                                min="1"
                                max="5"
                                value={graphHops}
                                onChange={(e) => setGraphHops(Number(e.target.value))}
                                style={{ width: '100%', cursor: 'pointer' }}
                            />
                            {graphHops >= 3 && (
                                <p style={{ fontSize: '0.65rem', color: 'tomato', margin: '0.2rem 0' }}>
                                    ⚠️ High hops may slow search
                                </p>
                            )}
                        </div>

                        {/* Inverse Relations (Ontology only) */}
                        {graphBackend === 'ontology' && (
                            <div style={{ marginTop: '0.8rem', borderTop: '1px dashed var(--border)', paddingTop: '0.5rem' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}>
                                    <input
                                        type="checkbox"
                                        checked={enableInverseSearch || false}
                                        onChange={(e) => setEnableInverseSearch?.(e.target.checked)}
                                    />
                                    Inverse Relations
                                </label>
                                {enableInverseSearch && (
                                    <div style={{ paddingLeft: '1.2rem', marginTop: '0.3rem', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.8rem', cursor: 'pointer' }}>
                                            <input
                                                type="radio"
                                                checked={inverseExtractionMode === 'always'}
                                                onChange={() => setInverseExtractionMode?.('always')}
                                            />
                                            Always
                                        </label>
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.8rem', cursor: 'pointer' }}>
                                            <input
                                                type="radio"
                                                checked={inverseExtractionMode === 'auto'}
                                                onChange={() => setInverseExtractionMode?.('auto')}
                                            />
                                            Auto (LLM)
                                        </label>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Relation Filter (Neo4j only) */}
                        {graphBackend === 'neo4j' && (
                            <div style={{ marginTop: '0.8rem', borderTop: '1px dashed var(--border)', paddingTop: '0.5rem' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}>
                                    <input
                                        type="checkbox"
                                        checked={useRelationFilter ?? true}
                                        onChange={(e) => setUseRelationFilter?.(e.target.checked)}
                                    />
                                    Use Relation Filter
                                </label>
                                <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', margin: '0.3rem 0 0 1.4rem', lineHeight: 1.3 }}>
                                    {useRelationFilter ?? true
                                        ? 'Filter by relationship keywords'
                                        : 'Entity-only search (more results, less precise)'}
                                </p>
                            </div>
                        )}
                    </div>
                )}

                {/* Column 2-1: BM25 Settings */}
                {usesBM25 && (
                    <div style={{ ...columnStyle, maxWidth: '300px' }}>
                        <label style={labelStyle}>BM25 Settings</label>

                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                            {/* Left: Tokenizer Selection */}
                            <div style={{ flex: 1 }}>
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Tokenizer:</span>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', marginTop: '0.2rem', paddingLeft: '0.2rem' }}>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.8rem', cursor: 'pointer' }}>
                                        <input
                                            type="radio"
                                            checked={bm25Tokenizer === 'llm'}
                                            onChange={() => setBm25Tokenizer('llm')}
                                        />
                                        LLM <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>(gpt-oss)</span>
                                    </label>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.8rem', cursor: 'pointer' }}>
                                        <input
                                            type="radio"
                                            checked={bm25Tokenizer === 'morpho'}
                                            onChange={() => setBm25Tokenizer('morpho')}
                                        />
                                        Morpho <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>(Kiwi)</span>
                                    </label>

                                    {/* Multi-POS option (only for morpho) */}
                                    {bm25Tokenizer === 'morpho' && (
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.75rem', cursor: 'pointer', paddingLeft: '1rem' }}>
                                            <input
                                                type="checkbox"
                                                checked={useMultiPOS}
                                                onChange={(e) => setUseMultiPOS(e.target.checked)}
                                            />
                                            Multi-POS
                                            <span
                                                style={{
                                                    display: 'inline-flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    width: '12px',
                                                    height: '12px',
                                                    borderRadius: '50%',
                                                    backgroundColor: '#fff',
                                                    border: '1px solid #0ea5e9',
                                                    color: '#0ea5e9',
                                                    fontSize: '9px',
                                                    fontWeight: 700,
                                                    cursor: 'help',
                                                    position: 'relative'
                                                }}
                                                onMouseEnter={(e) => {
                                                    const tooltip = e.currentTarget.querySelector('.tooltip-text') as HTMLElement;
                                                    if (tooltip) tooltip.style.visibility = 'visible';
                                                }}
                                                onMouseLeave={(e) => {
                                                    const tooltip = e.currentTarget.querySelector('.tooltip-text') as HTMLElement;
                                                    if (tooltip) tooltip.style.visibility = 'hidden';
                                                }}
                                            >
                                                ?
                                                <span
                                                    className="tooltip-text"
                                                    style={{
                                                        visibility: 'hidden',
                                                        position: 'absolute',
                                                        bottom: '120%',
                                                        left: '50%',
                                                        transform: 'translateX(-50%)',
                                                        backgroundColor: '#1e293b',
                                                        color: '#fff',
                                                        padding: '5px 8px',
                                                        borderRadius: '4px',
                                                        fontSize: '10px',
                                                        whiteSpace: 'nowrap',
                                                        zIndex: 1000,
                                                        boxShadow: '0 2px 6px rgba(0,0,0,0.15)'
                                                    }}
                                                >
                                                    Extract verbs, adjectives
                                                </span>
                                            </span>
                                        </label>
                                    )}
                                </div>
                            </div>

                            {/* Right: Top K */}
                            <div style={{ width: '80px' }}>
                                <label style={{ fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                                    <span>Top K</span>
                                    <span>{bm25TopK}</span>
                                </label>
                                <input
                                    type="range"
                                    min="1"
                                    max="20"
                                    value={bm25TopK}
                                    onChange={(e) => setBm25TopK(Number(e.target.value))}
                                    style={{ width: '100%', cursor: 'pointer' }}
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Column 2-2: ANN Settings */}
                {usesANN && (
                    <div style={columnStyle}>
                        <label style={labelStyle}>ANN Settings</label>

                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <div style={{ flex: 1 }}>
                                <label style={{ fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                                    <span>Top K</span>
                                    <span>{annTopK}</span>
                                </label>
                                <input
                                    type="range"
                                    min="1"
                                    max="20"
                                    value={annTopK}
                                    onChange={(e) => setAnnTopK(Number(e.target.value))}
                                    style={{ width: '100%', cursor: 'pointer' }}
                                />
                            </div>
                            <div style={{ flex: 1 }}>
                                <label style={{ fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                                    <span>Threshold</span>
                                    <span>{annThreshold.toFixed(2)}</span>
                                </label>
                                <input
                                    type="range"
                                    min="0"
                                    max="1"
                                    step="0.01"
                                    value={annThreshold}
                                    onChange={(e) => setAnnThreshold(Number(e.target.value))}
                                    style={{ width: '100%', cursor: 'pointer' }}
                                />
                            </div>
                        </div>

                        {searchStrategy === 'hybrid' && useParallelSearch !== undefined && setUseParallelSearch && (
                            <div style={{ marginTop: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderTop: '1px dashed var(--border)', paddingTop: '0.5rem' }}>
                                <input
                                    type="checkbox"
                                    id="useParallelSearch"
                                    checked={useParallelSearch}
                                    onChange={(e) => setUseParallelSearch(e.target.checked)}
                                    style={{ cursor: 'pointer' }}
                                />
                                <label htmlFor="useParallelSearch" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                                    Search in Parallel (RRF)
                                </label>
                            </div>
                        )}
                    </div>
                )}

                {/* Column 2-3: Reranker */}
                {showReranker && (
                    <div style={columnStyle}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer' }}>
                            <input
                                type="checkbox"
                                checked={useReranker}
                                onChange={(e) => setUseReranker(e.target.checked)}
                            />
                            Reranker
                        </label>

                        <div style={{ opacity: useReranker ? 1 : 0.4, transition: 'opacity 0.2s', marginTop: '0.5rem' }}>
                            <div style={{ display: 'flex', gap: '1rem' }}>
                                <div style={{ flex: 1 }}>
                                    <label style={{ fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
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
                                    <label style={{ fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
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

                            <div style={{ marginTop: '0.5rem' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', cursor: useReranker ? 'pointer' : 'not-allowed' }}>
                                    <input
                                        type="checkbox"
                                        checked={useLLMReranker}
                                        onChange={(e) => setUseLLMReranker(e.target.checked)}
                                        disabled={!useReranker}
                                    />
                                    Use LLM Reranker
                                </label>

                                {useLLMReranker && useReranker && (
                                    <div style={{ marginTop: '0.3rem', paddingLeft: '1.2rem' }}>
                                        <select
                                            className="input"
                                            value={llmChunkStrategy}
                                            onChange={(e) => setLlmChunkStrategy(e.target.value)}
                                            style={{ fontSize: '0.8rem', padding: '0.2rem 0.4rem' }}
                                        >
                                            <option value="full">Full Context</option>
                                            <option value="limited">Limited Context</option>
                                            <option value="smart">Smart Selection</option>
                                        </select>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* Column 2-4: NER Filter */}
                {showNER && (
                    <div style={columnStyle}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer' }}>
                            <input
                                type="checkbox"
                                checked={useNER}
                                onChange={(e) => setUseNER(e.target.checked)}
                            />
                            NER Filter
                        </label>
                        <p style={descStyle}>
                            Penalizes results without query entities.
                        </p>
                    </div>
                )}

                {/* Column 2-5: 2-Stage (Brute Force) */}
                {uses2Stage && (
                    <div style={columnStyle}>
                        <label style={labelStyle}>Flat Index (L2)</label>
                        <p style={{ ...descStyle, marginBottom: '0.5rem' }}>
                            Exact nearest neighbor search using L2 distance
                        </p>

                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <div style={{ flex: 1 }}>
                                <label style={{ fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                                    <span>Top K</span>
                                    <span>{bruteForceTopK}</span>
                                </label>
                                <input
                                    type="range"
                                    min="1"
                                    max="5"
                                    value={bruteForceTopK}
                                    onChange={(e) => setBruteForceTopK(Number(e.target.value))}
                                    style={{ width: '100%', cursor: 'pointer' }}
                                />
                            </div>
                            <div style={{ flex: 1 }}>
                                <label style={{ fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
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
                                    style={{ width: '100%', cursor: 'pointer' }}
                                />
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
