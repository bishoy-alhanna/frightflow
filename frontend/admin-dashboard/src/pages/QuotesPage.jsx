import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu'
import { useToast } from '@/hooks/use-toast'
import { 
  Search, 
  Filter, 
  Download, 
  Eye, 
  MoreHorizontal,
  Ship,
  Plane,
  Clock,
  MapPin,
  DollarSign,
  User,
  Mail,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react'
import { motion } from 'framer-motion'
import { useAdmin } from '../contexts/AdminContext'

const QuotesPage = () => {
  const { quotes, getQuotes, updateQuoteStatus, loading } = useAdmin()
  const { toast } = useToast()
  
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [modeFilter, setModeFilter] = useState('all')
  const [filteredQuotes, setFilteredQuotes] = useState([])

  useEffect(() => {
    // Filter quotes based on search and filters
    let filtered = quotes

    if (searchTerm) {
      filtered = filtered.filter(quote => 
        quote.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        quote.customer.toLowerCase().includes(searchTerm.toLowerCase()) ||
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
      default: return 'secondary'
    }
  }

  const getModeIcon = (mode) => {
    return mode === 'SEA' ? Ship : Plane
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Draft'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const handleStatusUpdate = async (quoteId, newStatus) => {
    try {
      const result = await updateQuoteStatus(quoteId, newStatus)
      if (result.success) {
        toast({
          title: "Status Updated",
          description: `Quote ${quoteId} status updated to ${newStatus}`,
        })
      } else {
        throw new Error(result.error)
      }
    } catch (error) {
      toast({
        title: "Update Failed",
        description: "Failed to update quote status. Please try again.",
        variant: "destructive"
      })
    }
  }

  const handleDownloadPDF = (quoteId) => {
    // Mock PDF download
    toast({
      title: "Download Started",
      description: `Downloading PDF for quote ${quoteId}`,
    })
  }

  const getStatusActions = (status) => {
    switch (status) {
      case 'DRAFT':
        return [
          { label: 'Issue Quote', value: 'ISSUED', icon: CheckCircle },
          { label: 'Cancel', value: 'CANCELLED', icon: XCircle }
        ]
      case 'ISSUED':
        return [
          { label: 'Mark Accepted', value: 'ACCEPTED', icon: CheckCircle },
          { label: 'Mark Expired', value: 'EXPIRED', icon: AlertCircle }
        ]
      case 'ACCEPTED':
        return []
      case 'EXPIRED':
        return [
          { label: 'Reissue', value: 'ISSUED', icon: CheckCircle }
        ]
      default:
        return []
    }
  }

  const stats = [
    {
      title: 'Total Quotes',
      value: quotes.length,
      color: 'blue'
    },
    {
      title: 'Issued',
      value: quotes.filter(q => q.status === 'ISSUED').length,
      color: 'yellow'
    },
    {
      title: 'Accepted',
      value: quotes.filter(q => q.status === 'ACCEPTED').length,
      color: 'green'
    },
    {
      title: 'Expired',
      value: quotes.filter(q => q.status === 'EXPIRED').length,
      color: 'red'
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Quotes Management</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage and track all freight quotes
          </p>
        </div>
        <Button>
          <Download className="h-4 w-4 mr-2" />
          Export All
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
                  placeholder="Search by quote ID, customer, origin, or destination..."
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

      {/* Quotes List */}
      <div className="space-y-4">
        {loading ? (
          <Card>
            <CardContent className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="text-gray-500 mt-2">Loading quotes...</p>
            </CardContent>
          </Card>
        ) : filteredQuotes.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No quotes found</h3>
              <p className="text-gray-500 mb-4">
                {quotes.length === 0 
                  ? "No quotes have been created yet."
                  : "No quotes match your current filters. Try adjusting your search criteria."
                }
              </p>
            </CardContent>
          </Card>
        ) : (
          filteredQuotes.map((quote, index) => {
            const ModeIcon = getModeIcon(quote.mode)
            const statusActions = getStatusActions(quote.status)
            
            return (
              <motion.div
                key={quote.id}
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
                            <h3 className="font-semibold text-lg">{quote.id}</h3>
                            <Badge variant={getStatusColor(quote.status)}>
                              {quote.status}
                            </Badge>
                          </div>
                          
                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                            <div className="flex items-center space-x-2">
                              <User className="h-4 w-4 text-gray-400" />
                              <div>
                                <p className="font-medium">{quote.customer}</p>
                                <p className="text-gray-500">{quote.customerEmail}</p>
                              </div>
                            </div>
                            
                            <div className="flex items-center space-x-2">
                              <MapPin className="h-4 w-4 text-gray-400" />
                              <span>{quote.origin} → {quote.destination}</span>
                            </div>
                            
                            <div className="flex items-center space-x-2">
                              <Package className="h-4 w-4 text-gray-400" />
                              <span>{quote.mode} {quote.service}</span>
                            </div>
                            
                            <div className="flex items-center space-x-2">
                              <DollarSign className="h-4 w-4 text-gray-400" />
                              <span>${quote.totalAmount?.toLocaleString()}</span>
                            </div>
                          </div>
                          
                          <div className="mt-3 flex items-center space-x-4 text-xs text-gray-500">
                            <div className="flex items-center space-x-1">
                              <Clock className="h-3 w-3" />
                              <span>
                                Issued: {formatDate(quote.issuedAt)}
                              </span>
                            </div>
                            {quote.validUntil && (
                              <div className="flex items-center space-x-1">
                                <AlertCircle className="h-3 w-3" />
                                <span>
                                  Valid until: {formatDate(quote.validUntil)}
                                </span>
                              </div>
                            )}
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
                          onClick={() => handleDownloadPDF(quote.id)}
                        >
                          <Download className="h-4 w-4 mr-1" />
                          PDF
                        </Button>
                        
                        {statusActions.length > 0 && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="outline" size="sm">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              {statusActions.map((action) => {
                                const ActionIcon = action.icon
                                return (
                                  <DropdownMenuItem
                                    key={action.value}
                                    onClick={() => handleStatusUpdate(quote.id, action.value)}
                                  >
                                    <ActionIcon className="mr-2 h-4 w-4" />
                                    {action.label}
                                  </DropdownMenuItem>
                                )
                              })}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
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

export default QuotesPage

