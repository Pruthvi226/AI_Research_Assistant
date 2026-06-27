/**
 * API client for AI Research Assistant backend.
 * Base URL defaults to same origin (proxy in dev) or env REACT_APP_API_URL.
 */

import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || '';
const API_TIMEOUT_MS = 300000;
const ADMIN_API_KEY = process.env.REACT_APP_ADMIN_API_KEY || '';

axios.defaults.baseURL = API_BASE;
axios.defaults.timeout = API_TIMEOUT_MS;
if (ADMIN_API_KEY) {
  axios.defaults.headers.common['X-Admin-Key'] = ADMIN_API_KEY;
  document.cookie = `scientia_admin=${encodeURIComponent(ADMIN_API_KEY)}; SameSite=Strict; Path=/`;
}

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
    ...(ADMIN_API_KEY ? { 'X-Admin-Key': ADMIN_API_KEY } : {}),
  },
  timeout: API_TIMEOUT_MS, // uploads and paper analysis can be long-running
});

/**
 * Health check
 */
export async function healthCheck() {
  const { data } = await api.get('/api/health');
  return data;
}

/**
 * Upload PDF and get summary + insights
 * @param {File} file - PDF file
 * @returns {Promise<UploadResponse>}
 */
export async function uploadPaper(file) {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/api/upload/pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

/**
 * Ask a question about the uploaded paper
 * @param {string} question
 * @param {string} [sessionId]
 */
export async function askQuestion(question, sessionId = '') {
  const { data } = await api.post('/api/chat', { question, session_id: sessionId });
  return data;
}

/**
 * Get conversation history for a session
 * @param {string} sessionId
 */
export async function getHistory(sessionId) {
  const { data } = await api.get('/api/history', { params: { session_id: sessionId } });
  return data;
}

export default api;
