// API configuration and service functions for admin dashboard
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '/api' // Use relative URL in production (handled by ingress/proxy)
  : 'http://localhost:5000/api' // Local development

class AdminApiService {
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
    const token = localStorage.getItem('admin-auth-token')
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
  async login(email, password, role = 'admin') {
    return this.request('/admin/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password, role }),
    })
  }

  async logout() {
    return this.request('/admin/auth/logout', {
      method: 'POST',
    })
  }

  // Dashboard Analytics
  async getDashboardStats() {
    return this.request('/admin/dashboard/stats')
  }

  async getAnalytics(timeRange = '7d') {
    return this.request(`/admin/analytics?range=${timeRange}`)
  }

  // Quotes Management
  async getQuotes(filters = {}) {
    const params = new URLSearchParams(filters)
    return this.request(`/admin/quotes?${params}`)
  }

  async getQuote(quoteId) {
    return this.request(`/admin/quotes/${quoteId}`)
  }

  async updateQuote(quoteId, updateData) {
    return this.request(`/admin/quotes/${quoteId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData),
    })
  }

  async deleteQuote(quoteId) {
    return this.request(`/admin/quotes/${quoteId}`, {
      method: 'DELETE',
    })
  }

  // Shipments Management
  async getShipments(filters = {}) {
    const params = new URLSearchParams(filters)
    return this.request(`/admin/shipments?${params}`)
  }

  async getShipment(shipmentId) {
    return this.request(`/admin/shipments/${shipmentId}`)
  }

  async updateShipment(shipmentId, updateData) {
    return this.request(`/admin/shipments/${shipmentId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData),
    })
  }

  async addTrackingUpdate(shipmentId, updateData) {
    return this.request(`/admin/shipments/${shipmentId}/tracking`, {
      method: 'POST',
      body: JSON.stringify(updateData),
    })
  }

  // Customer Management
  async getCustomers(filters = {}) {
    const params = new URLSearchParams(filters)
    return this.request(`/admin/customers?${params}`)
  }

  async getCustomer(customerId) {
    return this.request(`/admin/customers/${customerId}`)
  }

  async updateCustomer(customerId, updateData) {
    return this.request(`/admin/customers/${customerId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData),
    })
  }

  async suspendCustomer(customerId) {
    return this.request(`/admin/customers/${customerId}/suspend`, {
      method: 'POST',
    })
  }

  // Vendor Management
  async getVendors(filters = {}) {
    const params = new URLSearchParams(filters)
    return this.request(`/admin/vendors?${params}`)
  }

  async getVendor(vendorId) {
    return this.request(`/admin/vendors/${vendorId}`)
  }

  async createVendor(vendorData) {
    return this.request('/admin/vendors', {
      method: 'POST',
      body: JSON.stringify(vendorData),
    })
  }

  async updateVendor(vendorId, updateData) {
    return this.request(`/admin/vendors/${vendorId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData),
    })
  }

  // User Management
  async getUsers(filters = {}) {
    const params = new URLSearchParams(filters)
    return this.request(`/admin/users?${params}`)
  }

  async createUser(userData) {
    return this.request('/admin/users', {
      method: 'POST',
      body: JSON.stringify(userData),
    })
  }

  async updateUser(userId, updateData) {
    return this.request(`/admin/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData),
    })
  }

  // System Settings
  async getSystemSettings() {
    return this.request('/admin/settings')
  }

  async updateSystemSettings(settings) {
    return this.request('/admin/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
  }

  // Reports and Exports
  async exportQuotes(filters = {}) {
    const params = new URLSearchParams(filters)
    const response = await fetch(`${this.baseURL}/admin/reports/quotes?${params}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('admin-auth-token')}`,
      },
    })
    
    if (!response.ok) {
      throw new Error('Failed to export quotes')
    }
    
    return response.blob()
  }

  async exportShipments(filters = {}) {
    const params = new URLSearchParams(filters)
    const response = await fetch(`${this.baseURL}/admin/reports/shipments?${params}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('admin-auth-token')}`,
      },
    })
    
    if (!response.ok) {
      throw new Error('Failed to export shipments')
    }
    
    return response.blob()
  }

  // Notifications
  async getNotifications() {
    return this.request('/admin/notifications')
  }

  async markNotificationRead(notificationId) {
    return this.request(`/admin/notifications/${notificationId}/read`, {
      method: 'POST',
    })
  }
}

export default new AdminApiService()

