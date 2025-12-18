import React, { useEffect, useState } from 'react';
import { X, Save, Trash2, RefreshCw, Pencil } from 'lucide-react';
import { kbApi } from '../services/api';

interface EntityListModalProps {
    isOpen: boolean;
    onClose: () => void;
    kbId: string;
}

interface Entity {
    name: string;
    label: string;
    count: number;
    aliases: string[];
    is_promoted: boolean;
}

export default function EntityListModal({ isOpen, onClose, kbId }: EntityListModalProps) {
    const [entities, setEntities] = useState<Entity[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    // Edit state
    const [editingName, setEditingName] = useState<string | null>(null);
    const [newName, setNewName] = useState('');

    const startEditing = (entity: Entity) => {
        setEditingName(entity.name);
        setNewName(entity.name);
    };

    const saveNameEdit = () => {
        if (!editingName || !newName.trim() || newName === editingName) {
            setEditingName(null);
            return;
        }

        // Update entities list: replace name
        setEntities(prev => prev.map(e =>
            e.name === editingName
                ? { ...e, name: newName.trim() }
                : e
        ));
        setEditingName(null);
    };

    useEffect(() => {
        if (isOpen && kbId) {
            loadEntities();
        }
    }, [isOpen, kbId]);

    const loadEntities = async () => {
        setIsLoading(true);
        try {
            const response = await kbApi.getEntities(kbId);
            // Sort by count desc
            const sorted = response.data.sort((a: Entity, b: Entity) => b.count - a.count);
            setEntities(sorted);
        } catch (error) {
            console.error(error);
            alert('Failed to load entities');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await kbApi.updateEntities(kbId, entities);
            alert('Saved successfully');
            onClose();
        } catch (error) {
            console.error(error);
            alert('Failed to save entities');
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = (name: string) => {
        if (confirm(`Delete entity "${name}"?`)) {
            setEntities(prev => prev.filter(e => e.name !== name));
        }
    };

    const togglePromoted = (name: string) => {
        setEntities(prev => prev.map(e =>
            e.name === name ? { ...e, is_promoted: !e.is_promoted } : e
        ));
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 50
        }} onClick={onClose}>
            <div className="card" style={{ width: '90%', maxWidth: '800px', height: '80vh', display: 'flex', flexDirection: 'column' }} onClick={(e) => e.stopPropagation()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h2 style={{ margin: 0 }}>Registered Entities (Gazetteer)</h2>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button className="btn" onClick={loadEntities} title="Refresh">
                            <RefreshCw size={20} />
                        </button>
                        <button className="btn" onClick={onClose}>
                            <X size={20} />
                        </button>
                    </div>
                </div>

                <div style={{ flex: 1, overflow: 'auto', border: '1px solid var(--border)', borderRadius: '4px' }}>
                    {isLoading ? (
                        <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>
                    ) : entities.length === 0 ? (
                        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>No entities found.</div>
                    ) : (
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead style={{ position: 'sticky', top: 0, backgroundColor: 'var(--surface)', zIndex: 1, borderBottom: '1px solid var(--border)' }}>
                                <tr>
                                    <th style={{ padding: '0.75rem', textAlign: 'left', backgroundColor: 'var(--surface)' }}>Name</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'left', backgroundColor: 'var(--surface)' }}>Type</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'center', backgroundColor: 'var(--surface)' }}>Count</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'center', backgroundColor: 'var(--surface)' }}>Promoted</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'right', backgroundColor: 'var(--surface)' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {entities.map((entity) => (
                                    <tr key={entity.name} style={{ borderBottom: '1px solid var(--border)' }}>
                                        <td style={{ padding: '0.75rem' }}>
                                            {editingName === entity.name ? (
                                                <input
                                                    autoFocus
                                                    type="text"
                                                    value={newName}
                                                    onChange={(e) => setNewName(e.target.value)}
                                                    onBlur={saveNameEdit}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') saveNameEdit();
                                                        if (e.key === 'Escape') setEditingName(null);
                                                    }}
                                                    style={{
                                                        width: '100%',
                                                        padding: '0.25rem',
                                                        border: '1px solid var(--primary)',
                                                        borderRadius: '4px'
                                                    }}
                                                />
                                            ) : (
                                                <div
                                                    style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}
                                                    onClick={() => startEditing(entity)}
                                                    title="Click to edit name"
                                                >
                                                    {entity.name}
                                                    <Pencil size={12} style={{ opacity: 0.3 }} />
                                                </div>
                                            )}
                                        </td>
                                        <td style={{ padding: '0.75rem' }}>
                                            <span className="badge badge-secondary">{entity.label}</span>
                                        </td>
                                        <td style={{ padding: '0.75rem', textAlign: 'center' }}>{entity.count}</td>
                                        <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                                            <input
                                                type="checkbox"
                                                checked={entity.is_promoted}
                                                onChange={() => togglePromoted(entity.name)}
                                            />
                                        </td>
                                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                                            <button
                                                className="btn"
                                                style={{ color: 'var(--error)', padding: '0.25rem' }}
                                                onClick={() => handleDelete(entity.name)}
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                    <button className="btn" onClick={onClose} disabled={isSaving}>Cancel</button>
                    <button
                        className="btn btn-primary"
                        onClick={handleSave}
                        disabled={isSaving || isLoading}
                        style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                    >
                        <Save size={18} />
                        {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </div>
        </div>
    );
}
