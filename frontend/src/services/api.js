const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function getAuthToken() {
  return localStorage.getItem('minepulse_token');
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('minepulse_token', token);
  } else {
    localStorage.removeItem('minepulse_token');
  }
}

export function getCurrentUser() {
  const userJson = localStorage.getItem('minepulse_user');
  if (userJson) {
    try {
      return JSON.parse(userJson);
    } catch (e) {
      return null;
    }
  }
  return null;
}

export function setCurrentUser(user) {
  if (user) {
    localStorage.setItem('minepulse_user', JSON.stringify(user));
  } else {
    localStorage.removeItem('minepulse_user');
  }
}

async function request(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Unauthorized / Expired Token
    setAuthToken(null);
    setCurrentUser(null);
  }

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || data.message || 'API request failed');
  }
  return data;
}

export const api = {
  // Auth API
  login: async (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/api/v1/auth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Invalid username or password');
    }

    setAuthToken(data.access_token);
    setCurrentUser(data.user);
    return data;
  },

  logout: () => {
    setAuthToken(null);
    setCurrentUser(null);
  },

  getMe: () => request('/api/v1/auth/me'),

  // Predictions & Core REST APIs
  getSnapshotSummary: () => request('/api/v1/snapshot/summary'),
  getFailureRiskPredictions: () => request('/api/v1/predict/failure-risk'),
  getDemandForecasts: (horizonDays = 30) => request(`/api/v1/forecast/demand?horizon_days=${horizonDays}`),
  getRecommendations: () => request('/api/v1/recommendations/inventory'),
  applyDispatcherOverride: (overrideData) => request('/api/v1/recommendations/override', {
    method: 'POST',
    body: JSON.stringify(overrideData),
  }),
  getAuditLogs: () => request('/api/v1/audit/logs'),

  // Model Monitoring & Retraining
  getMonitoringSummary: () => request('/api/v1/monitoring/summary'),
  getDriftAnalysis: () => request('/api/v1/monitoring/drift'),
  triggerRetraining: (triggerData = { force: true, reason: 'Manual trigger from Dashboard' }) =>
    request('/api/v1/monitoring/trigger-retrain', {
      method: 'POST',
      body: JSON.stringify(triggerData),
    }),
};
