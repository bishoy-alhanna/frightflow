import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(null)

  useEffect(() => {
    // Check for existing token on app load
    const savedToken = localStorage.getItem('auth_token')
    const savedUser = localStorage.getItem('user_data')
    
    if (savedToken && savedUser) {
      setToken(savedToken)
      setUser(JSON.parse(savedUser))
    }
    setLoading(false)
  }, [])

  const login = async (email, password) => {
    try {
      // For demo purposes, simulate login
      // In production, this would call the actual auth API
      const mockUser = {
        id: 'user123',
        email: email,
        name: 'John Doe',
        company: 'Acme Corp',
        role: 'customer'
      }
      
      const mockToken = 'mock-jwt-token-' + Date.now()
      
      setUser(mockUser)
      setToken(mockToken)
      localStorage.setItem('auth_token', mockToken)
      localStorage.setItem('user_data', JSON.stringify(mockUser))
      
      return { success: true, user: mockUser }
    } catch (error) {
      console.error('Login error:', error)
      return { success: false, error: error.message }
    }
  }

  const signup = async (userData) => {
    try {
      // For demo purposes, simulate signup
      const mockUser = {
        id: 'user' + Date.now(),
        email: userData.email,
        name: userData.name,
        company: userData.company,
        role: 'customer'
      }
      
      const mockToken = 'mock-jwt-token-' + Date.now()
      
      setUser(mockUser)
      setToken(mockToken)
      localStorage.setItem('auth_token', mockToken)
      localStorage.setItem('user_data', JSON.stringify(mockUser))
      
      return { success: true, user: mockUser }
    } catch (error) {
      console.error('Signup error:', error)
      return { success: false, error: error.message }
    }
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_data')
  }

  const updateProfile = async (profileData) => {
    try {
      const updatedUser = { ...user, ...profileData }
      setUser(updatedUser)
      localStorage.setItem('user_data', JSON.stringify(updatedUser))
      return { success: true, user: updatedUser }
    } catch (error) {
      console.error('Profile update error:', error)
      return { success: false, error: error.message }
    }
  }

  const value = {
    user,
    token,
    loading,
    login,
    signup,
    logout,
    updateProfile,
    isAuthenticated: !!user
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

