import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
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
  Cell,
  AreaChart,
  Area
} from 'recharts'
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Package, 
  Users, 
  FileText,
  Download,
  Calendar,
  BarChart3,
  PieChart as PieChartIcon,
  Activity
} from 'lucide-react'
import { motion } from 'framer-motion'
import { useAdmin } from '../contexts/AdminContext'

const AnalyticsPage = () => {
  const { analytics } = useAdmin()
  const [timeRange, setTimeRange] = useState('7d')
  const [chartType, setChartType] = useState('revenue')

  // Mock data for different time ranges
  const getDataByTimeRange = (range) => {
    switch (range) {
      case '24h':
        return [
          { period: '00:00', revenue: 1200, quotes: 5, shipments: 2 },
          { period: '04:00', revenue: 800, quotes: 3, shipments: 1 },
          { period: '08:00', revenue: 2400, quotes: 8, shipments: 4 },
          { period: '12:00', revenue: 3200, quotes: 12, shipments: 6 },
          { period: '16:00', revenue: 2800, quotes: 10, shipments: 5 },
          { period: '20:00', revenue: 1600, quotes: 6, shipments: 3 }
        ]
      case '7d':
        return [
          { period: 'Mon', revenue: 18500, quotes: 25, shipments: 12 },
          { period: 'Tue', revenue: 22000, quotes: 32, shipments: 18 },
          { period: 'Wed', revenue: 19800, quotes: 28, shipments: 15 },
          { period: 'Thu', revenue: 25600, quotes: 35, shipments: 22 },
          { period: 'Fri', revenue: 28900, quotes: 42, shipments: 28 },
          { period: 'Sat', revenue: 15200, quotes: 18, shipments: 10 },
          { period: 'Sun', revenue: 12400, quotes: 15, shipments: 8 }
        ]
      case '30d':
        return analytics.monthlyRevenue?.map((item, index) => ({
          period: item.month,
          revenue: item.revenue,
          quotes: 20 + index * 5,
          shipments: 10 + index * 3
        })) || []
      default:
        return []
    }
  }

  const chartData = getDataByTimeRange(timeRange)

  const kpiData = [
    {
      title: 'Total Revenue',
      value: `$${(analytics.overview?.totalRevenue || 0).toLocaleString()}`,
      change: analytics.overview?.revenueGrowth || 0,
      icon: DollarSign,
      color: 'green'
    },
    {
      title: 'Active Quotes',
      value: analytics.overview?.totalQuotes || 0,
      change: analytics.overview?.quotesGrowth || 0,
      icon: FileText,
      color: 'blue'
    },
    {
      title: 'Shipments',
      value: analytics.overview?.totalShipments || 0,
      change: analytics.overview?.shipmentsGrowth || 0,
      icon: Package,
      color: 'purple'
    },
    {
      title: 'Customers',
      value: analytics.overview?.totalCustomers || 0,
      change: analytics.overview?.customersGrowth || 0,
      icon: Users,
      color: 'orange'
    }
  ]

  const serviceDistribution = [
    { name: 'Sea FCL', value: 45, color: '#3b82f6' },
    { name: 'Sea LCL', value: 20, color: '#10b981' },
    { name: 'Air Freight', value: 25, color: '#f59e0b' },
    { name: 'Express', value: 10, color: '#ef4444' }
  ]

  const routePerformance = [
    { route: 'Asia-US', volume: 120, revenue: 450000, growth: 15.2 },
    { route: 'Asia-Europe', volume: 95, revenue: 380000, growth: 8.7 },
    { route: 'Europe-US', volume: 78, revenue: 290000, growth: -2.1 },
    { route: 'Intra-Asia', volume: 156, revenue: 220000, growth: 22.5 },
    { route: 'Others', volume: 45, revenue: 125000, growth: 5.8 }
  ]

  const getKpiColor = (color) => {
    const colors = {
      green: 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400',
      blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400',
      purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400',
      orange: 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400'
    }
    return colors[color] || colors.blue
  }

  const formatTooltipValue = (value, name) => {
    if (name === 'revenue') return [`$${value.toLocaleString()}`, 'Revenue']
    return [value, name.charAt(0).toUpperCase() + name.slice(1)]
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Analytics Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Business insights and performance metrics
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-[120px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">Last 24h</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpiData.map((kpi, index) => {
          const Icon = kpi.icon
          const isPositive = kpi.change >= 0
          
          return (
            <motion.div
              key={kpi.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                        {kpi.title}
                      </p>
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">
                        {kpi.value}
                      </p>
                    </div>
                    <div className={`p-3 rounded-full ${getKpiColor(kpi.color)}`}>
                      <Icon className="h-6 w-6" />
                    </div>
                  </div>
                  <div className="mt-4 flex items-center">
                    {isPositive ? (
                      <TrendingUp className="h-4 w-4 text-green-500" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-500" />
                    )}
                    <span className={`text-sm font-medium ml-1 ${
                      isPositive ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {Math.abs(kpi.change)}%
                    </span>
                    <span className="text-sm text-gray-500 ml-1">vs last period</span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {/* Main Chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
      >
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Performance Trends</CardTitle>
              <CardDescription>
                {timeRange === '24h' ? 'Hourly' : timeRange === '7d' ? 'Daily' : 'Monthly'} performance metrics
              </CardDescription>
            </div>
            <Select value={chartType} onValueChange={setChartType}>
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="revenue">Revenue</SelectItem>
                <SelectItem value="quotes">Quotes</SelectItem>
                <SelectItem value="shipments">Shipments</SelectItem>
              </SelectContent>
            </Select>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              {chartType === 'revenue' ? (
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="period" />
                  <YAxis />
                  <Tooltip formatter={formatTooltipValue} />
                  <Area 
                    type="monotone" 
                    dataKey="revenue" 
                    stroke="#3b82f6" 
                    fill="#3b82f6" 
                    fillOpacity={0.1}
                  />
                </AreaChart>
              ) : (
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="period" />
                  <YAxis />
                  <Tooltip formatter={formatTooltipValue} />
                  <Bar 
                    dataKey={chartType} 
                    fill={chartType === 'quotes' ? '#10b981' : '#f59e0b'} 
                  />
                </BarChart>
              )}
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </motion.div>

      {/* Secondary Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Service Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <PieChartIcon className="h-5 w-5 mr-2" />
                Service Distribution
              </CardTitle>
              <CardDescription>Breakdown by service type</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={serviceDistribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {serviceDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${value}%`, 'Share']} />
                </PieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-2 mt-4">
                {serviceDistribution.map((entry, index) => (
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

        {/* Route Performance */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <BarChart3 className="h-5 w-5 mr-2" />
                Route Performance
              </CardTitle>
              <CardDescription>Top performing trade routes</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {routePerformance.map((route, index) => (
                  <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium">{route.route}</span>
                        <span className={`text-sm ${
                          route.growth >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {route.growth >= 0 ? '+' : ''}{route.growth}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm text-gray-500">
                        <span>{route.volume} shipments</span>
                        <span>${(route.revenue / 1000).toFixed(0)}k revenue</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.7 }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Activity className="h-5 w-5 mr-2" />
              Recent Activity
            </CardTitle>
            <CardDescription>Latest business activities and milestones</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {analytics.recentActivity?.map((activity, index) => (
                <div key={index} className="flex items-start space-x-3 p-3 rounded-lg border">
                  <div className={`p-2 rounded-full ${
                    activity.type === 'quote' ? 'bg-blue-100 text-blue-600' :
                    activity.type === 'shipment' ? 'bg-green-100 text-green-600' :
                    'bg-purple-100 text-purple-600'
                  }`}>
                    {activity.type === 'quote' ? <FileText className="h-4 w-4" /> :
                     activity.type === 'shipment' ? <Package className="h-4 w-4" /> :
                     <Users className="h-4 w-4" />}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{activity.message}</p>
                    <p className="text-xs text-gray-500">{activity.time}</p>
                  </div>
                </div>
              )) || (
                <p className="text-gray-500 text-center py-4">No recent activity</p>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

export default AnalyticsPage

