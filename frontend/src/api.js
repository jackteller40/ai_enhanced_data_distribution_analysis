// frontend/src/api.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const getAuthToken = () => {
  return localStorage.getItem('jwt_token');
};

const handleResponse = async (response) => {
  if (response.status === 204) return null; // No content — don't parse
  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('jwt_token');
      window.location.href = '/login';
    }
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Network response was not ok');
  }
  return response.json();
};

const fetchWithAuth = async (endpoint, options = {}) => {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  return handleResponse(response);
};

export const api = {
  // Auth
  login: (credentials) => fetchWithAuth('/login', { method: 'POST', body: JSON.stringify(credentials) }),
  signup: (userData) => fetchWithAuth('/signup', { method: 'POST', body: JSON.stringify(userData) }),
  deleteAccount: () => fetchWithAuth('/account', { method: 'DELETE' }), // no body, auth token identifies user

  // Profile
  updateProfile: (profileData) => fetchWithAuth('/profile', { method: 'PUT', body: JSON.stringify(profileData) }),
  getProfile: () => fetchWithAuth('/profile/me'),

  // Queue / Swipe
  getQueue: (matchType) => fetchWithAuth(`/queue?match_type=${encodeURIComponent(matchType)}`),
  likeSuggestion: (suggestionId) => fetchWithAuth(`/suggestions/${suggestionId}/like`, { method: 'POST' }),
  rejectSuggestion: (suggestionId) => fetchWithAuth(`/suggestions/${suggestionId}/reject`, { method: 'POST' }),

  // Conversations & Messages
  createConversation: (activeMatchId) => fetchWithAuth(`/conversations?active_match_id=${encodeURIComponent(activeMatchId)}`, { method: 'POST' }),
  getMessages: (conversationId) => fetchWithAuth(`/conversations/${conversationId}/messages`),
  sendMessage: (conversationId, messageData) => fetchWithAuth(`/conversations/${conversationId}/messages`, { method: 'POST', body: JSON.stringify(messageData) }),
  markRead: (conversationId) => fetchWithAuth(`/conversations/${conversationId}/read`, { method: 'POST' }),
  
  // Preferences (Updated names to perfectly match Profile.jsx)
  updateRomanticPreferences: (data) => fetchWithAuth('/preferences/romantic', { method: 'PUT', body: JSON.stringify(data) }),
  updateRoommatePreferences: (data) => fetchWithAuth('/preferences/roommate', { method: 'PUT', body: JSON.stringify(data) }),
};