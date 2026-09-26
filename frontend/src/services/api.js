import axios from 'axios';

// Render.com da: VITE_API_URL = "https://medsim-backend.onrender.com"
// Lokal dev da: /api (Vite proxy orqali localhost:8000 ga yo'naltiriladi)
const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const api = axios.create({
  baseURL: API_BASE,
});

export const getMannequins = async () => {
  const response = await api.get('/mannequins').catch(() => ({ data: [] }));
  return response.data;
};

export const focusMannequin = async (slug) => {
  const response = await api.post('/focus', { slug });
  return response.data;
};

export const sendSpeech = async (audioBlob, mannequinSlug, sessionId) => {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'speech.webm');
  formData.append('mannequinSlug', mannequinSlug);
  if (sessionId) {
    formData.append('sessionId', sessionId);
  }

  const response = await api.post('/speech', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getScenarios = async (mannequinSlug) => {
  const response = await api.get(`/scenarios`, { params: { mannequinSlug } });
  return response.data;
};

export const createSession = async (data) => {
  const response = await api.post('/sessions', data);
  return response.data;
};

export const endSession = async (id) => {
  const response = await api.post(`/sessions/${id}/end`);
  return response.data;
};

export const getSessionLogs = async (id) => {
  const response = await api.get(`/sessions/${id}/logs`);
  return response.data;
};
