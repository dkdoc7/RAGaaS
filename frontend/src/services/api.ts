import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

export const kbApi = {
    list: () => api.get('/knowledge-bases/'),
    create: (data: { name: string; description: string; chunking_strategy: string; chunking_config: any }) => api.post('/knowledge-bases/', data),
    get: (id: string) => api.get(`/knowledge-bases/${id}`),
    delete: (id: string) => api.delete(`/knowledge-bases/${id}`),
};

export const docApi = {
    list: (kbId: string) => api.get(`/knowledge-bases/${kbId}/documents`),
    upload: (kbId: string, file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post(`/knowledge-bases/${kbId}/documents`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },
    delete: (kbId: string, docId: string) => api.delete(`/knowledge-bases/${kbId}/documents/${docId}`),
    getChunks: (kbId: string, docId: string) => api.get(`/knowledge-bases/${kbId}/documents/${docId}/chunks`),
};

export const retrievalApi = {
    retrieve: (kbId: string, data: { query: string; top_k: number; score_threshold: number; strategy: string }) =>
        api.post(`/knowledge-bases/${kbId}/retrieve`, data),
};

export default api;
