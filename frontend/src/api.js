import axios from "axios";

const configuredOrigin = process.env.REACT_APP_API_URL || "";
export const API_BASE = configuredOrigin.replace(/\/$/, "");
export const backendConfigured =
  Boolean(configuredOrigin) || process.env.NODE_ENV === "development";
const AUTH_TOKEN_KEY = "scientia.session-token";
const api = axios.create({ baseURL: API_BASE, timeout: 120000 });
api.interceptors.request.use((config) => {
  if (!backendConfigured)
    throw new Error(
      "Connect a backend to use PDF analysis and AI tools. See Settings.",
    );
  const token = getAuthToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || "";
    if (
      error.response?.status === 401 &&
      !url.includes("/api/auth/login") &&
      !url.includes("/api/auth/register")
    ) {
      clearAuthToken();
      window.dispatchEvent(new Event("scientia:unauthorized"));
    }
    return Promise.reject(error);
  },
);
export function getAuthToken() {
  try {
    return sessionStorage.getItem(AUTH_TOKEN_KEY) || "";
  } catch {
    return "";
  }
}
export function setAuthToken(token) {
  try {
    sessionStorage.setItem(AUTH_TOKEN_KEY, token);
  } catch {
    throw new Error("Session storage is unavailable. Enable browser storage to sign in.");
  }
}
export function clearAuthToken() {
  try {
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
  } catch {
    // The in-memory app still drops its authenticated state.
  }
}
export async function authenticate(email, password, createAccount = false) {
  const { data } = await api.post(
    createAccount ? "/api/auth/register" : "/api/auth/login",
    { email, password },
  );
  setAuthToken(data.token);
  return data.user;
}
export async function signOut() {
  try {
    if (getAuthToken()) await api.post("/api/auth/logout");
  } finally {
    clearAuthToken();
  }
}
export function errorMessage(error) {
  return (
    error.response?.data?.error ||
    (error.code === "ERR_NETWORK"
      ? "Cannot reach the research API. Check the backend URL and its CORS settings."
      : error.message) ||
    "Something went wrong. Please retry."
  );
}
export async function healthCheck() {
  const { data } = await api.get("/api/health");
  if (!data || typeof data !== "object" || typeof data.mode !== "string") {
    throw new Error(
      "The free backend is starting. Wait a moment and check the connection again.",
    );
  }
  return data;
}
export async function uploadPaper(file, onProgress, signal) {
  if (!file || !/\.pdf$/i.test(file.name))
    throw new Error("Choose a PDF document.");
  if (file.size > 20 * 1024 * 1024)
    throw new Error("Please choose a PDF smaller than 20 MB.");
  const form = new FormData();
  form.append("file", file);
  const data = (await api.post("/api/upload/pdf?async=true", form, { signal }))
    .data;
  if (!data.job_id) return data;
  const deadline = Date.now() + 8 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    const job = (
      await api.get(`/api/jobs/${encodeURIComponent(data.job_id)}`, { signal })
    ).data.job;
    onProgress?.(job);
    if (job.status === "done") return job.result;
    if (job.status === "failed")
      throw new Error(job.error || "PDF processing failed.");
  }
  throw new Error(
    "Processing is taking longer than expected. Check your document library before uploading again.",
  );
}
export async function askQuestion(question, sessionId = "") {
  return (
    await api.post("/api/chat", {
      question,
      session_id: sessionId,
      agent: "rag",
    })
  ).data;
}
export async function getHistory(sessionId) {
  return (await api.get("/api/history", { params: { session_id: sessionId } }))
    .data;
}
export default api;
