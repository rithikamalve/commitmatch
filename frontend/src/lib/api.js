const BASE = import.meta.env.VITE_API_URL || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  // Requests
  getRequests:      ()         => request('/requests'),
  getRequest:       (id)       => request(`/requests/${id}`),
  confirmRequest:   (id, donorId) =>
    request(`/requests/${id}/confirm`, { method: 'POST', body: JSON.stringify({ donor_id: donorId }) }),

  // Match
  createMatch: (patientId, requiredDate, notes) =>
    request('/match', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, required_date: requiredDate, notes }),
    }),

  // Donors
  getDonors:    (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return request(`/donors${q ? '?' + q : ''}`)
  },
  getDonor:      (id)         => request(`/donors/${encodeURIComponent(id)}`),
  getDonorScore: (id)         => request(`/donors/${id}/score`),

  // Patients
  getPatients:  ()            => request('/patients'),
  getPatient:   (id)          => request(`/patients/${id}`),

  // Analytics
  getSupplyDemand:   () => request('/analytics/supply-demand'),
  getChurnRisk:      () => request('/analytics/churn-risk'),
  getShortageAlerts: () => request('/analytics/shortage-alerts'),
  getNetworkHealth:  () => request('/analytics/network-health'),
}
