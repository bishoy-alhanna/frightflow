import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext({})

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

  useEffect(() => {
    // Check for existing session
    const savedUser = localStorage.getItem('admin-user')
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser))
      } catch (error) {
        localStorage.removeItem('admin-user')
      }
    }
    setLoading(false)
  }, [])

  const login = async (email, password) => {
    setLoading(true)
    try {
      // Mock authentication - in real app, this would call an API
      if (email === 'admin@freightflow.com' && password === 'admin123') {
        const adminUser = {
          id: 'admin-1',
          name: 'Admin User',
          email: 'admin@freightflow.com',
          role: 'admin',
          permissions: ['all'],
          avatar: null,
          lastLogin: new Date().toISOString()
        }
        
        setUser(adminUser)
        localStorage.setItem('admin-user', JSON.stringify(adminUser))
        
        return { success: true }
      } else if (email === 'ops@freightflow.com' && password === 'ops123') {
        const opsUser = {
          id: 'ops-1',
          name: 'Operations Manager',
          email: 'ops@freightflow.com',
          role: 'operations',
          permissions: ['quotes', 'shipments', 'customers'],
          avatar: null,
          lastLogin: new Date().toISOString()
        }
        
        setUser(opsUser)
        localStorage.setItem('admin-user', JSON.stringify(opsUser))
        
        return { success: true }
      } else {
        return { success: false, error: 'Invalid credentials' }
      }
    } catch (error) {
      return { success: false, error: 'Login failed' }
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem('admin-user')
  }

  const updateProfile = async (profileData) => {
    try {
      // Mock profile update
      const updatedUser = { ...user, ...profileData }
      setUser(updatedUser)
      localStorage.setItem('admin-user', JSON.stringify(updatedUser))
      return { success: true }
    } catch (error) {
      return { success: false, error: 'Profile update failed' }
    }
  }

  const hasPermission = (permission) => {
    if (!user) return false
    return user.permissions.includes('all') || user.permissions.includes(permission)
  }

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    logout,
    updateProfile,
    hasPermission
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

