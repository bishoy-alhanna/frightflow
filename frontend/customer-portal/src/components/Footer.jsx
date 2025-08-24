import { Link } from 'react-router-dom'
import { Ship, Mail, Phone, MapPin } from 'lucide-react'

const Footer = () => {
  return (
    <footer className="bg-muted/50 border-t">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Company Info */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Ship className="h-6 w-6 text-primary" />
              <span className="text-lg font-bold">FreightFlow</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Your trusted partner for global freight and logistics solutions. 
              Streamlining shipping with technology and expertise.
            </p>
            <div className="flex space-x-4">
              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                <Mail className="h-4 w-4" />
                <span>support@freightflow.com</span>
              </div>
            </div>
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <Phone className="h-4 w-4" />
              <span>+1 (555) 123-4567</span>
            </div>
          </div>

          {/* Services */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Services</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/quote" className="hover:text-foreground transition-colors">Sea Freight</Link></li>
              <li><Link to="/quote" className="hover:text-foreground transition-colors">Air Freight</Link></li>
              <li><Link to="/quote" className="hover:text-foreground transition-colors">FCL Shipping</Link></li>
              <li><Link to="/quote" className="hover:text-foreground transition-colors">LCL Shipping</Link></li>
              <li><Link to="/quote" className="hover:text-foreground transition-colors">Customs Clearance</Link></li>
            </ul>
          </div>

          {/* Company */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Company</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/about" className="hover:text-foreground transition-colors">About Us</Link></li>
              <li><Link to="/contact" className="hover:text-foreground transition-colors">Contact</Link></li>
              <li><Link to="/careers" className="hover:text-foreground transition-colors">Careers</Link></li>
              <li><Link to="/news" className="hover:text-foreground transition-colors">News</Link></li>
              <li><Link to="/partners" className="hover:text-foreground transition-colors">Partners</Link></li>
            </ul>
          </div>

          {/* Support */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Support</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/help" className="hover:text-foreground transition-colors">Help Center</Link></li>
              <li><Link to="/tracking" className="hover:text-foreground transition-colors">Track Shipment</Link></li>
              <li><Link to="/documentation" className="hover:text-foreground transition-colors">Documentation</Link></li>
              <li><Link to="/api" className="hover:text-foreground transition-colors">API Reference</Link></li>
              <li><Link to="/status" className="hover:text-foreground transition-colors">System Status</Link></li>
            </ul>
          </div>
        </div>

        {/* Bottom section */}
        <div className="mt-8 pt-8 border-t border-border">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <MapPin className="h-4 w-4" />
              <span>Global Headquarters: Singapore • Regional Offices: New York, London, Hong Kong</span>
            </div>
            <div className="flex space-x-6 text-sm text-muted-foreground">
              <Link to="/privacy" className="hover:text-foreground transition-colors">Privacy Policy</Link>
              <Link to="/terms" className="hover:text-foreground transition-colors">Terms of Service</Link>
              <Link to="/cookies" className="hover:text-foreground transition-colors">Cookie Policy</Link>
            </div>
          </div>
          <div className="mt-4 text-center text-sm text-muted-foreground">
            <p>&copy; 2025 FreightFlow. All rights reserved.</p>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer

