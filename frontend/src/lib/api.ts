/**
 * API Client — communicates with FastAPI backend.
 * All requests include JWT token from localStorage.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

interface ApiOptions {
  method?: string;
  body?: any;
  token?: string;
}

async function apiRequest(endpoint: string, options: ApiOptions = {}) {
  const { method = "GET", body, token } = options;
  
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  
  // Get token from localStorage if not provided
  const authToken = token || (typeof window !== "undefined" ? localStorage.getItem("token") : null);
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  
  const res = await fetch(`${API_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  
  return res.json();
}

// ── Auth ──
export const auth = {
  register: (email: string, password: string, displayName?: string) =>
    apiRequest("/api/v1/auth/register", {
      method: "POST",
      body: { email, password, display_name: displayName },
    }),
  
  login: (email: string, password: string) =>
    apiRequest("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
    }),
  
  me: () => apiRequest("/api/v1/auth/me"),
};

// ── Projects ──
export const projects = {
  create: (data: {
    topic: string;
    script?: string;
    aspect_ratio?: string;
    voice_name?: string;
    bgm_mood?: string;
    video_source?: string;
  }) => apiRequest("/api/v1/projects", { method: "POST", body: data }),
  
  list: (limit = 20, offset = 0) =>
    apiRequest(`/api/v1/projects?limit=${limit}&offset=${offset}`),
  
  get: (id: string) => apiRequest(`/api/v1/projects/${id}`),
  
  delete: (id: string) =>
    apiRequest(`/api/v1/projects/${id}`, { method: "DELETE" }),
};

// ── Music ──
export const music = {
  byMood: (mood?: string, limit = 30) =>
    apiRequest(`/api/v1/music?${mood ? `mood=${mood}&` : ""}limit=${limit}`),
};

// ── Credits ──
export const credits = {
  history: (limit = 20) =>
    apiRequest(`/api/v1/credits/history?limit=${limit}`),
};

export default { auth, projects, music, credits };
