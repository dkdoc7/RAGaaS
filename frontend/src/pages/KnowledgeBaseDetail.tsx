import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { kbApi, docApi } from '../services/api';
import { ArrowLeft } from 'lucide-react';
import clsx from 'clsx';

import DocumentsTab from '../components/DocumentsTab';
import ChatInterface from '../components/ChatInterface';
import ChunksModal from '../components/ChunksModal';
import ConfigSidebar from '../components/ConfigSidebar';
import ConfirmDialog from '../components/ConfirmDialog';

export default function KnowledgeBaseDetail() {
    const { id } = useParams<{ id: string }>();
    const [kb, setKb] = useState<any>(null);
    const [activeTab, setActiveTab] = useState('documents');
    const [documents, setDocuments] = useState<any[]>([]);

    // Search Configuration State
    const [searchStrategy, setSearchStrategy] = useState('ann');
    const [topK, setTopK] = useState(5);
    const [scoreThreshold, setScoreThreshold] = useState(0.5);
    const [useReranker, setUseReranker] = useState(false);
    const [rerankerTopK, setRerankerTopK] = useState(5);
    const [rerankerThreshold, setRerankerThreshold] = useState(0.0);
    const [useLLMReranker, setUseLLMReranker] = useState(false);
    const [llmChunkStrategy, setLlmChunkStrategy] = useState('full');
    const [useNER, setUseNER] = useState(false);
    const [enableGraphSearch, setEnableGraphSearch] = useState(true);
    const [graphHops, setGraphHops] = useState(1);

    // Chunk viewer state
    const [selectedDoc, setSelectedDoc] = useState<any>(null);
    const [chunks, setChunks] = useState<any[]>([]);
    const [isLoadingChunks, setIsLoadingChunks] = useState(false);

    // Delete confirmation modal state
    const [deleteDocId, setDeleteDocId] = useState<string | null>(null);

    useEffect(() => {
        if (!id) return;

        loadKB();
        loadDocs();
        loadSettings();

        // WebSocket connection for real-time document status updates
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

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        return () => {
            ws.close();
        };
    }, [id]);

    const loadSettings = () => {
        try {
            const saved = localStorage.getItem('retrievalSettings');
            if (saved) {
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
                setEnableGraphSearch(settings.enableGraphSearch !== undefined ? settings.enableGraphSearch : true);
                setGraphHops(settings.graphHops || 1);
            }
        } catch (e) {
            console.error('Failed to load settings:', e);
        }
    };

    const saveSettings = () => {
        const settings = {
            searchStrategy,
            topK,
            scoreThreshold,
            useReranker,
            rerankerTopK,
            rerankerThreshold,
            useLLMReranker,
            llmChunkStrategy,
            useNER,
            enableGraphSearch,
            graphHops
        };
        localStorage.setItem('retrievalSettings', JSON.stringify(settings));
    };

    useEffect(() => {
        saveSettings();
    }, [
        searchStrategy,
        topK,
        scoreThreshold,
        useReranker,
        rerankerTopK,
        rerankerThreshold,
        useLLMReranker,
        llmChunkStrategy,
        useNER,
        enableGraphSearch,
        graphHops
    ]);

    const loadKB = async () => {
        try {
            const response = await kbApi.get(id!);
            setKb(response.data);
        } catch (error) {
            console.error('Failed to load KB:', error);
        }
    };

    const loadDocs = async () => {
        try {
            const response = await docApi.list(id!);
            setDocuments(response.data);
        } catch (error) {
            console.error('Failed to load documents:', error);
        }
    };

    const handleViewChunks = async (doc: any) => {
        setSelectedDoc(doc);
        setIsLoadingChunks(true);
        try {
            const response = await docApi.getChunks(id!, doc.id);
            setChunks(response.data.chunks || []);
        } catch (error) {
            console.error('Failed to load chunks:', error);
            alert('Failed to load chunks');
        } finally {
            setIsLoadingChunks(false);
        }
    };

    const confirmDelete = async () => {
        if (!deleteDocId) return;
        try {
            await docApi.delete(id!, deleteDocId);
            setDeleteDocId(null);
            loadDocs();
        } catch (error) {
            console.error('Failed to delete document:', error);
            alert('Failed to delete document');
        }
    };

    if (!kb) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <p>Loading...</p>
            </div>
        );
    }

    return (
        <div>
            {/* Header */}
            <div style={{ marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <Link to="/" className="btn" style={{ padding: '0.5rem' }}>
                    <ArrowLeft size={20} />
                </Link>
                <div style={{ flex: 1 }}>
                    <h1 style={{ margin: 0, marginBottom: '0.25rem' }}>{kb.name}</h1>
                    {kb.description && (
                        <p style={{ margin: 0, color: 'var(--text-secondary)' }}>{kb.description}</p>
                    )}
                </div>
            </div>

            {/* Config Summary Card */}
            <div className="card" style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
                    <div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Chunking Strategy</div>
                        <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                            {kb.chunking_strategy === 'size' && 'Fixed Size'}
                            {kb.chunking_strategy === 'parent_child' && 'Parent-Child'}
                            {kb.chunking_strategy === 'context_aware' && 'Context Aware'}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Similarity Metric</div>
                        <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                            {kb.metric_type === 'COSINE' ? 'Cosine (0-1)' : 'Inner Product'}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Graph RAG</div>
                        <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                            <span className={clsx('badge', kb.enable_graph_rag ? 'badge-success' : 'badge-secondary')} style={{ fontSize: '0.75rem' }}>
                                {kb.enable_graph_rag ? 'Enabled' : 'Disabled'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="tabs" style={{ marginBottom: '2rem' }}>
                <button
                    className={clsx('tab', activeTab === 'documents' && 'active')}
                    onClick={() => setActiveTab('documents')}
                >
                    Documents
                </button>
                <button
                    className={clsx('tab', activeTab === 'chat' && 'active')}
                    onClick={() => setActiveTab('chat')}
                >
                    Chat
                </button>
                <button
                    className={clsx('tab', activeTab === 'settings' && 'active')}
                    onClick={() => setActiveTab('settings')}
                >
                    Settings
                </button>
            </div>

            {/* Tab Content */}
            {activeTab === 'documents' && (
                <DocumentsTab
                    kbId={id!}
                    documents={documents}
                    onRefresh={loadDocs}
                    onDeleteDocument={(docId) => setDeleteDocId(docId)}
                    onViewChunks={handleViewChunks}
                />
            )}

            {activeTab === 'chat' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '2rem' }}>
                    <ChatInterface
                        kbId={id!}
                        strategy={searchStrategy}
                        topK={topK}
                        scoreThreshold={scoreThreshold}
                        useReranker={useReranker}
                        rerankerTopK={rerankerTopK}
                        rerankerThreshold={rerankerThreshold}
                        useLLMReranker={useLLMReranker}
                        llmChunkStrategy={llmChunkStrategy}
                        useNER={useNER}
                        enableGraphSearch={enableGraphSearch}
                        graphHops={graphHops}
                    />
                    <ConfigSidebar
                        searchStrategy={searchStrategy}
                        setSearchStrategy={setSearchStrategy}
                        topK={topK}
                        setTopK={setTopK}
                        scoreThreshold={scoreThreshold}
                        setScoreThreshold={setScoreThreshold}
                        useReranker={useReranker}
                        setUseReranker={setUseReranker}
                        rerankerTopK={rerankerTopK}
                        setRerankerTopK={setRerankerTopK}
                        rerankerThreshold={rerankerThreshold}
                        setRerankerThreshold={setRerankerThreshold}
                        useLLMReranker={useLLMReranker}
                        setUseLLMReranker={setUseLLMReranker}
                        llmChunkStrategy={llmChunkStrategy}
                        setLlmChunkStrategy={setLlmChunkStrategy}
                        useNER={useNER}
                        setUseNER={setUseNER}
                        enableGraphSearch={enableGraphSearch}
                        setEnableGraphSearch={setEnableGraphSearch}
                        graphHops={graphHops}
                        setGraphHops={setGraphHops}
                        enableGraphRag={kb.enable_graph_rag}
                    />
                </div>
            )}

            {activeTab === 'settings' && (
                <div className="card">
                    <h3>Knowledge Base Settings</h3>
                    <p>Settings implementation pending...</p>
                </div>
            )}

            {/* Chunks Modal */}
            <ChunksModal
                isOpen={selectedDoc !== null}
                onClose={() => setSelectedDoc(null)}
                document={selectedDoc}
                chunks={chunks}
                isLoading={isLoadingChunks}
                kbId={id!}
                onChunkUpdated={() => handleViewChunks(selectedDoc)}
            />

            {/* Delete Confirmation Dialog */}
            <ConfirmDialog
                isOpen={deleteDocId !== null}
                onConfirm={confirmDelete}
                onCancel={() => setDeleteDocId(null)}
                title="Delete Document"
                message="Are you sure you want to delete this document? This action cannot be undone."
            />
        </div>
    );
}
