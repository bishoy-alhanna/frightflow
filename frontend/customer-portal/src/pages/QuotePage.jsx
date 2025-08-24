import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { useToast } from '@/hooks/use-toast'
import { 
  Ship, 
  Plane, 
  Package, 
  MapPin, 
  Calendar,
  DollarSign,
  Clock,
  Plus,
  Minus,
  Info
} from 'lucide-react'
import { motion } from 'framer-motion'
import { useQuote } from '../contexts/QuoteContext'
import { useAuth } from '../contexts/AuthContext'

const QuotePage = () => {
  const { createQuote, createMockQuote, loading } = useQuote()
  const { isAuthenticated } = useAuth()
  const { toast } = useToast()
  const navigate = useNavigate()

  const [formData, setFormData] = useState({
    mode: '',
    service: '',
    origin: '',
    destination: '',
    containers: [{ type: '40HC', count: 1 }],
    cargo: {
      weightKg: '',
      volumeM3: '',
      description: ''
    },
    accessorials: [],
    preferredDate: '',
    notes: ''
  })

  const [quote, setQuote] = useState(null)

  const modes = [
    { value: 'SEA', label: 'Sea Freight', icon: Ship },
    { value: 'AIR', label: 'Air Freight', icon: Plane }
  ]

  const services = {
    SEA: [
      { value: 'FCL', label: 'Full Container Load (FCL)' },
      { value: 'LCL', label: 'Less than Container Load (LCL)' }
    ],
    AIR: [
      { value: 'AIR', label: 'Air Freight' }
    ]
  }

  const containerTypes = [
    { value: '20GP', label: '20ft General Purpose' },
    { value: '40GP', label: '40ft General Purpose' },
    { value: '40HC', label: '40ft High Cube' },
    { value: '45HC', label: '45ft High Cube' }
  ]

  const accessorialOptions = [
    { value: 'FUEL', label: 'Fuel Surcharge', description: 'Fuel adjustment factor' },
    { value: 'PORT_FEES', label: 'Port Handling Fees', description: 'Terminal and port charges' },
    { value: 'DOCUMENTATION', label: 'Documentation Fee', description: 'Bill of lading and customs docs' },
    { value: 'SECURITY', label: 'Security Screening', description: 'Cargo security inspection' },
    { value: 'INSURANCE', label: 'Cargo Insurance', description: 'Full cargo value protection' }
  ]

  const ports = [
    'SGSIN - Singapore',
    'HKHKG - Hong Kong',
    'CNSHA - Shanghai, China',
    'JPNGO - Nagoya, Japan',
    'KRPUS - Busan, South Korea',
    'USNYC - New York, USA',
    'USLAX - Los Angeles, USA',
    'NLRTM - Rotterdam, Netherlands',
    'DEHAM - Hamburg, Germany',
    'EGALY - Alexandria, Egypt'
  ]

  const handleInputChange = (field, value) => {
    if (field.includes('.')) {
      const [parent, child] = field.split('.')
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...prev[parent],
          [child]: value
        }
      }))
    } else {
      setFormData(prev => ({
        ...prev,
        [field]: value
      }))
    }
  }

  const handleContainerChange = (index, field, value) => {
    const newContainers = [...formData.containers]
    newContainers[index] = { ...newContainers[index], [field]: value }
    setFormData(prev => ({ ...prev, containers: newContainers }))
  }

  const addContainer = () => {
    setFormData(prev => ({
      ...prev,
      containers: [...prev.containers, { type: '40HC', count: 1 }]
    }))
  }

  const removeContainer = (index) => {
    if (formData.containers.length > 1) {
      const newContainers = formData.containers.filter((_, i) => i !== index)
      setFormData(prev => ({ ...prev, containers: newContainers }))
    }
  }

  const handleAccessorialChange = (accessorial, checked) => {
    if (checked) {
      setFormData(prev => ({
        ...prev,
        accessorials: [...prev.accessorials, accessorial]
      }))
    } else {
      setFormData(prev => ({
        ...prev,
        accessorials: prev.accessorials.filter(a => a !== accessorial)
      }))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!formData.mode || !formData.service || !formData.origin || !formData.destination) {
      toast({
        title: "Missing Information",
        description: "Please fill in all required fields.",
        variant: "destructive"
      })
      return
    }

    try {
      // Use mock quote for demo purposes
      const result = createMockQuote(formData)
      
      if (result.success) {
        setQuote(result.quote)
        toast({
          title: "Quote Generated!",
          description: "Your freight quote has been generated successfully.",
        })
      } else {
        throw new Error(result.error)
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to generate quote. Please try again.",
        variant: "destructive"
      })
    }
  }

  const handleAcceptQuote = () => {
    if (!isAuthenticated) {
      toast({
        title: "Login Required",
        description: "Please login to accept quotes and manage shipments.",
        variant: "destructive"
      })
      navigate('/login')
      return
    }

    toast({
      title: "Quote Accepted!",
      description: "Your quote has been accepted. We'll contact you shortly to proceed.",
    })
    navigate('/shipments')
  }

  return (
    <div className="min-h-screen py-8">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center space-y-4 mb-8">
            <h1 className="text-3xl lg:text-4xl font-bold">Get Instant Freight Quote</h1>
            <p className="text-xl text-muted-foreground">
              Fill in your shipment details and get competitive rates in seconds
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Quote Form */}
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Package className="h-5 w-5" />
                    <span>Shipment Details</span>
                  </CardTitle>
                  <CardDescription>
                    Provide your cargo information to get accurate pricing
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Mode and Service */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="mode">Transport Mode *</Label>
                        <Select value={formData.mode} onValueChange={(value) => handleInputChange('mode', value)}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select transport mode" />
                          </SelectTrigger>
                          <SelectContent>
                            {modes.map((mode) => {
                              const Icon = mode.icon
                              return (
                                <SelectItem key={mode.value} value={mode.value}>
                                  <div className="flex items-center space-x-2">
                                    <Icon className="h-4 w-4" />
                                    <span>{mode.label}</span>
                                  </div>
                                </SelectItem>
                              )
                            })}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="service">Service Type *</Label>
                        <Select 
                          value={formData.service} 
                          onValueChange={(value) => handleInputChange('service', value)}
                          disabled={!formData.mode}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select service type" />
                          </SelectTrigger>
                          <SelectContent>
                            {formData.mode && services[formData.mode]?.map((service) => (
                              <SelectItem key={service.value} value={service.value}>
                                {service.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Origin and Destination */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="origin">Origin Port *</Label>
                        <Select value={formData.origin} onValueChange={(value) => handleInputChange('origin', value)}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select origin port" />
                          </SelectTrigger>
                          <SelectContent>
                            {ports.map((port) => (
                              <SelectItem key={port} value={port.split(' - ')[0]}>
                                {port}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="destination">Destination Port *</Label>
                        <Select value={formData.destination} onValueChange={(value) => handleInputChange('destination', value)}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select destination port" />
                          </SelectTrigger>
                          <SelectContent>
                            {ports.map((port) => (
                              <SelectItem key={port} value={port.split(' - ')[0]}>
                                {port}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Container Details (FCL only) */}
                    {formData.service === 'FCL' && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <Label>Container Details</Label>
                          <Button type="button" variant="outline" size="sm" onClick={addContainer}>
                            <Plus className="h-4 w-4 mr-1" />
                            Add Container
                          </Button>
                        </div>
                        
                        {formData.containers.map((container, index) => (
                          <div key={index} className="flex items-center space-x-4 p-4 border rounded-lg">
                            <div className="flex-1">
                              <Select 
                                value={container.type} 
                                onValueChange={(value) => handleContainerChange(index, 'type', value)}
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {containerTypes.map((type) => (
                                    <SelectItem key={type.value} value={type.value}>
                                      {type.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="w-20">
                              <Input
                                type="number"
                                min="1"
                                value={container.count}
                                onChange={(e) => handleContainerChange(index, 'count', parseInt(e.target.value) || 1)}
                                placeholder="Qty"
                              />
                            </div>
                            {formData.containers.length > 1 && (
                              <Button 
                                type="button" 
                                variant="outline" 
                                size="sm"
                                onClick={() => removeContainer(index)}
                              >
                                <Minus className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Cargo Details */}
                    <div className="space-y-4">
                      <Label>Cargo Information</Label>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="weight">Weight (kg)</Label>
                          <Input
                            id="weight"
                            type="number"
                            value={formData.cargo.weightKg}
                            onChange={(e) => handleInputChange('cargo.weightKg', e.target.value)}
                            placeholder="Enter weight in kg"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="volume">Volume (m³)</Label>
                          <Input
                            id="volume"
                            type="number"
                            step="0.1"
                            value={formData.cargo.volumeM3}
                            onChange={(e) => handleInputChange('cargo.volumeM3', e.target.value)}
                            placeholder="Enter volume in m³"
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="description">Cargo Description</Label>
                        <Textarea
                          id="description"
                          value={formData.cargo.description}
                          onChange={(e) => handleInputChange('cargo.description', e.target.value)}
                          placeholder="Describe your cargo (e.g., electronics, textiles, machinery)"
                          rows={3}
                        />
                      </div>
                    </div>

                    {/* Accessorial Services */}
                    <div className="space-y-4">
                      <Label>Additional Services</Label>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {accessorialOptions.map((option) => (
                          <div key={option.value} className="flex items-start space-x-3 p-3 border rounded-lg">
                            <Checkbox
                              id={option.value}
                              checked={formData.accessorials.includes(option.value)}
                              onCheckedChange={(checked) => handleAccessorialChange(option.value, checked)}
                            />
                            <div className="flex-1">
                              <Label htmlFor={option.value} className="font-medium cursor-pointer">
                                {option.label}
                              </Label>
                              <p className="text-sm text-muted-foreground">{option.description}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Additional Information */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="preferredDate">Preferred Ship Date</Label>
                        <Input
                          id="preferredDate"
                          type="date"
                          value={formData.preferredDate}
                          onChange={(e) => handleInputChange('preferredDate', e.target.value)}
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="notes">Special Instructions</Label>
                      <Textarea
                        id="notes"
                        value={formData.notes}
                        onChange={(e) => handleInputChange('notes', e.target.value)}
                        placeholder="Any special requirements or instructions"
                        rows={3}
                      />
                    </div>

                    <Button type="submit" className="w-full" size="lg" disabled={loading}>
                      {loading ? 'Generating Quote...' : 'Get Quote'}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </div>

            {/* Quote Result */}
            <div className="space-y-6">
              {quote ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                >
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <DollarSign className="h-5 w-5" />
                        <span>Your Quote</span>
                      </CardTitle>
                      <CardDescription>
                        Quote ID: {quote.quote_id}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-muted-foreground">Route</span>
                          <span className="font-medium">{quote.origin} → {quote.destination}</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-muted-foreground">Service</span>
                          <Badge variant="secondary">{quote.mode} {quote.service}</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-muted-foreground">Status</span>
                          <Badge variant="default">{quote.status}</Badge>
                        </div>
                      </div>

                      <Separator />

                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-muted-foreground">Base Rate</span>
                          <span>${quote.base_amount?.toLocaleString()}</span>
                        </div>
                        {quote.items?.filter(item => item.item_type === 'SURCHARGE').map((item, index) => (
                          <div key={index} className="flex justify-between items-center">
                            <span className="text-sm text-muted-foreground">{item.description}</span>
                            <span>${item.total_price?.toLocaleString()}</span>
                          </div>
                        ))}
                        <Separator />
                        <div className="flex justify-between items-center text-lg font-bold">
                          <span>Total</span>
                          <span className="text-primary">${quote.total_amount?.toLocaleString()}</span>
                        </div>
                      </div>

                      <div className="space-y-2 text-sm text-muted-foreground">
                        <div className="flex items-center space-x-2">
                          <Clock className="h-4 w-4" />
                          <span>Valid until: {new Date(quote.valid_until).toLocaleDateString()}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Info className="h-4 w-4" />
                          <span>Transit time: 18-22 days (estimated)</span>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Button className="w-full" onClick={handleAcceptQuote}>
                          Accept Quote
                        </Button>
                        <Button variant="outline" className="w-full">
                          Download PDF
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ) : (
                <Card>
                  <CardContent className="p-6 text-center">
                    <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">
                      Fill in the form to get your instant quote
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Info Card */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Why Choose Us?</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center space-x-2 text-sm">
                    <Clock className="h-4 w-4 text-green-500" />
                    <span>Instant quotes in seconds</span>
                  </div>
                  <div className="flex items-center space-x-2 text-sm">
                    <MapPin className="h-4 w-4 text-green-500" />
                    <span>500+ ports worldwide</span>
                  </div>
                  <div className="flex items-center space-x-2 text-sm">
                    <Package className="h-4 w-4 text-green-500" />
                    <span>Real-time tracking</span>
                  </div>
                  <div className="flex items-center space-x-2 text-sm">
                    <DollarSign className="h-4 w-4 text-green-500" />
                    <span>Competitive rates</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default QuotePage

