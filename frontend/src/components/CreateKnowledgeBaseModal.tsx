import React, { useState } from 'react';
import { X, FileText, Settings, Check, Info } from 'lucide-react';
import { kbApi } from '../services/api';

interface CreateKnowledgeBaseModalProps {
    isOpen: boolean;
    onClose: () => void;
    onCreateComplete: () => void;
}

const LabelWithTooltip = ({ label, tooltip }: { label: string, tooltip: string }) => {
    const [show, setShow] = useState(false);

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <label style={{ fontSize: '0.875rem', fontWeight: 500 }}>{label}</label>
            <div
                style={{ position: 'relative', display: 'flex', alignItems: 'center' }}
                onMouseEnter={() => setShow(true)}
                onMouseLeave={() => setShow(false)}
            >
                <Info size={14} color="#9ca3af" style={{ cursor: 'help' }} />
                {show && (
                    <div style={{
                        width: '200px',
                        backgroundColor: '#333',
                        color: '#fff',
                        textAlign: 'center',
                        borderRadius: '6px',
                        padding: '0.5rem',
                        position: 'absolute',
                        zIndex: 10,
                        bottom: '125%',
                        left: '50%',
                        marginLeft: '-100px',
                        fontSize: '0.75rem',
                        fontWeight: 'normal',
                        pointerEvents: 'none',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
                    }}>
                        {tooltip}
                        <div style={{
                            content: '""',
                            position: 'absolute',
                            top: '100%',
                            left: '50%',
                            marginLeft: '-5px',
                            borderWidth: '5px',
                            borderStyle: 'solid',
                            borderColor: '#333 transparent transparent transparent'
                        }}></div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default function CreateKnowledgeBaseModal({ isOpen, onClose, onCreateComplete }: CreateKnowledgeBaseModalProps) {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [strategy, setStrategy] = useState('size');
    const [config, setConfig] = useState({
        chunk_size: 1000,
        overlap: 200,
        parent_size: 2000,
        child_size: 500,
        parent_overlap: 0,
        child_overlap: 100,
        h1: true,
        h2: true,
        h3: true,
        semantic_mode: false,
        buffer_size: 1,
        breakpoint_type: 'percentile',
        breakpoint_amount: 95
    });
    const [enableGraphRag, setEnableGraphRag] = useState(false);
    const [isCreating, setIsCreating] = useState(false);

    if (!isOpen) return null;

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsCreating(true);
        try {
            const payload: any = {
                name,
                description,
                chunking_strategy: strategy,
                chunking_config: config,
                enable_graph_rag: enableGraphRag
            };

            // Add graph_config if Graph RAG is enabled
            if (enableGraphRag) {
                payload.graph_config = {
                    max_hops: 2,
                    expansion_limit: 50,
                    normalization_method: "minmax",
                    merge_strategy: "weighted_sum",
                    enable_adaptive_weights: true,
                    adaptive_fallback_rules: {
                        min_graph_results: 3,
                        fallback_vector_weight: 0.9,
                        fallback_graph_weight: 0.1,
                        relation_keywords: ["관계", "연결", "사이"],
                        relation_vector_weight: 0.4,
                        relation_graph_weight: 0.6
                    }
                };
            }

            await kbApi.create(payload);
            onCreateComplete();
            onClose();
            // Reset form
            setName('');
            setDescription('');
            setStrategy('size');
            setEnableGraphRag(false);
        } catch (err) {
            console.error(err);
            alert('Failed to create Knowledge Base');
        } finally {
            setIsCreating(false);
        }
    };

    const strategies = [
        {
            id: 'size',
            name: 'Fixed Size',
            description: 'Chunks text into fixed-size segments with overlap.',
            icon: <FileText size={20} />
        },
        {
            id: 'parent_child',
            name: 'Parent-Child',
            description: 'Creates large parent chunks for context and small child chunks for retrieval.',
            icon: <Settings size={20} />
        },
        {
            id: 'context_aware',
            name: 'Context Aware',
            description: 'Splits text based on document structure (headers, markdown).',
            icon: <FileText size={20} />
        }
    ];

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 50
        }} onClick={onClose}>
            <div className="card" style={{ width: '100%', maxWidth: '600px', maxHeight: '90vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h2 style={{ margin: 0 }}>Create Knowledge Base</h2>
                    <button className="btn" onClick={onClose} style={{ padding: '0.5rem' }}>
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleCreate}>
                    <div style={{ marginBottom: '1rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Name</label>
                        <input
                            className="input"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                            placeholder="e.g. Product Manuals"
                        />
                    </div>
                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Description</label>
                        <textarea
                            className="input"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={3}
                            placeholder="Optional description..."
                        />
                    </div>

                    <div style={{ marginBottom: '1.5rem', border: '1px solid var(--border)', borderRadius: '8px', padding: '1rem', background: '#f8fafc' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                            <div>
                                <LabelWithTooltip
                                    label="Enable Graph RAG"
                                    tooltip="Uses knowledge graph for entity-based retrieval in addition to vector search"
                                />
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                                    Combines vector search with graph-based entity/relation extraction
                                </div>
                            </div>
                            <label style={{ position: 'relative', display: 'inline-block', width: '48px', height: '24px' }}>
                                <input
                                    type="checkbox"
                                    checked={enableGraphRag}
                                    onChange={(e) => setEnableGraphRag(e.target.checked)}
                                    style={{ opacity: 0, width: 0, height: 0 }}
                                />
                                <span style={{
                                    position: 'absolute',
                                    cursor: 'pointer',
                                    top: 0,
                                    left: 0,
                                    right: 0,
                                    bottom: 0,
                                    backgroundColor: enableGraphRag ? 'var(--primary)' : '#ccc',
                                    transition: '0.4s',
                                    borderRadius: '24px'
                                }}>
                                    <span style={{
                                        position: 'absolute',
                                        content: '""',
                                        height: '18px',
                                        width: '18px',
                                        left: enableGraphRag ? '26px' : '3px',
                                        bottom: '3px',
                                        backgroundColor: 'white',
                                        transition: '0.4s',
                                        borderRadius: '50%'
                                    }} />
                                </span>
                            </label>
                        </div>
                        {enableGraphRag && (
                            <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'white', borderRadius: '6px', fontSize: '0.875rem' }}>
                                <div style={{ color: 'var(--text-secondary)' }}>
                                    ℹ️ Graph RAG will extract entities and relationships from documents to enable contextual search.
                                    Default configuration will be used (customizable in Settings after creation).
                                </div>
                            </div>
                        )}
                    </div>

                    <div style={{ marginBottom: '2rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Chunking Strategy</label>
                        <div style={{ display: 'grid', gap: '1rem', marginBottom: '1.5rem' }}>
                            {strategies.map((s) => (
                                <div key={s.id}>
                                    <div
                                        onClick={() => setStrategy(s.id)}
                                        style={{
                                            border: strategy === s.id ? '2px solid var(--primary)' : '1px solid var(--border)',
                                            borderRadius: '8px',
                                            padding: '1rem',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'flex-start',
                                            gap: '1rem',
                                            background: strategy === s.id ? '#eff6ff' : 'white',
                                            transition: 'all 0.2s'
                                        }}
                                    >
                                        <div style={{
                                            color: strategy === s.id ? 'var(--primary)' : 'var(--text-secondary)',
                                            marginTop: '0.125rem'
                                        }}>
                                            {s.icon}
                                        </div>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{s.name}</div>
                                            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{s.description}</div>
                                        </div>
                                        {strategy === s.id && (
                                            <div style={{ color: 'var(--primary)' }}>
                                                <Check size={20} />
                                            </div>
                                        )}
                                    </div>

                                    {/* Inline Configuration Form */}
                                    {strategy === s.id && (
                                        <div style={{
                                            marginTop: '0.5rem',
                                            marginLeft: '1rem',
                                            padding: '1.5rem',
                                            background: '#f8fafc',
                                            borderRadius: '8px',
                                            border: '1px solid var(--border)',
                                            borderLeft: '4px solid var(--primary)'
                                        }}>
                                            <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', textTransform: 'uppercase', color: 'var(--text-secondary)', letterSpacing: '0.05em' }}>
                                                {s.name} Settings
                                            </h4>

                                            {s.id === 'size' && (
                                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                                    <div>
                                                        <LabelWithTooltip
                                                            label="Chunk Size"
                                                            tooltip="The maximum number of characters in each chunk."
                                                        />
                                                        <input
                                                            type="number"
                                                            className="input"
                                                            value={config.chunk_size}
                                                            onChange={(e) => setConfig({ ...config, chunk_size: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                    <div>
                                                        <LabelWithTooltip
                                                            label="Overlap"
                                                            tooltip="The number of characters to overlap between chunks to maintain context."
                                                        />
                                                        <input
                                                            type="number"
                                                            className="input"
                                                            value={config.overlap}
                                                            onChange={(e) => setConfig({ ...config, overlap: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                </div>
                                            )}

                                            {s.id === 'parent_child' && (
                                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                                    <div>
                                                        <LabelWithTooltip
                                                            label="Parent Chunk Size"
                                                            tooltip="Size of the larger parent chunks used for context retrieval."
                                                        />
                                                        <input
                                                            type="number"
                                                            className="input"
                                                            value={config.parent_size}
                                                            onChange={(e) => setConfig({ ...config, parent_size: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                    <div>
                                                        <LabelWithTooltip
                                                            label="Child Chunk Size"
                                                            tooltip="Size of the smaller child chunks used for precise matching."
                                                        />
                                                        <input
                                                            type="number"
                                                            className="input"
                                                            value={config.child_size}
                                                            onChange={(e) => setConfig({ ...config, child_size: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                    <div>
                                                        <LabelWithTooltip
                                                            label="Parent Overlap"
                                                            tooltip="Overlap for parent chunks."
                                                        />
                                                        <input
                                                            type="number"
                                                            className="input"
                                                            value={config.parent_overlap}
                                                            onChange={(e) => setConfig({ ...config, parent_overlap: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                    <div>
                                                        <LabelWithTooltip
                                                            label="Child Overlap"
                                                            tooltip="Overlap for child chunks."
                                                        />
                                                        <input
                                                            type="number"
                                                            className="input"
                                                            value={config.child_overlap}
                                                            onChange={(e) => setConfig({ ...config, child_overlap: parseInt(e.target.value) })}
                                                        />
                                                    </div>
                                                </div>
                                            )}

                                            {s.id === 'context_aware' && (
                                                <div>
                                                    <div style={{ marginBottom: '1rem', display: 'flex', gap: '1rem' }}>
                                                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                                            <input
                                                                type="radio"
                                                                name="context_mode"
                                                                checked={!config.semantic_mode}
                                                                onChange={() => setConfig({ ...config, semantic_mode: false })}
                                                            />
                                                            Split by Headers
                                                        </label>
                                                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                                            <input
                                                                type="radio"
                                                                name="context_mode"
                                                                checked={config.semantic_mode}
                                                                onChange={() => setConfig({ ...config, semantic_mode: true })}
                                                            />
                                                            Semantic Split (LLM)
                                                        </label>
                                                    </div>

                                                    {!config.semantic_mode ? (
                                                        <div>
                                                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Header Levels</label>
                                                            <div style={{ display: 'flex', gap: '1.5rem' }}>
                                                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={config.h1}
                                                                        onChange={(e) => setConfig({ ...config, h1: e.target.checked })}
                                                                    />
                                                                    H1 (#)
                                                                </label>
                                                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={config.h2}
                                                                        onChange={(e) => setConfig({ ...config, h2: e.target.checked })}
                                                                    />
                                                                    H2 (##)
                                                                </label>
                                                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={config.h3}
                                                                        onChange={(e) => setConfig({ ...config, h3: e.target.checked })}
                                                                    />
                                                                    H3 (###)
                                                                </label>
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                                            <div>
                                                                <LabelWithTooltip
                                                                    label="Buffer Size"
                                                                    tooltip="Number of sentences to group together for comparison. Larger buffer reduces noise."
                                                                />
                                                                <input
                                                                    type="number"
                                                                    className="input"
                                                                    value={config.buffer_size}
                                                                    onChange={(e) => setConfig({ ...config, buffer_size: parseInt(e.target.value) })}
                                                                />
                                                            </div>
                                                            <div>
                                                                <LabelWithTooltip
                                                                    label="Threshold Type"
                                                                    tooltip="Method to determine the split point based on semantic similarity."
                                                                />
                                                                <select
                                                                    className="input"
                                                                    value={config.breakpoint_type}
                                                                    onChange={(e) => setConfig({ ...config, breakpoint_type: e.target.value })}
                                                                >
                                                                    <option value="percentile">Percentile</option>
                                                                    <option value="standard_deviation">Standard Deviation</option>
                                                                    <option value="interquartile">Interquartile</option>
                                                                </select>
                                                            </div>
                                                            <div>
                                                                <LabelWithTooltip
                                                                    label="Threshold Amount"
                                                                    tooltip="Sensitivity of the split. Higher values create smaller, more granular chunks."
                                                                />
                                                                <input
                                                                    type="number"
                                                                    className="input"
                                                                    value={config.breakpoint_amount}
                                                                    onChange={(e) => setConfig({ ...config, breakpoint_amount: parseFloat(e.target.value) })}
                                                                />
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                        <button type="button" className="btn" onClick={onClose} disabled={isCreating}>Cancel</button>
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={!name || isCreating}
                        >
                            {isCreating ? 'Creating...' : 'Create'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
