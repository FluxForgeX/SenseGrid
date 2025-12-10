import React from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white flex flex-col">
      <nav className="p-6 flex justify-between items-center max-w-7xl mx-auto w-full">
        <div className="text-2xl font-bold text-teal-400">SenseGrid</div>
        <div className="space-x-4">
          <Link to="/login" className="hover:text-teal-300 transition">Login</Link>
          <Link to="/register" className="bg-teal-500 hover:bg-teal-600 px-4 py-2 rounded-lg transition">Get Started</Link>
        </div>
      </nav>

      <main className="flex-grow flex items-center justify-center px-4">
        <div className="max-w-4xl mx-auto text-center">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-5xl md:text-7xl font-extrabold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-teal-400 to-blue-500"
          >
            Smart Living, Simplified.
          </motion.h1>
          
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-xl text-gray-300 mb-10 max-w-2xl mx-auto"
          >
            Monitor and control your home environment with ease. Real-time data, smart automation, and intuitive design.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <Link to="/register" className="bg-teal-500 hover:bg-teal-600 text-white text-lg px-8 py-4 rounded-full font-semibold shadow-lg hover:shadow-teal-500/30 transition transform hover:scale-105">
              Start Your Journey
            </Link>
          </motion.div>
        </div>
      </main>

      <footer className="p-6 text-center text-gray-500">
        &copy; {new Date().getFullYear()} SenseGrid. All rights reserved.
      </footer>
    </div>
  )
}
