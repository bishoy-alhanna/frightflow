import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import { 
  Search, 
  Building, 
  Star, 
  Package, 
  Clock, 
  MapPin,
  Ship,
  Plane,
  FileText,
  Eye,
  Edit,
  MoreHorizontal,
  Plus,
  TrendingUp
} from 'lucide-react'
import { motion } from 'framer-motion'
import { useAdmin } from '../contexts/AdminContext'

const VendorsPage = () => {
  const { vendors, loading } = useAdmin()
  
  const [searchTerm, setSearchTerm] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [filteredVendors, setFilteredVendors] = useState([])

  useEffect(() => {
    // Filter vendors based on search and filters
    let filtered = vendors

    if (searchTerm) {
      filtered = filtered.filter(vendor => 
        vendor.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        vendor.type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        vendor.services.some(service => service.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    }

    if (typeFilter !== 'all') {
      filtered = filtered.filter(vendor => vendor.type === typeFilter)
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(vendor => vendor.status === statusFilter)
    }

    setFilteredVendors(filtered)
  }, [vendors, searchTerm, typeFilter, statusFilter])

  const getStatusColor = (status) => {
    switch (status) {
      case 'ACTIVE': return 'success'
      case 'INACTIVE': return 'secondary'
      case 'SUSPENDED': return 'destructive'
      default: return 'secondary'
    }
  }

  const getTypeIcon = (type) => {
    switch (type) {
      case 'CARRIER': return Ship
      case 'CUSTOMS_BROKER': return FileText
      case 'WAREHOUSE': return Building
      default: return Building
    }
  }

  const getServiceIcon = (service) => {
    if (service.includes('SEA')) return Ship
    if (service.includes('AIR')) return Plane
    if (service.includes('CUSTOMS')) return FileText
    return Package
  }

  const getRatingColor = (rating) => {
    if (rating >= 4.5) return 'text-green-600'
    if (rating >= 4.0) return 'text-yellow-600'
    if (rating >= 3.0) return 'text-orange-600'
    return 'text-red-600'
  }

  const getPerformanceColor = (performance) => {
    if (performance >= 95) return 'text-green-600'
    if (performance >= 90) return 'text-yellow-600'
    if (performance >= 80) return 'text-orange-600'
    return 'text-red-600'
  }

  const stats = [
    {
      title: 'Total Vendors',
      value: vendors.length,
      color: 'blue'
    },
    {
      title: 'Active',
      value: vendors.filter(v => v.status === 'ACTIVE').length,
      color: 'green'
    },
    {
      title: 'Carriers',
      value: vendors.filter(v => v.type === 'CARRIER').length,
      color: 'purple'
    },
    {
      title: 'Avg Rating',
      value: vendors.length > 0 ? (vendors.reduce((sum, v) => sum + v.rating, 0) / vendors.length).toFixed(1) : '0.0',
      color: 'orange'
    }
  ]

  const vendorTypes = [...new Set(vendors.map(v => v.type))].sort()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Vendor Management</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage carriers, customs brokers, and service providers
          </p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Add Vendor
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
                  placeholder="Search by vendor name, type, or services..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {vendorTypes.map(type => (
                  <SelectItem key={type} value={type}>
                    {type.replace('_', ' ')}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="ACTIVE">Active</SelectItem>
                <SelectItem value="INACTIVE">Inactive</SelectItem>
                <SelectItem value="SUSPENDED">Suspended</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Vendors List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {loading ? (
          <Card className="col-span-full">
            <CardContent className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="text-gray-500 mt-2">Loading vendors...</p>
            </CardContent>
          </Card>
        ) : filteredVendors.length === 0 ? (
          <Card className="col-span-full">
            <CardContent className="p-8 text-center">
              <Building className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No vendors found</h3>
              <p className="text-gray-500 mb-4">
                {vendors.length === 0 
                  ? "No vendors have been registered yet."
                  : "No vendors match your current filters. Try adjusting your search criteria."
                }
              </p>
            </CardContent>
          </Card>
        ) : (
          filteredVendors.map((vendor, index) => {
            const TypeIcon = getTypeIcon(vendor.type)
            
            return (
              <motion.div
                key={vendor.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <Card className="hover:shadow-md transition-shadow">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                          <TypeIcon className="h-6 w-6 text-gray-600 dark:text-gray-400" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-lg">{vendor.name}</h3>
                          <p className="text-sm text-gray-500">
                            {vendor.type.replace('_', ' ')}
                          </p>
                        </div>
                      </div>
                      <Badge variant={getStatusColor(vendor.status)}>
                        {vendor.status}
                      </Badge>
                    </div>

                    {/* Services */}
                    <div className="mb-4">
                      <p className="text-sm text-gray-500 mb-2">Services</p>
                      <div className="flex flex-wrap gap-2">
                        {vendor.services.map((service, idx) => {
                          const ServiceIcon = getServiceIcon(service)
                          return (
                            <div key={idx} className="flex items-center space-x-1 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-xs">
                              <ServiceIcon className="h-3 w-3" />
                              <span>{service.replace('_', ' ')}</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {/* Routes */}
                    <div className="mb-4">
                      <p className="text-sm text-gray-500 mb-2">Coverage</p>
                      <div className="flex items-center space-x-2 text-sm">
                        <MapPin className="h-4 w-4 text-gray-400" />
                        <span>{vendor.routes.join(', ')}</span>
                      </div>
                    </div>

                    {/* Performance Metrics */}
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-500">Rating</span>
                          <div className="flex items-center space-x-1">
                            <Star className={`h-4 w-4 ${getRatingColor(vendor.rating)}`} fill="currentColor" />
                            <span className={`text-sm font-medium ${getRatingColor(vendor.rating)}`}>
                              {vendor.rating}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-500">On-Time</span>
                          <span className={`text-sm font-medium ${getPerformanceColor(vendor.onTimePerformance)}`}>
                            {vendor.onTimePerformance}%
                          </span>
                        </div>
                        <Progress value={vendor.onTimePerformance} className="h-2" />
                      </div>
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-2 gap-4 mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                      <div className="text-center">
                        <div className="flex items-center justify-center space-x-1 mb-1">
                          <Package className="h-4 w-4 text-gray-400" />
                          <span className="text-sm font-medium">{vendor.totalShipments}</span>
                        </div>
                        <p className="text-xs text-gray-500">Total Shipments</p>
                      </div>
                      <div className="text-center">
                        <div className="flex items-center justify-center space-x-1 mb-1">
                          <TrendingUp className="h-4 w-4 text-gray-400" />
                          <span className="text-sm font-medium">{vendor.onTimePerformance}%</span>
                        </div>
                        <p className="text-xs text-gray-500">Performance</p>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex space-x-2">
                      <Button variant="outline" size="sm" className="flex-1">
                        <Eye className="h-4 w-4 mr-1" />
                        View
                      </Button>
                      <Button variant="outline" size="sm" className="flex-1">
                        <Edit className="h-4 w-4 mr-1" />
                        Edit
                      </Button>
                      <Button variant="outline" size="sm">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
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

export default VendorsPage

