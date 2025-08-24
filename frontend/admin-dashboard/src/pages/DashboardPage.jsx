import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import { 
  FileText, 
  Package, 
  Users, 
  DollarSign, 
  TrendingUp, 
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Ship,
  Plane,
  Clock,
  AlertCircle
} from 'lucide-react'
import { motion } from 'framer-motion'
import { useAdmin } from '../contexts/AdminContext'
import { useAuth } from '../contexts/AuthContext'

const DashboardPage = () => {
  const { analytics, quotes, shipments, customers } = useAdmin()
  const { user } = useAuth()

  const stats = [
    {
      title: 'Total Quotes',
      value: analytics.overview?.totalQuotes || 0,
      change: analytics.overview?.quotesGrowth || 0,
      icon: FileText,
      color: 'blue'
    },
    {
      title: 'Active Shipments',
      value: analytics.overview?.totalShipments || 0,
      change: analytics.overview?.shipmentsGrowth || 0,
      icon: Package,
      color: 'green'
    },
    {
      title: 'Total Customers',
      value: analytics.overview?.totalCustomers || 0,
      change: analytics.overview?.customersGrowth || 0,
      icon: Users,
      color: 'purple'
    },
    {
      title: 'Monthly Revenue',
      value: `$${(analytics.overview?.totalRevenue || 0).toLocaleString()}`,
      change: analytics.overview?.revenueGrowth || 0,
      icon: DollarSign,
      color: 'orange'
    }
  ]

  const getStatColor = (color) => {
    const colors = {
      blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400',
      green: 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400',
      purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400',
      orange: 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400'
    }
    return colors[color] || colors.blue
  }

  const recentQuotes = quotes.slice(0, 5)
  const recentShipments = shipments.slice(0, 5)

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
    return mode === 'SEA' ? Ship : Plane
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Draft'
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    })
  }

  const pieData = [
    { name: 'Sea Freight', value: 65, color: '#3b82f6' },
    { name: 'Air Freight', value: 35, color: '#10b981' }
  ]

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Welcome back, {user?.name?.split(' ')[0] || 'Admin'}!
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Here's what's happening with your freight operations today.
          </p>
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Last updated: {new Date().toLocaleString()}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => {
          const Icon = stat.icon
          const isPositive = stat.change >= 0
          
          return (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                        {stat.title}
                      </p>
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">
                        {stat.value}
                      </p>
                    </div>
                    <div className={`p-3 rounded-full ${getStatColor(stat.color)}`}>
                      <Icon className="h-6 w-6" />
                    </div>
                  </div>
                  <div className="mt-4 flex items-center">
                    {isPositive ? (
                      <ArrowUpRight className="h-4 w-4 text-green-500" />
                    ) : (
                      <ArrowDownRight className="h-4 w-4 text-red-500" />
                    )}
                    <span className={`text-sm font-medium ml-1 ${
                      isPositive ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {Math.abs(stat.change)}%
                    </span>
                    <span className="text-sm text-gray-500 ml-1">vs last month</span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Monthly Revenue</CardTitle>
              <CardDescription>Revenue trend over the last 7 months</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={analytics.monthlyRevenue || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip formatter={(value) => [`$${value.toLocaleString()}`, 'Revenue']} />
                  <Line 
                    type="monotone" 
                    dataKey="revenue" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    dot={{ fill: '#3b82f6' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

        {/* Service Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Service Distribution</CardTitle>
              <CardDescription>Breakdown by transport mode</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${value}%`, 'Share']} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex justify-center space-x-6 mt-4">
                {pieData.map((entry, index) => (
                  <div key={index} className="flex items-center">
                    <div 
                      className="w-3 h-3 rounded-full mr-2" 
                      style={{ backgroundColor: entry.color }}
                    />
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {entry.name} ({entry.value}%)
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Quotes */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Recent Quotes</CardTitle>
                <CardDescription>Latest quote requests and updates</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link to="/quotes">View All</Link>
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentQuotes.length === 0 ? (
                  <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                    No recent quotes
                  </p>
                ) : (
                  recentQuotes.map((quote) => {
                    const ModeIcon = getModeIcon(quote.mode)
                    return (
                      <div key={quote.id} className="flex items-center justify-between p-3 rounded-lg border">
                        <div className="flex items-center space-x-3">
                          <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                            <ModeIcon className="h-4 w-4" />
                          </div>
                          <div>
                            <p className="font-medium text-sm">{quote.id}</p>
                            <p className="text-xs text-gray-500">{quote.customer}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge variant={getStatusColor(quote.status)} className="text-xs">
                            {quote.status}
                          </Badge>
                          <p className="text-xs text-gray-500 mt-1">
                            ${quote.totalAmount?.toLocaleString()}
                          </p>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Recent Shipments */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.7 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Active Shipments</CardTitle>
                <CardDescription>Current shipments in transit</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link to="/shipments">View All</Link>
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentShipments.length === 0 ? (
                  <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                    No active shipments
                  </p>
                ) : (
                  recentShipments.map((shipment) => {
                    const ModeIcon = getModeIcon(shipment.mode)
                    return (
                      <div key={shipment.id} className="flex items-center justify-between p-3 rounded-lg border">
                        <div className="flex items-center space-x-3">
                          <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                            <ModeIcon className="h-4 w-4" />
                          </div>
                          <div>
                            <p className="font-medium text-sm">{shipment.id}</p>
                            <p className="text-xs text-gray-500">
                              {shipment.origin} → {shipment.destination}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge variant={getStatusColor(shipment.status)} className="text-xs">
                            {shipment.status.replace('_', ' ')}
                          </Badge>
                          <p className="text-xs text-gray-500 mt-1">
                            ETA: {formatDate(shipment.estimatedArrival)}
                          </p>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Top Routes */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.8 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>Top Routes</CardTitle>
            <CardDescription>Most popular shipping routes this month</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {analytics.topRoutes?.map((route, index) => (
                <div key={index} className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800">
                  <div className="flex items-center space-x-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 text-sm font-medium">
                      {index + 1}
                    </div>
                    <div>
                      <p className="font-medium">{route.route}</p>
                      <p className="text-sm text-gray-500">{route.count} shipments</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">${route.revenue?.toLocaleString()}</p>
                    <p className="text-sm text-gray-500">Revenue</p>
                  </div>
                </div>
              )) || (
                <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                  No route data available
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

export default DashboardPage

