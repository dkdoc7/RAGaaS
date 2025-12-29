import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { kbApi, docApi } from '../services/api';
import { ArrowLeft } from 'lucide-react';
import clsx from 'clsx';

import DocumentsTab from '../components/DocumentsTab';
import ChatInterface from '../components/ChatInterface';
import ChunksModal from '../components/ChunksModal';
import HorizontalConfig from '../components/HorizontalConfig';
import SearchResults from '../components/SearchResults';
import ConfirmDialog from '../components/ConfirmDialog';
import EntityListModal from '../components/EntityListModal';


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
    const [useLLMKeywordExtraction, setUseLLMKeywordExtraction] = useState(false);
    const [enableGraphSearch, setEnableGraphSearch] = useState(false);
    const [graphHops, setGraphHops] = useState(2);

    // Brute Force State
    const [useBruteForce, setUseBruteForce] = useState(false);
    const [bruteForceTopK, setBruteForceTopK] = useState(1);
    const [bruteForceThreshold, setBruteForceThreshold] = useState(1.5);

    // Chat results state
    const [retrievedChunks, setRetrievedChunks] = useState<any[]>([]);

    // Chunk viewer state
    const [selectedDoc, setSelectedDoc] = useState<any>(null);
    const [chunks, setChunks] = useState<any[]>([]);
    const [isLoadingChunks, setIsLoadingChunks] = useState(false);

    // Delete confirmation modal state
    // Delete confirmation modal state
    // Delete confirmation modal state
    const [deleteDocId, setDeleteDocId] = useState<string | null>(null);
    const [showEntityModal, setShowEntityModal] = useState(false);


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
            console.log("WS Received:", event.data);
            const data = JSON.parse(event.data);
            if (data.type === 'document_status_update') {
                console.log("Updating doc status:", data);
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
                setSearchStrategy(settings.searchStrategy ?? 'ann');
                setTopK(settings.topK ?? 5);
                setScoreThreshold(settings.scoreThreshold ?? 0.5);
                setUseReranker(settings.useReranker ?? false);
                setRerankerTopK(settings.rerankerTopK ?? 5);
                setRerankerThreshold(settings.rerankerThreshold ?? 0.0);
                setUseLLMReranker(settings.useLLMReranker ?? false);
                setLlmChunkStrategy(settings.llmChunkStrategy ?? 'full');
                setUseNER(settings.useNER ?? false);
                setUseLLMKeywordExtraction(settings.useLLMKeywordExtraction ?? false);
                setEnableGraphSearch(settings.enableGraphSearch ?? false);
                setGraphHops(settings.graphHops ?? 2);
                setUseBruteForce(settings.useBruteForce ?? false);
                setBruteForceTopK(settings.bruteForceTopK ?? 1);
                setBruteForceThreshold(settings.bruteForceThreshold ?? 1.5);
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
            useLLMKeywordExtraction,
            enableGraphSearch,
            graphHops,
            useBruteForce,
            bruteForceTopK,
            bruteForceThreshold
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
        useLLMKeywordExtraction,
        enableGraphSearch,
        graphHops,
        useBruteForce,
        bruteForceTopK,
        bruteForceThreshold
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

    // Auto-refresh documents if any are processing
    useEffect(() => {
        const hasProcessing = documents.some(doc => doc.status === 'processing');
        if (hasProcessing) {
            const timer = setTimeout(() => {
                loadDocs();
            }, 3000);
            return () => clearTimeout(timer);
        }
    }, [documents]);

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
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '5px', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <Link to="/" className="btn btn-ghost" style={{ padding: '0.5rem', display: 'flex', alignItems: 'center' }}>
                    <ArrowLeft size={24} />
                </Link>

                <div style={{ display: 'flex', alignItems: 'baseline', gap: '1.5rem' }}>
                    <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700 }}>{kb.name}</h1>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                        <span>
                            Chunking: <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                                {kb.chunking_strategy === 'size' && 'Fixed Size'}
                                {kb.chunking_strategy === 'parent_child' && 'Parent-Child'}
                                {kb.chunking_strategy === 'context_aware' && 'Context Aware'}
                            </span>
                        </span>

                        {kb.graph_backend && kb.graph_backend !== 'none' && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span
                                    className="badge"
                                    style={{
                                        fontSize: '0.8rem',
                                        padding: '0.25rem 0.75rem',
                                        fontWeight: 600,
                                        backgroundColor: kb.graph_backend === 'ontology' ? '#1e40af' : '#166534',
                                        color: 'white'
                                    }}
                                >
                                    {kb.graph_backend === 'ontology' ? 'Ontology' : 'Neo4j'}
                                </span>
                                <button
                                    onClick={() => setShowEntityModal(true)}
                                    className="btn"
                                    style={{
                                        padding: '0.25rem 0.75rem',
                                        height: 'auto',
                                        fontSize: '0.8rem',
                                        color: 'white',
                                        backgroundColor: 'var(--primary)',
                                        border: 'none',
                                        borderRadius: '9999px'
                                    }}
                                    title="Manage Entities"
                                >
                                    Entities
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Config Summary Card removed as per design request */}.

            {/* Tabs */}
            <div className="tabs" style={{ marginBottom: '5px' }}>
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
                    Playground
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
                <div style={{ flex: 1, overflow: 'auto' }}>
                    <DocumentsTab
                        kbId={id!}
                        documents={documents}
                        onRefresh={loadDocs}
                        onDeleteDocument={(docId) => setDeleteDocId(docId)}
                        onViewChunks={handleViewChunks}
                    />
                </div>
            )}

            {activeTab === 'chat' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', flex: 1, minHeight: 0 }}>
                    {/* Top: Horizontal Configuration */}
                    <HorizontalConfig
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
                        useLLMKeywordExtraction={useLLMKeywordExtraction}
                        setUseLLMKeywordExtraction={setUseLLMKeywordExtraction}
                        enableGraphRag={kb.graph_backend !== 'none'}
                        useBruteForce={useBruteForce}
                        setUseBruteForce={setUseBruteForce}
                        bruteForceTopK={bruteForceTopK}
                        setBruteForceTopK={setBruteForceTopK}
                        bruteForceThreshold={bruteForceThreshold}
                        setBruteForceThreshold={setBruteForceThreshold}
                        graphBackend={kb.graph_backend}
                    />

                    {/* Bottom: Split View */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '5px', flex: 1, minHeight: 0 }}>
                        {/* Left: Chat */}
                        <div style={{ overflow: 'hidden', height: '100%', minHeight: 0 }}>
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
                                useLLMKeywordExtraction={useLLMKeywordExtraction}
                                enableGraphSearch={enableGraphSearch}
                                graphHops={graphHops}
                                useBruteForce={useBruteForce}
                                bruteForceTopK={bruteForceTopK}
                                bruteForceThreshold={bruteForceThreshold}
                                onChunksReceived={setRetrievedChunks}
                            />
                        </div>

                        {/* Right: Results */}
                        <div style={{ overflow: 'hidden', height: '100%', minHeight: 0 }}>
                            <SearchResults chunks={retrievedChunks} />
                        </div>
                    </div>
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

            <ConfirmDialog
                isOpen={deleteDocId !== null}
                onConfirm={confirmDelete}
                onCancel={() => setDeleteDocId(null)}
                title="Delete Document"
                message="Are you sure you want to delete this document? This action cannot be undone."
            />

            <EntityListModal
                isOpen={showEntityModal}
                onClose={() => setShowEntityModal(false)}
                kbId={id!}
            />
        </div>
    );
}
