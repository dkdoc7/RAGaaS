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
    useLLMKeywordExtraction?: boolean;
    enableGraphSearch: boolean;
    graphHops: number;
    useBruteForce?: boolean;
    bruteForceTopK?: number;
    bruteForceThreshold?: number;
    onChunksReceived: (chunks: any[]) => void;
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
    useLLMKeywordExtraction,
    enableGraphSearch,
    graphHops,
    useBruteForce,
    bruteForceTopK,
    bruteForceThreshold,
    onChunksReceived
}: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
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

        // Clear previous search results
        onChunksReceived([]);

        try {
            // Auto-switch to hybrid strategy when graph search is enabled
            // When disabled, use selected strategy (but fallback to 'ann' if it's 'graph')
            let effectiveStrategy = strategy;
            if (enableGraphSearch) {
                effectiveStrategy = 'hybrid';
            } else if (strategy === 'graph') {
                // If graph search is off but strategy is 'graph', use 'ann' instead
                effectiveStrategy = 'ann';
            }

            console.log('[ChatInterface] Sending request with:', {
                strategy: effectiveStrategy,
                enable_graph_search: enableGraphSearch,
                graph_hops: graphHops
            });

            const response = await retrievalApi.chat(kbId, {
                query: input,
                top_k: topK,
                score_threshold: scoreThreshold,
                strategy: effectiveStrategy,
                use_reranker: useReranker,
                reranker_top_k: rerankerTopK,
                reranker_threshold: rerankerThreshold,
                use_llm_reranker: useLLMReranker,
                llm_chunk_strategy: llmChunkStrategy,
                use_ner: useNER,
                use_llm_keyword_extraction: useLLMKeywordExtraction,
                enable_graph_search: enableGraphSearch,
                graph_hops: graphHops,
                use_brute_force: useBruteForce,
                brute_force_top_k: bruteForceTopK,
                brute_force_threshold: bruteForceThreshold
            });

            const assistantMessage: Message = {
                role: 'assistant',
                content: response.data.answer,
                chunks: response.data.chunks
            };

            setMessages(prev => [...prev, assistantMessage]);
            if (response.data.chunks) {
                onChunksReceived(response.data.chunks);
            }
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
        <div className="card" style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            border: '1px solid var(--border)',
            borderRadius: '12px'
        }}>
            <h3 style={{ margin: 0, padding: '5px', borderBottom: '1px solid var(--border)' }}>
                Chat with Knowledge Base
            </h3>

            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '1rem',
                background: '#f9fafb'
            }}>
                {messages.length === 0 && (
                    <div style={{
                        textAlign: 'center',
                        color: 'var(--text-secondary)',
                        padding: '2rem',
                        fontSize: '0.9rem',
                        marginTop: '20%'
                    }}>
                        <div style={{ marginBottom: '1rem', fontSize: '2rem' }}>💬</div>
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
                                maxWidth: '85%',
                                padding: '0.75rem 1rem',
                                borderRadius: '12px',
                                background: msg.role === 'user' ? 'var(--primary)' : 'white',
                                color: msg.role === 'user' ? 'white' : 'var(--text-primary)',
                                boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                                border: msg.role === 'assistant' ? '1px solid var(--border)' : 'none'
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
                            border: '1px solid var(--border)',
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

            <div style={{ padding: '1rem', borderTop: '1px solid var(--border)', background: 'white', borderBottomLeftRadius: '12px', borderBottomRightRadius: '12px' }}>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <textarea
                        className="input"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Ask a question..."
                        rows={1}
                        style={{
                            flex: 1,
                            resize: 'none',
                            padding: '0.75rem',
                            minHeight: '45px',
                            maxHeight: '150px'
                        }}
                        disabled={isLoading}
                    />
                    <button
                        className="btn btn-primary"
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        style={{
                            alignSelf: 'flex-end',
                            height: '45px',
                            padding: '0 1.5rem'
                        }}
                    >
                        {isLoading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
                        Send
                    </button>
                </div>
            </div>
        </div>
    );
}
