import { createContext, useContext, useState, useCallback } from 'react'
import { useAuth } from './AuthContext'

const QuoteContext = createContext()

export const useQuote = () => {
  const context = useContext(QuoteContext)
  if (!context) {
    throw new Error('useQuote must be used within a QuoteProvider')
  }
  return context
}

export const QuoteProvider = ({ children }) => {
  const { token } = useAuth()
  const [quotes, setQuotes] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // API base URL - in production this would come from environment variables
  const API_BASE_URL = process.env.NODE_ENV === 'production' 
    ? '/api/v1' 
    : 'http://localhost:8101/api/v1'

  const createQuote = useCallback(async (quoteData) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_BASE_URL}/quotes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
          'Idempotency-Key': `quote-${Date.now()}-${Math.random()}`
        },
        body: JSON.stringify(quoteData)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const newQuote = await response.json()
      setQuotes(prev => [newQuote, ...prev])
      return { success: true, quote: newQuote }
    } catch (err) {
      console.error('Create quote error:', err)
      setError(err.message)
      return { success: false, error: err.message }
    } finally {
      setLoading(false)
    }
  }, [token, API_BASE_URL])

  const getQuotes = useCallback(async (filters = {}) => {
    setLoading(true)
    setError(null)
    
    try {
      const queryParams = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value) queryParams.append(key, value)
      })
      
      const response = await fetch(`${API_BASE_URL}/quotes?${queryParams}`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setQuotes(data.items || [])
      return { success: true, quotes: data.items || [], pagination: data.pagination }
    } catch (err) {
      console.error('Get quotes error:', err)
      setError(err.message)
      return { success: false, error: err.message }
    } finally {
      setLoading(false)
    }
  }, [token, API_BASE_URL])

  const getQuote = useCallback(async (quoteId) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_BASE_URL}/quotes/${quoteId}`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const quote = await response.json()
      return { success: true, quote }
    } catch (err) {
      console.error('Get quote error:', err)
      setError(err.message)
      return { success: false, error: err.message }
    } finally {
      setLoading(false)
    }
  }, [token, API_BASE_URL])

  const acceptQuote = useCallback(async (quoteId) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_BASE_URL}/quotes/${quoteId}/accept`, {
        method: 'PUT',
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const acceptedQuote = await response.json()
      
      // Update the quote in the local state
      setQuotes(prev => prev.map(quote => 
        quote.quote_id === quoteId ? acceptedQuote : quote
      ))
      
      return { success: true, quote: acceptedQuote }
    } catch (err) {
      console.error('Accept quote error:', err)
      setError(err.message)
      return { success: false, error: err.message }
    } finally {
      setLoading(false)
    }
  }, [token, API_BASE_URL])

  const downloadQuotePDF = useCallback(async (quoteId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/quotes/${quoteId}/pdf`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      // Open the download URL in a new tab
      window.open(data.download_url, '_blank')
      
      return { success: true, downloadUrl: data.download_url }
    } catch (err) {
      console.error('Download PDF error:', err)
      return { success: false, error: err.message }
    }
  }, [token, API_BASE_URL])

  // Mock data for development when API is not available
  const createMockQuote = useCallback((quoteData) => {
    const mockQuote = {
      quote_id: `Q-${Date.now().toString().slice(-8)}`,
      customer_id: 'CUST123',
      mode: quoteData.mode,
      service: quoteData.service,
      origin: quoteData.origin,
      destination: quoteData.destination,
      currency: 'USD',
      base_amount: Math.floor(Math.random() * 3000) + 1000,
      total_amount: Math.floor(Math.random() * 3500) + 1200,
      status: 'ISSUED',
      valid_until: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      issued_at: new Date().toISOString(),
      is_valid: true,
      is_expired: false,
      items: [
        {
          description: `${quoteData.service} freight from ${quoteData.origin} to ${quoteData.destination}`,
          unit_price: Math.floor(Math.random() * 2500) + 800,
          quantity: 1,
          total_price: Math.floor(Math.random() * 2500) + 800,
          item_type: 'BASE',
          currency: 'USD'
        }
      ]
    }
    
    setQuotes(prev => [mockQuote, ...prev])
    return { success: true, quote: mockQuote }
  }, [])

  const value = {
    quotes,
    loading,
    error,
    createQuote,
    getQuotes,
    getQuote,
    acceptQuote,
    downloadQuotePDF,
    createMockQuote,
    clearError: () => setError(null)
  }

  return (
    <QuoteContext.Provider value={value}>
      {children}
    </QuoteContext.Provider>
  )
}

