import { useState } from 'react';
import { X, ChevronRight, ChevronDown, Loader2, Edit2, Check, XCircle } from 'lucide-react';
import { docApi } from '../services/api';

interface Chunk {
    chunk_id: string;
    content: string;
    metadata?: any;
    parent_id?: string;
    children?: Chunk[];
}

interface ChunksModalProps {
    isOpen: boolean;
    onClose: () => void;
    document: {
        id: string;
        filename: string;
    } | null;
    chunks: Chunk[];
    isLoading: boolean;
    kbId: string;
    onChunkUpdated: () => void;
}

export default function ChunksModal({ isOpen, onClose, document, chunks, isLoading, kbId, onChunkUpdated }: ChunksModalProps) {
    const [expandedParents, setExpandedParents] = useState<Record<string, boolean>>({});
    const [expandedChunks, setExpandedChunks] = useState<Record<number, boolean>>({});
    const [editingChunk, setEditingChunk] = useState<string | null>(null);
    const [editContent, setEditContent] = useState<string>('');
    const [isSaving, setIsSaving] = useState(false);

    if (!isOpen || !document) return null;

    // Group chunks by parent
    const parentChunks = chunks.filter(c => !c.parent_id);
    const childrenByParent = chunks.reduce((acc, chunk) => {
        if (chunk.parent_id) {
            if (!acc[chunk.parent_id]) acc[chunk.parent_id] = [];
            acc[chunk.parent_id].push(chunk);
        }
        return acc;
    }, {} as Record<string, Chunk[]>);

    const hasParentChild = parentChunks.length > 0 && Object.keys(childrenByParent).length > 0;

    const handleEditClick = (chunk: Chunk) => {
        setEditingChunk(chunk.chunk_id);
        setEditContent(chunk.content);
    };

    const handleCancelEdit = () => {
        setEditingChunk(null);
        setEditContent('');
    };

    const handleSaveEdit = async (chunkId: string) => {
        if (!editContent.trim()) return;

        setIsSaving(true);
        try {
            await docApi.updateChunk(kbId, document.id, chunkId, editContent);
            setEditingChunk(null);
            setEditContent('');
            onChunkUpdated(); // Refresh chunks
            alert('Chunk updated successfully!');
        } catch (error) {
            console.error('Failed to update chunk:', error);
            alert('Failed to update chunk');
        } finally {
            setIsSaving(false);
        }
    };

    const renderChunkContent = (chunk: Chunk, isExpanded: boolean) => {
        const isEditing = editingChunk === chunk.chunk_id;

        if (isEditing) {
            return (
                <div style={{ marginTop: '0.5rem' }}>
                    <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        className="input"
                        style={{
                            width: '100%',
                            minHeight: '150px',
                            fontSize: '0.875rem',
                            lineHeight: '1.5',
                            fontFamily: 'inherit',
                            resize: 'vertical'
                        }}
                        disabled={isSaving}
                    />
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                        <button
                            className="btn btn-primary"
                            onClick={() => handleSaveEdit(chunk.chunk_id)}
                            disabled={isSaving || !editContent.trim()}
                            style={{ fontSize: '0.75rem', padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                        >
                            {isSaving ? <Loader2 size={14} className="spin" /> : <Check size={14} />}
                            Save
                        </button>
                        <button
                            className="btn"
                            onClick={handleCancelEdit}
                            disabled={isSaving}
                            style={{ fontSize: '0.75rem', padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                        >
                            <XCircle size={14} />
                            Cancel
                        </button>
                    </div>
                </div>
            );
        }

        return (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
                <div style={{ flex: 1, fontSize: '0.875rem', lineHeight: '1.5', maxHeight: isExpanded ? 'none' : '4.5em', overflow: 'hidden' }}>
                    {chunk.content}
                </div>
                <button
                    className="btn"
                    onClick={() => handleEditClick(chunk)}
                    style={{
                        padding: '0.25rem',
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-secondary)',
                        flexShrink: 0
                    }}
                    title="Edit chunk"
                >
                    <Edit2 size={14} />
                </button>
            </div>
        );
    };

    return (
        <div
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0,0,0,0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 50
            }}
            onClick={onClose}
        >
            <div
                className="card"
                style={{
                    width: '90%',
                    maxWidth: '900px',
                    maxHeight: '90vh',
                    overflow: 'auto',
                    position: 'relative'
                }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                    <div>
                        <h2 style={{ margin: 0, fontSize: '1.5rem' }}>Document Chunks</h2>
                        <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                            {document.filename}
                        </p>
                    </div>
                    <button
                        className="btn"
                        onClick={onClose}
                        style={{ padding: '0.5rem' }}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                {isLoading ? (
                    <div style={{ padding: '2rem', textAlign: 'center' }}>
                        <Loader2 size={32} className="spin" style={{ margin: '0 auto' }} />
                        <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Loading chunks...</p>
                    </div>
                ) : chunks.length === 0 ? (
                    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                        No chunks found
                    </div>
                ) : hasParentChild ? (
                    // Parent-Child view
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {parentChunks.map((parent) => {
                            const children = childrenByParent[parent.chunk_id] || [];
                            const isExpanded = expandedParents[parent.chunk_id];

                            return (
                                <div key={parent.chunk_id} className="card" style={{ background: '#f9fafb' }}>
                                    <div
                                        onClick={() => setExpandedParents(prev => ({ ...prev, [parent.chunk_id]: !prev[parent.chunk_id] }))}
                                        style={{ cursor: 'pointer', display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}
                                    >
                                        {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                                                Parent Chunk • {children.length} children
                                            </div>
                                            {renderChunkContent(parent, isExpanded)}
                                        </div>
                                    </div>

                                    {isExpanded && children.length > 0 && (
                                        <div style={{ marginTop: '1rem', paddingLeft: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                            {children.map((child, idx) => (
                                                <div key={child.chunk_id} style={{ background: 'white', padding: '1rem', borderRadius: '8px', borderLeft: '3px solid var(--primary)' }}>
                                                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                                                        Child {idx + 1}
                                                    </div>
                                                    {renderChunkContent(child, true)}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    // Regular chunks view
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {chunks.map((chunk, idx) => {
                            const isExpanded = expandedChunks[idx];
                            return (
                                <div key={chunk.chunk_id} className="card" style={{ background: '#f9fafb' }}>
                                    <div
                                        onClick={() => !editingChunk && setExpandedChunks(prev => ({ ...prev, [idx]: !prev[idx] }))}
                                        style={{ cursor: editingChunk ? 'default' : 'pointer', display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}
                                    >
                                        {!editingChunk && (isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />)}
                                        {editingChunk && <div style={{ width: '20px' }} />}
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                                                Chunk {idx + 1}
                                            </div>
                                            {renderChunkContent(chunk, isExpanded)}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
