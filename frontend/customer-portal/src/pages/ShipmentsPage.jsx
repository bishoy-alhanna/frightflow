import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Package, 
  Search, 
  Filter, 
  Download, 
  Eye,
  Ship,
  Plane,
  Clock,
  MapPin,
  DollarSign,
  FileText,
  Plus
} from 'lucide-react'
import { motion } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import { useQuote } from '../contexts/QuoteContext'

const ShipmentsPage = () => {
  const { user } = useAuth()
  const { quotes, getQuotes, downloadQuotePDF } = useQuote()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [modeFilter, setModeFilter] = useState('all')
  const [filteredQuotes, setFilteredQuotes] = useState([])

  // Mock shipment data for demonstration
  const mockShipments = [
    {
      id: 'SH-2025001',
      quote_id: 'Q-ABC12345',
      status: 'IN_TRANSIT',
      mode: 'SEA',
      service: 'FCL',
      origin: 'SGSIN',
      destination: 'USNYC',
      departure_date: '2025-01-15',
      estimated_arrival: '2025-02-05',
      actual_arrival: null,
      container_number: 'MSKU1234567',
      vessel_name: 'MSC OSCAR',
      tracking_updates: [
        { date: '2025-01-15', status: 'DEPARTED', location: 'Singapore Port' },
        { date: '2025-01-20', status: 'IN_TRANSIT', location: 'Suez Canal' },
        { date: '2025-01-28', status: 'IN_TRANSIT', location: 'Mediterranean Sea' }
      ]
    },
    {
      id: 'SH-2025002',
      quote_id: 'Q-XYZ789',
      status: 'DELIVERED',
      mode: 'AIR',
      service: 'AIR',
      origin: 'HKHKG',
      destination: 'EGALY',
      departure_date: '2025-01-10',
      estimated_arrival: '2025-01-12',
      actual_arrival: '2025-01-12',
      awb_number: 'AWB123456789',
      flight_number: 'CX123',
      tracking_updates: [
        { date: '2025-01-10', status: 'DEPARTED', location: 'Hong Kong Airport' },
        { date: '2025-01-11', status: 'IN_TRANSIT', location: 'Dubai Airport' },
        { date: '2025-01-12', status: 'DELIVERED', location: 'Alexandria Airport' }
      ]
    }
  ]

  const [shipments] = useState(mockShipments)

  useEffect(() => {
    // Filter quotes based on search and filters
    let filtered = quotes

    if (searchTerm) {
      filtered = filtered.filter(quote => 
        quote.quote_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        quote.origin.toLowerCase().includes(searchTerm.toLowerCase()) ||
        quote.destination.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(quote => quote.status === statusFilter)
    }

    if (modeFilter !== 'all') {
      filtered = filtered.filter(quote => quote.mode === modeFilter)
    }

    setFilteredQuotes(filtered)
  }, [quotes, searchTerm, statusFilter, modeFilter])

  const getStatusColor = (status) => {
    switch (status) {
      case 'DRAFT': return 'secondary'
      case 'ISSUED': return 'default'
      case 'ACCEPTED': return 'success'
      case 'EXPIRED': return 'destructive'
      case 'IN_TRANSIT': return 'default'
      case 'DELIVERED': return 'success'
      default: return 'secondary'
    }
  }

  const getModeIcon = (mode) => {
    switch (mode) {
      case 'SEA': return Ship
      case 'AIR': return Plane
      default: return Package
    }
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const handleDownloadPDF = async (quoteId) => {
    try {
      await downloadQuotePDF(quoteId)
    } catch (error) {
      console.error('Failed to download PDF:', error)
    }
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="p-6 text-center">
            <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Login Required</h2>
            <p className="text-muted-foreground mb-4">
              Please login to view your shipments and quotes.
            </p>
            <Button asChild>
              <Link to="/login">Login</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen py-8">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
            <div>
              <h1 className="text-3xl font-bold">My Shipments</h1>
              <p className="text-muted-foreground">
                Track your quotes and shipments in one place
              </p>
            </div>
            <Button asChild>
              <Link to="/quote">
                <Plus className="h-4 w-4 mr-2" />
                New Quote
              </Link>
            </Button>
          </div>

          {/* Filters */}
          <Card className="mb-6">
            <CardContent className="p-4">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search by quote ID, origin, or destination..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Filter by status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="DRAFT">Draft</SelectItem>
                    <SelectItem value="ISSUED">Issued</SelectItem>
                    <SelectItem value="ACCEPTED">Accepted</SelectItem>
                    <SelectItem value="EXPIRED">Expired</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={modeFilter} onValueChange={setModeFilter}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Filter by mode" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Modes</SelectItem>
                    <SelectItem value="SEA">Sea Freight</SelectItem>
                    <SelectItem value="AIR">Air Freight</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Tabs */}
          <Tabs defaultValue="quotes" className="space-y-6">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="quotes">Quotes ({filteredQuotes.length})</TabsTrigger>
              <TabsTrigger value="shipments">Active Shipments ({shipments.length})</TabsTrigger>
            </TabsList>

            {/* Quotes Tab */}
            <TabsContent value="quotes" className="space-y-4">
              {filteredQuotes.length === 0 ? (
                <Card>
                  <CardContent className="p-8 text-center">
                    <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">No quotes found</h3>
                    <p className="text-muted-foreground mb-4">
                      {quotes.length === 0 
                        ? "You haven't created any quotes yet. Get started by requesting a quote."
                        : "No quotes match your current filters. Try adjusting your search criteria."
                      }
                    </p>
                    <Button asChild>
                      <Link to="/quote">Get Your First Quote</Link>
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-4">
                  {filteredQuotes.map((quote, index) => {
                    const ModeIcon = getModeIcon(quote.mode)
                    return (
                      <motion.div
                        key={quote.quote_id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, delay: index * 0.1 }}
                      >
                        <Card className="hover:shadow-md transition-shadow">
                          <CardContent className="p-6">
                            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
                              <div className="flex items-start space-x-4 flex-1">
                                <div className="p-2 bg-primary/10 rounded-lg">
                                  <ModeIcon className="h-6 w-6 text-primary" />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center space-x-2 mb-2">
                                    <h3 className="font-semibold text-lg">{quote.quote_id}</h3>
                                    <Badge variant={getStatusColor(quote.status)}>
                                      {quote.status}
                                    </Badge>
                                  </div>
                                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                                    <div className="flex items-center space-x-2">
                                      <MapPin className="h-4 w-4 text-muted-foreground" />
                                      <span>{quote.origin} → {quote.destination}</span>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                      <Package className="h-4 w-4 text-muted-foreground" />
                                      <span>{quote.mode} {quote.service}</span>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                      <DollarSign className="h-4 w-4 text-muted-foreground" />
                                      <span>${quote.total_amount?.toLocaleString()}</span>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                      <Clock className="h-4 w-4 text-muted-foreground" />
                                      <span>
                                        {quote.issued_at 
                                          ? formatDate(quote.issued_at)
                                          : 'Draft'
                                        }
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center space-x-2">
                                <Button variant="outline" size="sm">
                                  <Eye className="h-4 w-4 mr-1" />
                                  View
                                </Button>
                                <Button 
                                  variant="outline" 
                                  size="sm"
                                  onClick={() => handleDownloadPDF(quote.quote_id)}
                                >
                                  <Download className="h-4 w-4 mr-1" />
                                  PDF
                                </Button>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </motion.div>
                    )
                  })}
                </div>
              )}
            </TabsContent>

            {/* Shipments Tab */}
            <TabsContent value="shipments" className="space-y-4">
              {shipments.length === 0 ? (
                <Card>
                  <CardContent className="p-8 text-center">
                    <Ship className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">No active shipments</h3>
                    <p className="text-muted-foreground mb-4">
                      You don't have any active shipments at the moment.
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-6">
                  {shipments.map((shipment, index) => {
                    const ModeIcon = getModeIcon(shipment.mode)
                    return (
                      <motion.div
                        key={shipment.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, delay: index * 0.1 }}
                      >
                        <Card>
                          <CardHeader>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-3">
                                <div className="p-2 bg-primary/10 rounded-lg">
                                  <ModeIcon className="h-6 w-6 text-primary" />
                                </div>
                                <div>
                                  <CardTitle className="text-xl">{shipment.id}</CardTitle>
                                  <CardDescription>
                                    Quote: {shipment.quote_id} • {shipment.mode} {shipment.service}
                                  </CardDescription>
                                </div>
                              </div>
                              <Badge variant={getStatusColor(shipment.status)}>
                                {shipment.status.replace('_', ' ')}
                              </Badge>
                            </div>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            {/* Route and Dates */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                              <div className="space-y-2">
                                <h4 className="font-medium">Route</h4>
                                <div className="flex items-center space-x-2 text-sm">
                                  <MapPin className="h-4 w-4 text-muted-foreground" />
                                  <span>{shipment.origin} → {shipment.destination}</span>
                                </div>
                              </div>
                              <div className="space-y-2">
                                <h4 className="font-medium">Departure</h4>
                                <div className="flex items-center space-x-2 text-sm">
                                  <Clock className="h-4 w-4 text-muted-foreground" />
                                  <span>{formatDate(shipment.departure_date)}</span>
                                </div>
                              </div>
                              <div className="space-y-2">
                                <h4 className="font-medium">
                                  {shipment.actual_arrival ? 'Delivered' : 'ETA'}
                                </h4>
                                <div className="flex items-center space-x-2 text-sm">
                                  <Clock className="h-4 w-4 text-muted-foreground" />
                                  <span>
                                    {formatDate(shipment.actual_arrival || shipment.estimated_arrival)}
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* Tracking Info */}
                            <div className="space-y-2">
                              <h4 className="font-medium">Tracking Information</h4>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                {shipment.container_number && (
                                  <div>
                                    <span className="text-muted-foreground">Container: </span>
                                    <span className="font-mono">{shipment.container_number}</span>
                                  </div>
                                )}
                                {shipment.vessel_name && (
                                  <div>
                                    <span className="text-muted-foreground">Vessel: </span>
                                    <span>{shipment.vessel_name}</span>
                                  </div>
                                )}
                                {shipment.awb_number && (
                                  <div>
                                    <span className="text-muted-foreground">AWB: </span>
                                    <span className="font-mono">{shipment.awb_number}</span>
                                  </div>
                                )}
                                {shipment.flight_number && (
                                  <div>
                                    <span className="text-muted-foreground">Flight: </span>
                                    <span>{shipment.flight_number}</span>
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Tracking Timeline */}
                            <div className="space-y-2">
                              <h4 className="font-medium">Tracking Updates</h4>
                              <div className="space-y-3">
                                {shipment.tracking_updates.map((update, updateIndex) => (
                                  <div key={updateIndex} className="flex items-center space-x-3">
                                    <div className={`w-3 h-3 rounded-full ${
                                      updateIndex === shipment.tracking_updates.length - 1 
                                        ? 'bg-primary' 
                                        : 'bg-muted-foreground'
                                    }`} />
                                    <div className="flex-1">
                                      <div className="flex items-center justify-between">
                                        <span className="font-medium text-sm">
                                          {update.status.replace('_', ' ')}
                                        </span>
                                        <span className="text-xs text-muted-foreground">
                                          {formatDate(update.date)}
                                        </span>
                                      </div>
                                      <p className="text-sm text-muted-foreground">
                                        {update.location}
                                      </p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </motion.div>
                    )
                  })}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}

export default ShipmentsPage

