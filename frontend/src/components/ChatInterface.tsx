import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { retrievalApi } from '../services/api';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    chunks?: any[];
}

interface ChatInterfaceProps {
    kbId: string;
    strategy: string;
    topK: number;
    scoreThreshold: number;
    useReranker: boolean;
    rerankerTopK: number;
    rerankerThreshold: number;
    useLLMReranker: boolean;
    llmChunkStrategy: string;
    useNER: boolean;
    enableGraphSearch: boolean;
    graphHops: number;
}

export default function ChatInterface({
    kbId,
    strategy,
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
}: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [currentChunks, setCurrentChunks] = useState<any[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMessage: Message = {
            role: 'user',
            content: input
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await retrievalApi.chat(kbId, {
                query: input,
                top_k: topK,
                score_threshold: scoreThreshold,
                strategy,
                use_reranker: useReranker,
                reranker_top_k: rerankerTopK,
                reranker_threshold: rerankerThreshold,
                use_llm_reranker: useLLMReranker,
                llm_chunk_strategy: llmChunkStrategy,
                use_ner: useNER,
                enable_graph_search: enableGraphSearch,
                graph_hops: graphHops
            });

            const assistantMessage: Message = {
                role: 'assistant',
                content: response.data.answer,
                chunks: response.data.chunks
            };

            setMessages(prev => [...prev, assistantMessage]);
            setCurrentChunks(response.data.chunks || []);
        } catch (error) {
            console.error('Chat error:', error);
            const errorMessage: Message = {
                role: 'assistant',
                content: 'Sorry, I encountered an error while processing your request.'
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '1rem' }}>
            {/* Chat Messages */}
            <div className="card" style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                minHeight: '400px',
                maxHeight: '600px'
            }}>
                <h3 style={{ margin: 0, marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                    Chat with Knowledge Base
                </h3>

                <div style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '1rem',
                    background: '#f9fafb',
                    borderRadius: '8px',
                    marginBottom: '1rem'
                }}>
                    {messages.length === 0 && (
                        <div style={{
                            textAlign: 'center',
                            color: 'var(--text-secondary)',
                            padding: '2rem',
                            fontSize: '0.875rem'
                        }}>
                            Start a conversation by asking a question about your documents.
                        </div>
                    )}

                    {messages.map((msg, idx) => (
                        <div
                            key={idx}
                            style={{
                                marginBottom: '1rem',
                                display: 'flex',
                                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
                            }}
                        >
                            <div
                                style={{
                                    maxWidth: '80%',
                                    padding: '0.75rem 1rem',
                                    borderRadius: '12px',
                                    background: msg.role === 'user' ? 'var(--primary)' : 'white',
                                    color: msg.role === 'user' ? 'white' : 'var(--text-primary)',
                                    boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word'
                                }}
                            >
                                {msg.content}
                            </div>
                        </div>
                    ))}

                    {isLoading && (
                        <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '1rem' }}>
                            <div style={{
                                padding: '0.75rem 1rem',
                                borderRadius: '12px',
                                background: 'white',
                                boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem'
                            }}>
                                <Loader2 size={16} className="spin" />
                                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                                    Thinking...
                                </span>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <textarea
                        className="input"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Ask a question..."
                        rows={2}
                        style={{ flex: 1, resize: 'none' }}
                        disabled={isLoading}
                    />
                    <button
                        className="btn btn-primary"
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        style={{
                            alignSelf: 'flex-end',
                            minWidth: '80px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        {isLoading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
                        Send
                    </button>
                </div>
            </div>

            {/* Retrieved Chunks */}
            {currentChunks.length > 0 && (
                <>
                    {/* Graph RAG Metadata */}
                    {currentChunks[0]?.graph_metadata && (
                        <div className="card" style={{ background: '#f0f9ff', borderLeft: '4px solid var(--primary)' }}>
                            <h4 style={{ margin: 0, marginBottom: '1rem', color: 'var(--primary)' }}>
                                🔍 Graph RAG Search Details
                            </h4>

                            {/* Extracted Entities */}
                            <div style={{ marginBottom: '1rem' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                                    Extracted Entities:
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                    {currentChunks[0].graph_metadata.extracted_entities.map((entity: string, idx: number) => (
                                        <span key={idx} className="badge badge-primary" style={{ fontSize: '0.75rem' }}>
                                            {entity}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            {/* Triples */}
                            {currentChunks[0].graph_metadata.triples && currentChunks[0].graph_metadata.triples.length > 0 && (
                                <div style={{ marginBottom: '1rem' }}>
                                    <div style={{ fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                                        Knowledge Graph Triples ({currentChunks[0].graph_metadata.triples.length}):
                                    </div>
                                    <div style={{
                                        maxHeight: '200px',
                                        overflowY: 'auto',
                                        background: 'white',
                                        padding: '0.75rem',
                                        borderRadius: '6px',
                                        fontSize: '0.8rem'
                                    }}>
                                        {currentChunks[0].graph_metadata.triples.map((triple: any, idx: number) => {
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
                                                    background: '#f9fafb',
                                                    borderRadius: '4px',
                                                    fontFamily: 'monospace'
                                                }}>
                                                    <span style={{ color: '#0ea5e9', fontWeight: 600 }}>{formatValue(triple.subject)}</span>
                                                    {' '}→{' '}
                                                    <span style={{ color: '#8b5cf6' }}>{formatValue(triple.predicate)}</span>
                                                    {' '}→{' '}
                                                    <span style={{ color: '#0ea5e9', fontWeight: 600 }}>{formatValue(triple.object)}</span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* SPARQL Query */}
                            <div>
                                <div style={{ fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                                    SPARQL Query:
                                </div>
                                <pre style={{
                                    background: 'white',
                                    padding: '0.75rem',
                                    borderRadius: '6px',
                                    overflow: 'auto',
                                    fontSize: '0.7rem',
                                    lineHeight: '1.4',
                                    margin: 0,
                                    maxHeight: '200px'
                                }}>
                                    {currentChunks[0].graph_metadata.sparql_query}
                                </pre>
                            </div>
                        </div>
                    )}

                    {/* Chunks List */}
                    <div className="card">
                        <h4 style={{ margin: 0, marginBottom: '1rem' }}>
                            Retrieved Chunks ({currentChunks.length})
                        </h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            {currentChunks.map((chunk, idx) => (
                                <div
                                    key={idx}
                                    style={{
                                        padding: '1rem',
                                        background: '#f9fafb',
                                        borderRadius: '8px',
                                        borderLeft: '3px solid var(--primary)'
                                    }}
                                >
                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        marginBottom: '0.5rem',
                                        fontSize: '0.75rem',
                                        color: 'var(--text-secondary)'
                                    }}>
                                        <span>Chunk {idx + 1}</span>
                                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                            {chunk.metadata?.source === 'graph' && (
                                                <span className="badge badge-primary" style={{ fontSize: '0.65rem' }}>
                                                    Graph
                                                </span>
                                            )}
                                            <span className="badge badge-primary" style={{ fontSize: '0.7rem' }}>
                                                Score: {chunk.score?.toFixed(3) || 'N/A'}
                                            </span>
                                        </div>
                                    </div>
                                    <div style={{
                                        fontSize: '0.875rem',
                                        lineHeight: '1.5',
                                        color: 'var(--text-primary)',
                                        maxHeight: '150px',
                                        overflowY: 'auto'
                                    }}>
                                        {chunk.content}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
