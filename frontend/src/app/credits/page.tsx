'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Coins, CreditCard, TrendingDown, TrendingUp } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'

const pricingTiers = [
  { id: 'free', name: 'Free Trial', credits: 1000, price: 0, popular: false, isFree: true },
  { id: '1', name: 'Starter', credits: 1000, price: 10, popular: false },
  { id: '2', name: 'Professional', credits: 5000, price: 40, popular: true, savings: '20% off' },
  { id: '3', name: 'Enterprise', credits: 15000, price: 100, popular: false, savings: '33% off' },
]

export default function CreditsPage() {
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [balance, setBalance] = useState(0)
  const [transactions, setTransactions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [purchasing, setPurchasing] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    if (!isSignedIn) {
      console.log('Not signed in, skipping fetch')
      return
    }
    
    console.log('fetchData called, isSignedIn:', isSignedIn)
    
    try {
      const token = await getToken()
      console.log('Token obtained:', token ? 'Yes' : 'No')
      
      const api = createApiClient(token)
      
      // Fetch only credits, skip transactions for now
      const creditsData = await api.getCreditBalance()

      console.log('Raw credits data from API:', creditsData)
      console.log('Type of creditsData:', typeof creditsData)
      console.log('creditsData.credits_available:', creditsData.credits_available)
      console.log('Type of credits_available:', typeof creditsData.credits_available)

      const balanceValue = creditsData.credits_available || 0
      console.log('Setting balance to:', balanceValue)
      
      setBalance(balanceValue)
      setTransactions([]) // Set empty transactions for now
      
      console.log('Balance state should now be:', balanceValue)
    } catch (error) {
      console.error('Failed to fetch credit data:', error)
    } finally {
      setLoading(false)
    }
  }, [isSignedIn, getToken])

  const handlePurchase = async (tier: typeof pricingTiers[0]) => {
    if (tier.isFree) {
      // Handle free credits
      setPurchasing(tier.id)
      setError(null)
      
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const response = await api.addFreeCredits(tier.credits)
        
        console.log('Free credits response:', response)
        
        // Update balance immediately from response
        setBalance(response.credits_available)
        
        // Refresh full data
        await fetchData()
        
        // Show success (you could add a toast notification here)
        alert(`Successfully added ${tier.credits} free credits! New balance: ${response.credits_available}`)
      } catch (err: any) {
        console.error('Error adding free credits:', err)
        setError(err.message || 'Failed to add free credits')
      } finally {
        setPurchasing(null)
      }
    } else {
      // Handle paid purchase (placeholder for now)
      alert('Paid purchases not implemented yet')
    }
  }

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  useEffect(() => {
    console.log('useEffect triggered, isSignedIn:', isSignedIn, 'isLoaded:', isLoaded)
    if (isSignedIn && isLoaded) {
      fetchData()
    }
  }, [isSignedIn, isLoaded, fetchData])

  if (!isLoaded || !isSignedIn || loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="text-emerald-400 text-lg">Loading credits...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Credits</h1>
          <p className="text-white/60">Manage your account balance and purchase credits</p>
        </div>

        {/* Current Balance */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-emerald-500/10 to-green-600/10 border-2 border-emerald-500/30 rounded-2xl p-8 mb-8"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="text-white/60 text-sm mb-2">Current Balance</div>
              <div className="text-6xl font-bold text-white mb-2">
                {balance.toLocaleString()}
              </div>
              <div className="text-emerald-400 text-sm">credits available</div>
            </div>
            <div className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center">
              <Coins className="w-10 h-10 text-emerald-400" />
            </div>
          </div>
        </motion.div>

        {/* Pricing Tiers */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-6">Purchase Credits</h2>
          
          {error && (
            <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400">
              {error}
            </div>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {pricingTiers.map((tier, index) => (
              <motion.div
                key={tier.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`relative bg-gray-900/50 border rounded-xl p-6 hover:border-emerald-500/50 transition-all ${
                  tier.popular ? 'border-emerald-500/50 scale-105' : 'border-gray-800/50'
                }`}
              >
                {tier.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-emerald-500 text-white text-xs font-semibold rounded-full">
                    POPULAR
                  </div>
                )}
                {tier.isFree && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-blue-500 text-white text-xs font-semibold rounded-full">
                    FREE
                  </div>
                )}
                
                <div className="text-center mb-6">
                  <h3 className="text-xl font-bold text-white mb-2">{tier.name}</h3>
                  <div className="text-4xl font-bold text-white mb-1">{tier.credits.toLocaleString()}</div>
                  <div className="text-white/40 text-sm mb-4">credits</div>
                  <div className={`text-2xl font-bold ${tier.isFree ? 'text-blue-400' : 'text-emerald-400'}`}>
                    {tier.isFree ? 'FREE' : `$${tier.price}`}
                  </div>
                  {tier.savings && (
                    <div className="text-emerald-400 text-xs mt-1">{tier.savings}</div>
                  )}
                </div>

                <button
                  onClick={() => handlePurchase(tier)}
                  disabled={purchasing === tier.id}
                  className={`w-full py-3 rounded-xl font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                    tier.isFree
                      ? 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white'
                      : tier.popular
                      ? 'bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 text-white'
                      : 'bg-gray-800 hover:bg-gray-700 text-white'
                  }`}
                >
                  {purchasing === tier.id ? 'Processing...' : tier.isFree ? 'Claim Free Credits' : 'Purchase'}
                </button>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Transaction History */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6"
        >
          <h2 className="text-xl font-bold text-white mb-6">Transaction History</h2>
          
          {transactions.length > 0 ? (
            <div className="space-y-3">
              {transactions.map((transaction) => (
                <div
                  key={transaction.id}
                  className="flex items-center justify-between p-4 bg-gray-800/30 border border-gray-700/30 rounded-xl"
                >
                  <div className="flex items-center space-x-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      transaction.type === 'purchase'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-red-500/10 text-red-400'
                    }`}>
                      {transaction.type === 'purchase' ? (
                        <TrendingUp className="w-5 h-5" />
                      ) : (
                        <TrendingDown className="w-5 h-5" />
                      )}
                    </div>
                    <div>
                      <div className="text-white font-medium">{transaction.description}</div>
                      <div className="text-white/40 text-sm">
                        {new Date(transaction.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`font-semibold ${
                      transaction.type === 'purchase' ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                      {transaction.type === 'purchase' ? '+' : '-'}{Math.abs(transaction.amount).toLocaleString()}
                    </div>
                    <div className="text-white/40 text-sm">
                      Balance: {transaction.balance_after.toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-white/40">
              No transactions yet
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}

