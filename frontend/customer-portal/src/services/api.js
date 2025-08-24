// API configuration and service functions for customer portal
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '/api' // Use relative URL in production (handled by ingress/proxy)
  : 'http://localhost:5000/api' // Local development

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    // Add auth token if available
    const token = localStorage.getItem('auth-token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        return await response.json()
      }
      
      return await response.text()
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  // Authentication
  async login(email, password) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async register(userData) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    })
  }

  async logout() {
    return this.request('/auth/logout', {
      method: 'POST',
    })
  }

  // Quotes
  async createQuote(quoteData) {
    return this.request('/quotes', {
      method: 'POST',
      body: JSON.stringify(quoteData),
    })
  }

  async getQuotes(filters = {}) {
    const params = new URLSearchParams(filters)
    return this.request(`/quotes?${params}`)
  }

  async getQuote(quoteId) {
    return this.request(`/quotes/${quoteId}`)
  }

  async acceptQuote(quoteId) {
    return this.request(`/quotes/${quoteId}/accept`, {
      method: 'POST',
    })
  }

  async downloadQuotePDF(quoteId) {
    const response = await fetch(`${this.baseURL}/quotes/${quoteId}/pdf`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('auth-token')}`,
      },
    })
    
    if (!response.ok) {
      throw new Error('Failed to download PDF')
    }
    
    return response.blob()
  }

  // Shipments
  async getShipments(filters = {}) {
    const params = new URLSearchParams(filters)
    return this.request(`/shipments?${params}`)
  }

  async getShipment(shipmentId) {
    return this.request(`/shipments/${shipmentId}`)
  }

  async trackShipment(trackingNumber) {
    return this.request(`/shipments/track/${trackingNumber}`)
  }

  // User Profile
  async getProfile() {
    return this.request('/users/profile')
  }

  async updateProfile(profileData) {
    return this.request('/users/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData),
    })
  }

  // Ports and locations
  async getPorts() {
    return this.request('/ports')
  }

  async getServiceTypes(mode) {
    return this.request(`/services?mode=${mode}`)
  }
}

export default new ApiService()

