import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import './App.css'

// Components
import Header from './components/Header'
import Footer from './components/Footer'
import HomePage from './pages/HomePage'
import QuotePage from './pages/QuotePage'
import ShipmentsPage from './pages/ShipmentsPage'
import ProfilePage from './pages/ProfilePage'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import { Toaster } from '@/components/ui/toaster'

// Context
import { AuthProvider } from './contexts/AuthContext'
import { QuoteProvider } from './contexts/QuoteContext'

function App() {
  const [theme, setTheme] = useState('light')

  useEffect(() => {
    // Check for saved theme preference or default to light
    const savedTheme = localStorage.getItem('theme') || 'light'
    setTheme(savedTheme)
    document.documentElement.classList.toggle('dark', savedTheme === 'dark')
  }, [])

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
    localStorage.setItem('theme', newTheme)
    document.documentElement.classList.toggle('dark', newTheme === 'dark')
  }

  return (
    <AuthProvider>
      <QuoteProvider>
        <Router>
          <div className="min-h-screen bg-background text-foreground">
            <Header theme={theme} toggleTheme={toggleTheme} />
            <main className="flex-1">
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/quote" element={<QuotePage />} />
                <Route path="/shipments" element={<ShipmentsPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
              </Routes>
            </main>
            <Footer />
            <Toaster />
          </div>
        </Router>
      </QuoteProvider>
    </AuthProvider>
  )
}

export default App

