'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { MessageCircle, BarChart3, Database, Sparkles, ArrowRight, Lightbulb } from 'lucide-react'
import Link from 'next/link'
import { SignInButton, SignUpButton, useUser } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import { Logo } from '@/components/ui/logo'
import { Button } from '@/components/ui/button'
import { useUserSync } from '@/hooks/use-user-sync'

export default function LandingPage() {
  const { isSignedIn, user } = useUser()
  const router = useRouter()
  
  // Sync user to database when they sign in
  useUserSync()
  
  const userEmail = user?.primaryEmailAddress?.emailAddress || 'user'

  React.useEffect(() => {
    if (isSignedIn) {
      router.push('/dashboard')
    }
  }, [isSignedIn, router])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-blue-950 to-purple-950">
      {/* Navigation */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800/50">
        <Link href="/" className="flex items-center">
          <Logo className="h-10" />
        </Link>
        <div className="flex items-center space-x-4">
          <SignInButton mode="modal">
            <Button variant="ghost" size="sm">
              Sign In
            </Button>
          </SignInButton>
          <SignUpButton mode="modal">
            <Button variant="primary" size="sm">
              Get Started
            </Button>
          </SignUpButton>
        </div>
      </nav>

      <div className="container mx-auto px-6 py-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-6xl md:text-7xl font-bold bg-gradient-to-r from-emerald-400 via-green-500 to-blue-500 bg-clip-text text-transparent mb-6"
          >
            Product Review Analysis
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-xl text-white/80 mb-8 max-w-2xl mx-auto"
          >
            Discover insights from customer reviews across Reddit, Twitter, and more. 
            Chat with your data using AI-powered analysis.
          </motion.p>

          {/* CTA Button */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="mb-16"
          >
            <SignUpButton mode="modal">
              <Button size="lg" className="hover:scale-105">
                <span>Start Analyzing</span>
                <ArrowRight className="w-5 h-5" />
              </Button>
            </SignUpButton>
          </motion.div>

          {/* Terminal Demo */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="max-w-3xl mx-auto mb-12"
          >
            <div className="bg-gray-900/50 rounded-lg border border-emerald-500/30 p-6 text-left">
              <div className="flex items-center mb-4">
                <div className="flex space-x-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                </div>
                <div className="ml-4 text-emerald-400/60 text-sm font-mono">{userEmail} ~ $</div>
              </div>
              <div className="font-mono text-sm space-y-2">
                <div className="text-emerald-400">$ What are the main complaints about our competitor? ✦</div>
                <div className="text-blue-400">→ Analyzing 1,247 reviews... Vector search complete...</div>
                <div className="text-white/80 flex items-start gap-2">
                  <Lightbulb className="w-4 h-4 mt-0.5 text-yellow-400 flex-shrink-0" />
                  <span>Top complaints: Slow customer support (342 mentions), Complex pricing (189 mentions), Limited integrations (156 mentions) ■</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Features */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="grid md:grid-cols-3 gap-8"
        >
          {/* AI Chat Analysis */}
          <div className="text-center p-6 bg-gray-900/30 rounded-xl border border-gray-800/50">
            <div className="w-16 h-16 bg-gradient-to-br from-emerald-500 to-green-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <MessageCircle className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-2xl font-bold text-white mb-4">AI Chat Analysis</h3>
            <p className="text-white/70 leading-relaxed">
              Ask questions about your product reviews in natural language. Get instant insights powered by RAG and LLMs.
            </p>
          </div>

          {/* Real-time Scraping */}
          <div className="text-center p-6 bg-gray-900/30 rounded-xl border border-gray-800/50">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <Database className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-2xl font-bold text-white mb-4">Multi-Source Scraping</h3>
            <p className="text-white/70 leading-relaxed">
              Collect reviews from Reddit, Twitter, and custom sources. Import CSV files or scrape automatically.
            </p>
          </div>

          {/* Visual Analytics */}
          <div className="text-center p-6 bg-gray-900/30 rounded-xl border border-gray-800/50">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <BarChart3 className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-2xl font-bold text-white mb-4">Visual Analytics</h3>
            <p className="text-white/70 leading-relaxed">
              Explore sentiment trends, discover product gaps, and track competitor mentions with interactive visualizations.
            </p>
          </div>
        </motion.div>

        {/* How It Works */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1.0 }}
          className="mt-20 text-center"
        >
          <h2 className="text-4xl font-bold text-white mb-12">How It Works</h2>
          <div className="grid md:grid-cols-4 gap-6 max-w-5xl mx-auto">
            <div className="relative">
              <div className="w-12 h-12 bg-emerald-500/20 border-2 border-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4 text-emerald-400 font-bold">
                1
              </div>
              <h4 className="text-white font-semibold mb-2">Add Company</h4>
              <p className="text-white/60 text-sm">Create a profile for the product you want to analyze</p>
            </div>
            <div className="relative">
              <div className="w-12 h-12 bg-emerald-500/20 border-2 border-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4 text-emerald-400 font-bold">
                2
              </div>
              <h4 className="text-white font-semibold mb-2">Collect Data</h4>
              <p className="text-white/60 text-sm">Scrape reviews or upload CSV files from various sources</p>
            </div>
            <div className="relative">
              <div className="w-12 h-12 bg-emerald-500/20 border-2 border-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4 text-emerald-400 font-bold">
                3
              </div>
              <h4 className="text-white font-semibold mb-2">Ask Questions</h4>
              <p className="text-white/60 text-sm">Chat with AI to discover insights from your data</p>
            </div>
            <div className="relative">
              <div className="w-12 h-12 bg-emerald-500/20 border-2 border-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4 text-emerald-400 font-bold">
                4
              </div>
              <h4 className="text-white font-semibold mb-2">Take Action</h4>
              <p className="text-white/60 text-sm">Use insights to improve your product strategy</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Footer */}
      <footer className="text-center py-8 text-white/40 text-sm border-t border-gray-800/50 mt-20">
        © 2025 NeedleAI. All rights reserved.
      </footer>
    </div>
  )
}
