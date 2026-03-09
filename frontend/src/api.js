/**
 * API client for AI Research Assistant backend.
 * Base URL defaults to same origin (proxy in dev) or env REACT_APP_API_URL.
 */

import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || '';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000, // 2 min for upload + processing
});

/**
 * Health check
 */
export async function healthCheck() {
  const { data } = await api.get('/health');
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
  const { data } = await api.post('/upload', formData, {
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
  const { data } = await api.post('/ask', { question, session_id: sessionId });
  return data;
}

/**
 * Get conversation history for a session
 * @param {string} sessionId
 */
export async function getHistory(sessionId) {
  const { data } = await api.get('/history', { params: { session_id: sessionId } });
  return data;
}

export default api;
