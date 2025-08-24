import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import { 
  Search, 
  MapPin, 
  Calendar, 
  Ship, 
  Plane, 
  Package, 
  Clock,
  CheckCircle,
  Truck,
  AlertTriangle,
  Eye,
  Download
} from 'lucide-react'
import { motion } from 'framer-motion'
import { useAdmin } from '../contexts/AdminContext'

const ShipmentsPage = () => {
  const { shipments, getShipments, loading } = useAdmin()
  
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [modeFilter, setModeFilter] = useState('all')
  const [filteredShipments, setFilteredShipments] = useState([])

  useEffect(() => {
    // Filter shipments based on search and filters
    let filtered = shipments

    if (searchTerm) {
      filtered = filtered.filter(shipment => 
        shipment.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        shipment.customer.toLowerCase().includes(searchTerm.toLowerCase()) ||
        shipment.origin.toLowerCase().includes(searchTerm.toLowerCase()) ||
        shipment.destination.toLowerCase().includes(searchTerm.toLowerCase()) ||
        shipment.containerNumber?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        shipment.awbNumber?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(shipment => shipment.status === statusFilter)
    }

    if (modeFilter !== 'all') {
      filtered = filtered.filter(shipment => shipment.mode === modeFilter)
    }

    setFilteredShipments(filtered)
  }, [shipments, searchTerm, statusFilter, modeFilter])

  const getStatusColor = (status) => {
    switch (status) {
      case 'BOOKED': return 'secondary'
      case 'IN_TRANSIT': return 'default'
      case 'DELIVERED': return 'success'
      case 'DELAYED': return 'destructive'
      default: return 'secondary'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'BOOKED': return Package
      case 'IN_TRANSIT': return Truck
      case 'DELIVERED': return CheckCircle
      case 'DELAYED': return AlertTriangle
      default: return Package
    }
  }

  const getModeIcon = (mode) => {
    return mode === 'SEA' ? Ship : Plane
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'TBD'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const calculateProgress = (shipment) => {
    const now = new Date()
    const departure = new Date(shipment.departureDate)
    const arrival = new Date(shipment.estimatedArrival || shipment.actualArrival)
    
    if (shipment.status === 'DELIVERED') return 100
    if (shipment.status === 'BOOKED') return 0
    
    const totalTime = arrival.getTime() - departure.getTime()
    const elapsedTime = now.getTime() - departure.getTime()
    
    return Math.min(Math.max((elapsedTime / totalTime) * 100, 0), 95)
  }

  const stats = [
    {
      title: 'Total Shipments',
      value: shipments.length,
      color: 'blue'
    },
    {
      title: 'In Transit',
      value: shipments.filter(s => s.status === 'IN_TRANSIT').length,
      color: 'yellow'
    },
    {
      title: 'Delivered',
      value: shipments.filter(s => s.status === 'DELIVERED').length,
      color: 'green'
    },
    {
      title: 'Delayed',
      value: shipments.filter(s => s.status === 'DELAYED').length,
      color: 'red'
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Shipments Tracking</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Monitor and track all active shipments
          </p>
        </div>
        <Button>
          <Download className="h-4 w-4 mr-2" />
          Export Report
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
          >
            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stat.value}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {stat.title}
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search by shipment ID, customer, container/AWB number..."
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
                <SelectItem value="BOOKED">Booked</SelectItem>
                <SelectItem value="IN_TRANSIT">In Transit</SelectItem>
                <SelectItem value="DELIVERED">Delivered</SelectItem>
                <SelectItem value="DELAYED">Delayed</SelectItem>
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

      {/* Shipments List */}
      <div className="space-y-4">
        {loading ? (
          <Card>
            <CardContent className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="text-gray-500 mt-2">Loading shipments...</p>
            </CardContent>
          </Card>
        ) : filteredShipments.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center">
              <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No shipments found</h3>
              <p className="text-gray-500 mb-4">
                {shipments.length === 0 
                  ? "No shipments have been created yet."
                  : "No shipments match your current filters. Try adjusting your search criteria."
                }
              </p>
            </CardContent>
          </Card>
        ) : (
          filteredShipments.map((shipment, index) => {
            const ModeIcon = getModeIcon(shipment.mode)
            const StatusIcon = getStatusIcon(shipment.status)
            const progress = calculateProgress(shipment)
            
            return (
              <motion.div
                key={shipment.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <Card className="hover:shadow-md transition-shadow">
                  <CardContent className="p-6">
                    <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
                      <div className="flex items-start space-x-4 flex-1">
                        <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                          <ModeIcon className="h-6 w-6 text-gray-600 dark:text-gray-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-3 mb-2">
                            <h3 className="font-semibold text-lg">{shipment.id}</h3>
                            <Badge variant={getStatusColor(shipment.status)}>
                              <StatusIcon className="h-3 w-3 mr-1" />
                              {shipment.status.replace('_', ' ')}
                            </Badge>
                          </div>
                          
                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm mb-4">
                            <div>
                              <p className="text-gray-500 mb-1">Customer</p>
                              <p className="font-medium">{shipment.customer}</p>
                            </div>
                            
                            <div>
                              <p className="text-gray-500 mb-1">Route</p>
                              <div className="flex items-center space-x-2">
                                <MapPin className="h-4 w-4 text-gray-400" />
                                <span>{shipment.origin} → {shipment.destination}</span>
                              </div>
                            </div>
                            
                            <div>
                              <p className="text-gray-500 mb-1">Service</p>
                              <span>{shipment.mode} {shipment.service}</span>
                            </div>
                            
                            <div>
                              <p className="text-gray-500 mb-1">Departure</p>
                              <div className="flex items-center space-x-2">
                                <Calendar className="h-4 w-4 text-gray-400" />
                                <span>{formatDate(shipment.departureDate)}</span>
                              </div>
                            </div>
                            
                            <div>
                              <p className="text-gray-500 mb-1">
                                {shipment.actualArrival ? 'Delivered' : 'ETA'}
                              </p>
                              <div className="flex items-center space-x-2">
                                <Clock className="h-4 w-4 text-gray-400" />
                                <span>
                                  {formatDate(shipment.actualArrival || shipment.estimatedArrival)}
                                </span>
                              </div>
                            </div>
                            
                            <div>
                              <p className="text-gray-500 mb-1">Reference</p>
                              <span className="font-mono text-xs">
                                {shipment.containerNumber || shipment.awbNumber || 'N/A'}
                              </span>
                            </div>
                          </div>
                          
                          {/* Progress Bar */}
                          {shipment.status !== 'BOOKED' && (
                            <div className="mb-3">
                              <div className="flex justify-between items-center mb-2">
                                <span className="text-sm text-gray-500">Progress</span>
                                <span className="text-sm font-medium">{Math.round(progress)}%</span>
                              </div>
                              <Progress value={progress} className="h-2" />
                            </div>
                          )}
                          
                          {/* Latest Update */}
                          {shipment.trackingUpdates && shipment.trackingUpdates.length > 0 && (
                            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                              <p className="text-xs text-gray-500 mb-1">Latest Update</p>
                              <div className="flex items-center justify-between">
                                <div>
                                  <p className="text-sm font-medium">
                                    {shipment.trackingUpdates[shipment.trackingUpdates.length - 1].status.replace('_', ' ')}
                                  </p>
                                  <p className="text-xs text-gray-500">
                                    {shipment.trackingUpdates[shipment.trackingUpdates.length - 1].location}
                                  </p>
                                </div>
                                <p className="text-xs text-gray-500">
                                  {formatDate(shipment.trackingUpdates[shipment.trackingUpdates.length - 1].date)}
                                </p>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Button variant="outline" size="sm">
                          <Eye className="h-4 w-4 mr-1" />
                          Track
                        </Button>
                        <Button variant="outline" size="sm">
                          <Download className="h-4 w-4 mr-1" />
                          BOL
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })
        )}
      </div>
    </div>
  )
}

export default ShipmentsPage

