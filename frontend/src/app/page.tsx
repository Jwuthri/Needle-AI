'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { MessageCircle, Code, Zap } from 'lucide-react'
import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-blue-950 to-purple-950">
      {/* Navigation */}
      <nav className="flex items-center justify-between px-6 py-4">
        <div className="text-white font-bold tracking-wider">
          AI Agent App
        </div>
        <Link href="/chat">
          <button className="text-white/80 hover:text-white transition-colors">
            Go to Chat
          </button>
        </Link>
      </nav>

      <div className="container mx-auto px-6 py-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-6xl md:text-7xl font-bold bg-gradient-to-r from-purple-400 via-pink-500 to-blue-500 bg-clip-text text-transparent mb-6"
          >
            AI-Powered Chat
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-xl text-white/80 mb-8 max-w-2xl mx-auto"
          >
            Chat with advanced AI. Get instant, intelligent responses to any question.
          </motion.p>

          {/* Terminal Demo */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="max-w-3xl mx-auto mb-12"
          >
            <div className="bg-gray-900/50 rounded-lg border border-gray-700/50 p-6 text-left">
              <div className="flex items-center mb-4">
                <div className="flex space-x-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                </div>
                <div className="ml-4 text-white/60 text-sm font-mono">ai-chat-terminal</div>
              </div>
              <div className="font-mono text-sm space-y-2">
                <div className="text-green-400">$ What's the best approach for learning machine learning? ✦</div>
                <div className="text-blue-400">Analyzing query... Generating comprehensive response...</div>
                <div className="text-yellow-400">💬 Response ready! Here's a detailed learning path for you. ■</div>
              </div>
            </div>
          </motion.div>

          {/* Get Started Button */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="mb-16"
          >
            <Link href="/chat">
              <button className="px-8 py-4 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-medium rounded-lg transition-all duration-200 hover:scale-105 text-lg">
                Start Chatting →
              </button>
            </Link>
          </motion.div>
        </div>

        {/* Features */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="grid md:grid-cols-3 gap-8"
        >
          {/* Intelligent Conversations */}
          <div className="text-center p-6">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <MessageCircle className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-2xl font-bold text-white mb-4">Smart Conversations</h3>
            <p className="text-white/70 leading-relaxed">
              Engage in natural, intelligent conversations with advanced AI technology
            </p>
          </div>

          {/* Instant Responses */}
          <div className="text-center p-6">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <Zap className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-2xl font-bold text-white mb-4">Lightning Fast</h3>
            <p className="text-white/70 leading-relaxed">
              Get instant responses with real-time processing and optimized performance
            </p>
          </div>

          {/* Always Available */}
          <div className="text-center p-6">
            <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <Code className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-2xl font-bold text-white mb-4">Always Available</h3>
            <p className="text-white/70 leading-relaxed">
              24/7 availability with persistent conversations and session history
            </p>
          </div>
        </motion.div>
      </div>

      {/* Footer */}
      <footer className="text-center py-8 text-white/40 text-sm">
        © 2025 Ai Agent App. All rights reserved.
      </footer>
    </div>
  )
}
