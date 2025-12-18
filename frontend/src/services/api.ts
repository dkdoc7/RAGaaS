import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

export const kbApi = {
    list: () => api.get('/knowledge-bases/'),
    create: (data: { name: string; description: string; chunking_strategy: string; chunking_config: any; metric_type?: string; enable_graph_rag?: boolean }) => api.post('/knowledge-bases/', data),
    get: (id: string) => api.get(`/knowledge-bases/${id}`),
    delete: (id: string) => api.delete(`/knowledge-bases/${id}`),
    getEntities: (id: string) => api.get(`/knowledge-bases/${id}/entities`),
    updateEntities: (id: string, entities: any[]) => api.put(`/knowledge-bases/${id}/entities`, entities),
};

export const docApi = {
    list: (kbId: string) => api.get(`/knowledge-bases/${kbId}/documents`),
    upload: (kbId: string, file: File, config?: any) => {
        const formData = new FormData();
        formData.append('file', file);
        if (config) {
            formData.append('chunking_config', JSON.stringify(config));
        }
        return api.post(`/knowledge-bases/${kbId}/documents`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },
    delete: (kbId: string, docId: string) => api.delete(`/knowledge-bases/${kbId}/documents/${docId}`),
    getChunks: (kbId: string, docId: string) => api.get(`/knowledge-bases/${kbId}/documents/${docId}/chunks`),
    updateChunk: (kbId: string, docId: string, chunkId: string, content: string) => {
        const formData = new FormData();
        formData.append('content', content);
        return api.put(`/knowledge-bases/${kbId}/documents/${docId}/chunks/${chunkId}`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },
};

export const retrievalApi = {
    retrieve: (kbId: string, data: {
        query: string;
        top_k: number;
        score_threshold: number;
        strategy: string;
        use_reranker?: boolean;
        reranker_top_k?: number;
        reranker_threshold?: number;
        use_llm_reranker?: boolean;
        llm_chunk_strategy?: string;
        use_ner?: boolean;
        use_llm_keyword_extraction?: boolean;
        enable_graph_search?: boolean;
        graph_hops?: number;
        use_brute_force?: boolean;
        brute_force_top_k?: number;
        brute_force_threshold?: number;
    }) => api.post(`/knowledge-bases/${kbId}/retrieve`, data),
    chat: (kbId: string, data: {
        query: string;
        top_k?: number;
        score_threshold?: number;
        strategy?: string;
        use_reranker?: boolean;
        reranker_top_k?: number;
        reranker_threshold?: number;
        use_llm_reranker?: boolean;
        llm_chunk_strategy?: string;
        use_ner?: boolean;
        use_llm_keyword_extraction?: boolean;
        enable_graph_search?: boolean;
        graph_hops?: number;
        use_brute_force?: boolean;
        brute_force_top_k?: number;
        brute_force_threshold?: number;
    }) => api.post(`/knowledge-bases/${kbId}/chat`, data),
};

export default api;
