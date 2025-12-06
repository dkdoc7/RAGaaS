import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { kbApi } from '../services/api';
import { Plus, Database, Trash2, ArrowRight } from 'lucide-react';
import ConfirmDialog from '../components/ConfirmDialog';
import CreateKnowledgeBaseModal from '../components/CreateKnowledgeBaseModal';

interface KnowledgeBase {
    id: string;
    name: string;
    description: string;
    created_at: string;
}

export default function Dashboard() {
    const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const [deleteKbId, setDeleteKbId] = useState<string | null>(null);

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



    const handleDelete = (id: string, e: React.MouseEvent) => {
        e.preventDefault(); // Prevent navigation
        setDeleteKbId(id);
    };

    const confirmDeleteKb = async () => {
        if (!deleteKbId) return;
        try {
            await kbApi.delete(deleteKbId);
            loadKbs();
        } catch (err) {
            console.error(err);
        } finally {
            setDeleteKbId(null);
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

            <CreateKnowledgeBaseModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onCreateComplete={loadKbs}
            />

            <ConfirmDialog
                isOpen={!!deleteKbId}
                title="Delete Knowledge Base"
                message="Are you sure you want to delete this Knowledge Base? This action cannot be undone."
                onConfirm={confirmDeleteKb}
                onCancel={() => setDeleteKbId(null)}
                confirmText="Delete"
                isDestructive={true}
            />
        </div>
    );
}
