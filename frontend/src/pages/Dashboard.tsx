import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { kbApi } from '../services/api';
import { Plus, Database, Trash2, ArrowRight } from 'lucide-react';

interface KnowledgeBase {
    id: string;
    name: string;
    description: string;
    created_at: string;
}

export default function Dashboard() {
    const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [newKbName, setNewKbName] = useState('');
    const [newKbDesc, setNewKbDesc] = useState('');

    useEffect(() => {
        loadKbs();
    }, []);

    const loadKbs = async () => {
        try {
            const res = await kbApi.list();
            setKbs(res.data);
        } catch (err) {
            console.error(err);
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await kbApi.create({ name: newKbName, description: newKbDesc });
            setIsModalOpen(false);
            setNewKbName('');
            setNewKbDesc('');
            loadKbs();
        } catch (err) {
            console.error(err);
        }
    };

    const handleDelete = async (id: string, e: React.MouseEvent) => {
        e.preventDefault(); // Prevent navigation
        if (!confirm('Are you sure you want to delete this Knowledge Base?')) return;
        try {
            await kbApi.delete(id);
            loadKbs();
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className="container">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ fontSize: '1.875rem', fontWeight: 700, margin: 0 }}>Knowledge Bases</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Manage your RAG knowledge bases</p>
                </div>
                <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
                    <Plus size={20} />
                    Create Knowledge Base
                </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
                {kbs.map((kb) => (
                    <Link to={`/kb/${kb.id}`} key={kb.id} style={{ textDecoration: 'none', color: 'inherit' }}>
                        <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column', transition: 'transform 0.2s' }}>
                            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1rem' }}>
                                <div style={{ padding: '0.75rem', background: '#eff6ff', borderRadius: '8px', color: 'var(--primary)' }}>
                                    <Database size={24} />
                                </div>
                                <button
                                    className="btn"
                                    style={{ padding: '0.5rem', color: 'var(--text-secondary)' }}
                                    onClick={(e) => handleDelete(kb.id, e)}
                                >
                                    <Trash2 size={18} />
                                </button>
                            </div>
                            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.25rem' }}>{kb.name}</h3>
                            <p style={{ color: 'var(--text-secondary)', margin: 0, flex: 1, lineHeight: 1.5 }}>
                                {kb.description || 'No description'}
                            </p>
                            <div style={{ marginTop: '1.5rem', display: 'flex', alignItems: 'center', color: 'var(--primary)', fontWeight: 500, fontSize: '0.875rem' }}>
                                View Details <ArrowRight size={16} style={{ marginLeft: '0.5rem' }} />
                            </div>
                        </div>
                    </Link>
                ))}
            </div>

            {isModalOpen && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50
                }}>
                    <div className="card" style={{ width: '100%', maxWidth: '500px' }}>
                        <h2 style={{ marginTop: 0 }}>Create Knowledge Base</h2>
                        <form onSubmit={handleCreate}>
                            <div style={{ marginBottom: '1rem' }}>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Name</label>
                                <input
                                    className="input"
                                    value={newKbName}
                                    onChange={(e) => setNewKbName(e.target.value)}
                                    required
                                    placeholder="e.g. Product Manuals"
                                />
                            </div>
                            <div style={{ marginBottom: '1.5rem' }}>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Description</label>
                                <textarea
                                    className="input"
                                    value={newKbDesc}
                                    onChange={(e) => setNewKbDesc(e.target.value)}
                                    rows={3}
                                    placeholder="Optional description..."
                                />
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                                <button type="button" className="btn" onClick={() => setIsModalOpen(false)}>Cancel</button>
                                <button type="submit" className="btn btn-primary">Create</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
