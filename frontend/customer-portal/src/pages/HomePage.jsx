import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  Ship, 
  Plane, 
  Clock, 
  Shield, 
  Globe, 
  TrendingUp,
  CheckCircle,
  ArrowRight,
  Star,
  Users,
  Package,
  Zap
} from 'lucide-react'
import { motion } from 'framer-motion'

const HomePage = () => {
  const features = [
    {
      icon: Clock,
      title: 'Instant Quotes',
      description: 'Get accurate freight quotes in seconds with our AI-powered pricing engine.'
    },
    {
      icon: Globe,
      title: 'Global Network',
      description: 'Access to 500+ ports worldwide with reliable carrier partnerships.'
    },
    {
      icon: Shield,
      title: 'Secure & Insured',
      description: 'Your cargo is protected with comprehensive insurance coverage.'
    },
    {
      icon: TrendingUp,
      title: 'Real-time Tracking',
      description: 'Monitor your shipments with live updates and notifications.'
    }
  ]

  const services = [
    {
      icon: Ship,
      title: 'Sea Freight',
      description: 'Cost-effective ocean shipping for FCL and LCL cargo',
      features: ['FCL & LCL Options', 'Door-to-Door Service', 'Customs Clearance'],
      badge: 'Most Popular'
    },
    {
      icon: Plane,
      title: 'Air Freight',
      description: 'Fast and reliable air cargo services worldwide',
      features: ['Express Delivery', 'Temperature Control', 'Dangerous Goods'],
      badge: 'Fastest'
    },
    {
      icon: Package,
      title: 'Logistics',
      description: 'End-to-end supply chain management solutions',
      features: ['Warehousing', 'Distribution', 'Inventory Management'],
      badge: 'Complete'
    }
  ]

  const stats = [
    { label: 'Shipments Delivered', value: '50K+', icon: Package },
    { label: 'Happy Customers', value: '2K+', icon: Users },
    { label: 'Countries Served', value: '100+', icon: Globe },
    { label: 'Average Rating', value: '4.9', icon: Star }
  ]

  const testimonials = [
    {
      name: 'Sarah Johnson',
      company: 'TechCorp Inc.',
      content: 'FreightFlow has transformed our shipping operations. The instant quotes and tracking features are game-changers.',
      rating: 5
    },
    {
      name: 'Michael Chen',
      company: 'Global Imports Ltd.',
      content: 'Reliable, fast, and cost-effective. Their customer service is exceptional and they handle everything seamlessly.',
      rating: 5
    },
    {
      name: 'Emma Rodriguez',
      company: 'Fashion Forward',
      content: 'The best freight platform we\'ve used. Real-time tracking and competitive pricing make it our go-to choice.',
      rating: 5
    }
  ]

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-primary/10 via-background to-secondary/10 py-20 lg:py-32">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="space-y-8"
            >
              <div className="space-y-4">
                <Badge variant="secondary" className="w-fit">
                  <Zap className="w-3 h-3 mr-1" />
                  Powered by AI
                </Badge>
                <h1 className="text-4xl lg:text-6xl font-bold tracking-tight">
                  Ship Smarter with{' '}
                  <span className="text-primary">FreightFlow</span>
                </h1>
                <p className="text-xl text-muted-foreground max-w-lg">
                  Get instant freight quotes, track shipments in real-time, and manage your global logistics with our intelligent platform.
                </p>
              </div>
              
              <div className="flex flex-col sm:flex-row gap-4">
                <Button size="lg" asChild className="text-lg px-8">
                  <Link to="/quote">
                    Get Instant Quote
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Link>
                </Button>
                <Button size="lg" variant="outline" asChild className="text-lg px-8">
                  <Link to="/signup">Start Free Trial</Link>
                </Button>
              </div>

              <div className="flex items-center space-x-6 text-sm text-muted-foreground">
                <div className="flex items-center space-x-1">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>No setup fees</span>
                </div>
                <div className="flex items-center space-x-1">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>24/7 support</span>
                </div>
                <div className="flex items-center space-x-1">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Global coverage</span>
                </div>
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="relative"
            >
              <div className="bg-card border rounded-2xl p-8 shadow-2xl">
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold">Quick Quote</h3>
                    <Badge variant="secondary">Live Pricing</Badge>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">From</label>
                      <div className="p-3 bg-muted rounded-lg">Singapore</div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">To</label>
                      <div className="p-3 bg-muted rounded-lg">New York</div>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Service Type</label>
                    <div className="p-3 bg-muted rounded-lg">Sea Freight - FCL</div>
                  </div>
                  
                  <div className="bg-primary/10 border border-primary/20 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Estimated Cost</span>
                      <span className="text-2xl font-bold text-primary">$2,450</span>
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      Transit time: 18-22 days
                    </div>
                  </div>
                  
                  <Button className="w-full" asChild>
                    <Link to="/quote">Get Detailed Quote</Link>
                  </Button>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 bg-muted/30">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {stats.map((stat, index) => {
              const Icon = stat.icon
              return (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className="text-center space-y-2"
                >
                  <Icon className="h-8 w-8 text-primary mx-auto" />
                  <div className="text-3xl font-bold">{stat.value}</div>
                  <div className="text-sm text-muted-foreground">{stat.label}</div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-4 mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold">Why Choose FreightFlow?</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Experience the future of freight forwarding with our cutting-edge platform
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon
              return (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                >
                  <Card className="h-full hover:shadow-lg transition-shadow">
                    <CardHeader className="text-center">
                      <Icon className="h-12 w-12 text-primary mx-auto mb-4" />
                      <CardTitle className="text-xl">{feature.title}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <CardDescription className="text-center">
                        {feature.description}
                      </CardDescription>
                    </CardContent>
                  </Card>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Services Section */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-4 mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold">Our Services</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Comprehensive logistics solutions tailored to your business needs
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {services.map((service, index) => {
              const Icon = service.icon
              return (
                <motion.div
                  key={service.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                >
                  <Card className="h-full hover:shadow-lg transition-shadow relative">
                    {service.badge && (
                      <Badge className="absolute top-4 right-4 z-10">
                        {service.badge}
                      </Badge>
                    )}
                    <CardHeader>
                      <Icon className="h-12 w-12 text-primary mb-4" />
                      <CardTitle className="text-2xl">{service.title}</CardTitle>
                      <CardDescription className="text-base">
                        {service.description}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <ul className="space-y-2">
                        {service.features.map((feature) => (
                          <li key={feature} className="flex items-center space-x-2">
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            <span className="text-sm">{feature}</span>
                          </li>
                        ))}
                      </ul>
                      <Button className="w-full" variant="outline" asChild>
                        <Link to="/quote">Get Quote</Link>
                      </Button>
                    </CardContent>
                  </Card>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-4 mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold">What Our Customers Say</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Join thousands of satisfied customers who trust FreightFlow
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={testimonial.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className="h-full">
                  <CardContent className="p-6 space-y-4">
                    <div className="flex space-x-1">
                      {[...Array(testimonial.rating)].map((_, i) => (
                        <Star key={i} className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                      ))}
                    </div>
                    <p className="text-muted-foreground italic">
                      "{testimonial.content}"
                    </p>
                    <div>
                      <p className="font-semibold">{testimonial.name}</p>
                      <p className="text-sm text-muted-foreground">{testimonial.company}</p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary text-primary-foreground">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="space-y-8"
          >
            <h2 className="text-3xl lg:text-4xl font-bold">
              Ready to Transform Your Shipping?
            </h2>
            <p className="text-xl opacity-90 max-w-2xl mx-auto">
              Join thousands of businesses that have streamlined their logistics with FreightFlow. 
              Get started today with instant quotes and real-time tracking.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" variant="secondary" asChild className="text-lg px-8">
                <Link to="/quote">Get Your Quote Now</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="text-lg px-8 border-primary-foreground text-primary-foreground hover:bg-primary-foreground hover:text-primary">
                <Link to="/signup">Start Free Trial</Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  )
}

export default HomePage

