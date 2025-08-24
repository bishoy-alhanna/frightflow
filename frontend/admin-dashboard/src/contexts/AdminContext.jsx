import { createContext, useContext, useState, useEffect } from 'react'

const AdminContext = createContext({})

export const useAdmin = () => {
  const context = useContext(AdminContext)
  if (!context) {
    throw new Error('useAdmin must be used within an AdminProvider')
  }
  return context
}

export const AdminProvider = ({ children }) => {
  const [quotes, setQuotes] = useState([])
  const [shipments, setShipments] = useState([])
  const [customers, setCustomers] = useState([])
  const [vendors, setVendors] = useState([])
  const [analytics, setAnalytics] = useState({})
  const [loading, setLoading] = useState(false)

  // Mock data
  const mockQuotes = [
    {
      id: 'Q-ABC12345',
      customer: 'TechCorp Inc.',
      customerEmail: 'procurement@techcorp.com',
      origin: 'SGSIN',
      destination: 'USNYC',
      mode: 'SEA',
      service: 'FCL',
      status: 'ISSUED',
      totalAmount: 2450,
      issuedAt: '2025-01-15T10:30:00Z',
      validUntil: '2025-01-22T10:30:00Z',
      containers: [{ type: '40HC', count: 1 }]
    },
    {
      id: 'Q-XYZ789',
      customer: 'Global Imports Ltd.',
      customerEmail: 'shipping@globalimports.com',
      origin: 'HKHKG',
      destination: 'EGALY',
      mode: 'AIR',
      service: 'AIR',
      status: 'ACCEPTED',
      totalAmount: 1850,
      issuedAt: '2025-01-14T14:20:00Z',
      validUntil: '2025-01-21T14:20:00Z',
      weight: 500,
      volume: 2.5
    },
    {
      id: 'Q-DEF456',
      customer: 'Fashion Forward',
      customerEmail: 'logistics@fashionforward.com',
      origin: 'CNSHA',
      destination: 'NLRTM',
      mode: 'SEA',
      service: 'LCL',
      status: 'DRAFT',
      totalAmount: 890,
      issuedAt: null,
      validUntil: null,
      weight: 1200,
      volume: 8.5
    }
  ]

  const mockShipments = [
    {
      id: 'SH-2025001',
      quoteId: 'Q-ABC12345',
      customer: 'TechCorp Inc.',
      origin: 'SGSIN',
      destination: 'USNYC',
      mode: 'SEA',
      service: 'FCL',
      status: 'IN_TRANSIT',
      departureDate: '2025-01-15',
      estimatedArrival: '2025-02-05',
      containerNumber: 'MSKU1234567',
      vesselName: 'MSC OSCAR',
      trackingUpdates: [
        { date: '2025-01-15', status: 'DEPARTED', location: 'Singapore Port' },
        { date: '2025-01-20', status: 'IN_TRANSIT', location: 'Suez Canal' }
      ]
    },
    {
      id: 'SH-2025002',
      quoteId: 'Q-XYZ789',
      customer: 'Global Imports Ltd.',
      origin: 'HKHKG',
      destination: 'EGALY',
      mode: 'AIR',
      service: 'AIR',
      status: 'DELIVERED',
      departureDate: '2025-01-10',
      estimatedArrival: '2025-01-12',
      actualArrival: '2025-01-12',
      awbNumber: 'AWB123456789',
      flightNumber: 'CX123'
    }
  ]

  const mockCustomers = [
    {
      id: 'CUST-001',
      name: 'TechCorp Inc.',
      email: 'procurement@techcorp.com',
      phone: '+1-555-0123',
      company: 'TechCorp Inc.',
      industry: 'Technology',
      country: 'United States',
      status: 'ACTIVE',
      totalShipments: 15,
      totalSpent: 45000,
      joinedDate: '2024-03-15',
      lastActivity: '2025-01-15'
    },
    {
      id: 'CUST-002',
      name: 'Global Imports Ltd.',
      email: 'shipping@globalimports.com',
      phone: '+44-20-7123-4567',
      company: 'Global Imports Ltd.',
      industry: 'Import/Export',
      country: 'United Kingdom',
      status: 'ACTIVE',
      totalShipments: 28,
      totalSpent: 78000,
      joinedDate: '2024-01-20',
      lastActivity: '2025-01-14'
    },
    {
      id: 'CUST-003',
      name: 'Fashion Forward',
      email: 'logistics@fashionforward.com',
      phone: '+33-1-23-45-67-89',
      company: 'Fashion Forward',
      industry: 'Fashion',
      country: 'France',
      status: 'INACTIVE',
      totalShipments: 8,
      totalSpent: 12000,
      joinedDate: '2024-08-10',
      lastActivity: '2024-12-20'
    }
  ]

  const mockVendors = [
    {
      id: 'VEND-001',
      name: 'Pacific Shipping Lines',
      type: 'CARRIER',
      services: ['SEA_FCL', 'SEA_LCL'],
      routes: ['ASIA_US', 'ASIA_EUROPE'],
      status: 'ACTIVE',
      rating: 4.8,
      totalShipments: 150,
      onTimePerformance: 95.2
    },
    {
      id: 'VEND-002',
      name: 'Global Air Cargo',
      type: 'CARRIER',
      services: ['AIR_FREIGHT'],
      routes: ['GLOBAL'],
      status: 'ACTIVE',
      rating: 4.6,
      totalShipments: 89,
      onTimePerformance: 92.1
    },
    {
      id: 'VEND-003',
      name: 'Singapore Customs Services',
      type: 'CUSTOMS_BROKER',
      services: ['CUSTOMS_CLEARANCE', 'DOCUMENTATION'],
      routes: ['SINGAPORE'],
      status: 'ACTIVE',
      rating: 4.9,
      totalShipments: 200,
      onTimePerformance: 98.5
    }
  ]

  const mockAnalytics = {
    overview: {
      totalQuotes: 156,
      totalShipments: 89,
      totalCustomers: 45,
      totalRevenue: 234500,
      quotesGrowth: 12.5,
      shipmentsGrowth: 8.3,
      customersGrowth: 15.2,
      revenueGrowth: 18.7
    },
    recentActivity: [
      { type: 'quote', message: 'New quote Q-ABC12345 issued to TechCorp Inc.', time: '2 hours ago' },
      { type: 'shipment', message: 'Shipment SH-2025001 departed from Singapore', time: '4 hours ago' },
      { type: 'customer', message: 'New customer Fashion Forward registered', time: '1 day ago' }
    ],
    topRoutes: [
      { route: 'Singapore → New York', count: 25, revenue: 62500 },
      { route: 'Hong Kong → London', count: 18, revenue: 45000 },
      { route: 'Shanghai → Rotterdam', count: 15, revenue: 37500 }
    ],
    monthlyRevenue: [
      { month: 'Jul', revenue: 18500 },
      { month: 'Aug', revenue: 22000 },
      { month: 'Sep', revenue: 19800 },
      { month: 'Oct', revenue: 25600 },
      { month: 'Nov', revenue: 28900 },
      { month: 'Dec', revenue: 31200 },
      { month: 'Jan', revenue: 34500 }
    ]
  }

  useEffect(() => {
    // Initialize mock data
    setQuotes(mockQuotes)
    setShipments(mockShipments)
    setCustomers(mockCustomers)
    setVendors(mockVendors)
    setAnalytics(mockAnalytics)
  }, [])

  const getQuotes = async (filters = {}) => {
    setLoading(true)
    try {
      // Mock API call with filtering
      let filteredQuotes = [...mockQuotes]
      
      if (filters.status) {
        filteredQuotes = filteredQuotes.filter(q => q.status === filters.status)
      }
      
      if (filters.customer) {
        filteredQuotes = filteredQuotes.filter(q => 
          q.customer.toLowerCase().includes(filters.customer.toLowerCase())
        )
      }
      
      setQuotes(filteredQuotes)
      return { success: true, data: filteredQuotes }
    } catch (error) {
      return { success: false, error: 'Failed to fetch quotes' }
    } finally {
      setLoading(false)
    }
  }

  const updateQuoteStatus = async (quoteId, status) => {
    try {
      const updatedQuotes = quotes.map(q => 
        q.id === quoteId ? { ...q, status } : q
      )
      setQuotes(updatedQuotes)
      return { success: true }
    } catch (error) {
      return { success: false, error: 'Failed to update quote status' }
    }
  }

  const getShipments = async (filters = {}) => {
    setLoading(true)
    try {
      let filteredShipments = [...mockShipments]
      
      if (filters.status) {
        filteredShipments = filteredShipments.filter(s => s.status === filters.status)
      }
      
      setShipments(filteredShipments)
      return { success: true, data: filteredShipments }
    } catch (error) {
      return { success: false, error: 'Failed to fetch shipments' }
    } finally {
      setLoading(false)
    }
  }

  const getCustomers = async (filters = {}) => {
    setLoading(true)
    try {
      let filteredCustomers = [...mockCustomers]
      
      if (filters.status) {
        filteredCustomers = filteredCustomers.filter(c => c.status === filters.status)
      }
      
      setCustomers(filteredCustomers)
      return { success: true, data: filteredCustomers }
    } catch (error) {
      return { success: false, error: 'Failed to fetch customers' }
    } finally {
      setLoading(false)
    }
  }

  const value = {
    quotes,
    shipments,
    customers,
    vendors,
    analytics,
    loading,
    getQuotes,
    updateQuoteStatus,
    getShipments,
    getCustomers
  }

  return (
    <AdminContext.Provider value={value}>
      {children}
    </AdminContext.Provider>
  )
}

