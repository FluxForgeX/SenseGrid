import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useStore from '../store/useStore'
import { motion } from 'framer-motion'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const login = useStore(state => state.login)
  const navigate = useNavigate()

  const handleSubmit = (e) => {
    e.preventDefault()
    // Mock login
    if (email && password) {
      login({ name: 'User', email })
      navigate('/dashboard')
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-gray-800 p-8 rounded-2xl shadow-2xl w-full max-w-md border border-gray-700"
      >
        <h2 className="text-3xl font-bold text-white mb-6 text-center">Welcome Back</h2>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-gray-400 mb-2">Email</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-teal-500 transition"
              placeholder="you@example.com"
              required
            />
          </div>
          <div>
            <label className="block text-gray-400 mb-2">Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-teal-500 transition"
              placeholder="••••••••"
              required
            />
          </div>
          <button type="submit" className="w-full bg-teal-500 hover:bg-teal-600 text-white font-bold py-3 rounded-lg transition transform hover:scale-[1.02]">
            Log In
          </button>
        </form>
        <p className="mt-6 text-center text-gray-400">
          Don't have an account? <Link to="/register" className="text-teal-400 hover:underline">Sign up</Link>
        </p>
      </motion.div>
    </div>
  )
}
