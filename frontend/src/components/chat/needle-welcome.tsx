'use client'

import { useEffect, useRef } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'
import { Target, MessageCircle, Trophy, Sparkles, Database } from 'lucide-react'

interface NeedleWelcomeProps {
  onPromptSelect: (prompt: string) => void
  companySelected: boolean
}

const iconComponents = {
  Target,
  MessageCircle,
  Trophy,
  Sparkles,
  Database,
}

const prompts = [
  { icon: 'Target', title: 'Product Gaps', prompt: 'What are the main product gaps mentioned in reviews?' },
  { icon: 'MessageCircle', title: 'Sentiment', prompt: 'What is the overall sentiment of our reviews?' },
  { icon: 'Trophy', title: 'Competitors', prompt: 'Which competitors are mentioned most often?' },
  { icon: 'Sparkles', title: 'Features', prompt: 'What features are customers requesting?' },
  { icon: 'Database', title: 'Data', prompt: 'What are my datasets?' },
  { icon: 'Database', title: 'Data', prompt: 'Can you show me trends in my datasets' },
]

export function NeedleWelcome({ onPromptSelect, companySelected }: NeedleWelcomeProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)
  
  const needleX = useSpring(mouseX, { stiffness: 120, damping: 25 })
  const needleY = useSpring(mouseY, { stiffness: 120, damping: 25 })

  useEffect(() => {
    if (!containerRef.current) return

    const handleMouseMove = (e: MouseEvent) => {
      const rect = containerRef.current?.getBoundingClientRect()
      if (!rect) return

      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      
      // Smooth dampened movement - needle continuously follows cursor
      const dampening = 0.15
      mouseX.set((e.clientX - centerX) * dampening)
      mouseY.set((e.clientY - centerY) * dampening)
    }

    window.addEventListener('mousemove', handleMouseMove)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
    }
  }, [mouseX, mouseY])

  return (
    <div ref={containerRef} style={styles.container}>
      {/* Animated Background Circles */}
      <div style={styles.circlesContainer}>
        {[1, 2, 3, 4, 5].map((i) => (
          <motion.div
            key={i}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ 
              scale: [1, 1.2, 1],
              opacity: [0.15, 0.08, 0.15],
            }}
            transition={{ 
              duration: 3 + i * 0.5,
              delay: i * 0.3,
              repeat: Infinity,
              repeatDelay: 0,
              ease: "easeInOut",
            }}
            style={{
              ...styles.circle,
              width: `${i * 90}px`,
              height: `${i * 90}px`,
            }}
          />
        ))}
      </div>

      {/* Scanning Lines */}
      <div style={styles.scanContainer}>
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            initial={{ rotate: i * 120, opacity: 0 }}
            animate={{ 
              rotate: i * 120 + 360,
              opacity: [0, 0.3, 0],
            }}
            transition={{ 
              duration: 8,
              delay: i * 2.5,
              repeat: Infinity,
              ease: "linear",
            }}
            style={styles.scanLine}
          />
        ))}
      </div>

      {/* Center Needle/Target */}
      <div style={styles.needleContainer}>
        <motion.div
          style={{
            ...styles.needleOuter,
            x: needleX,
            y: needleY,
          }}
        >
          {/* Rotating outer ring */}
          <motion.div
            animate={{ 
              rotate: 360,
            }}
            transition={{ 
              duration: 20,
              repeat: Infinity,
              ease: "linear",
            }}
            style={styles.outerRing}
          >
            {[0, 90, 180, 270].map((angle) => (
              <div
                key={angle}
                style={{
                  ...styles.ringTick,
                  transform: `rotate(${angle}deg) translateY(-55px)`,
                }}
              />
            ))}
          </motion.div>

          {/* Counter-rotating needle */}
          <motion.div
            animate={{ 
              rotate: -360,
            }}
            transition={{ 
              duration: 15,
              repeat: Infinity,
              ease: "linear",
            }}
            style={styles.needleInner}
          >
            <div style={styles.needlePointer} />
          </motion.div>
          
          {/* Pulsing center dot */}
          <motion.div
            animate={{ 
              scale: [1, 1.3, 1],
              boxShadow: [
                '0 0 20px rgba(16, 185, 129, 0.8), inset 0 0 10px rgba(255, 255, 255, 0.5)',
                '0 0 30px rgba(16, 185, 129, 1), inset 0 0 15px rgba(255, 255, 255, 0.7)',
                '0 0 20px rgba(16, 185, 129, 0.8), inset 0 0 10px rgba(255, 255, 255, 0.5)',
              ],
            }}
            transition={{ 
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            style={styles.centerDot}
          />
        </motion.div>
      </div>

      {/* Title */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.8 }}
        style={styles.titleContainer}
      >
        <h2 style={styles.title}>Ask Needle</h2>
        <p style={styles.subtitle}>
          Precision insights from your customer data
        </p>
      </motion.div>

      {/* Prompt Cards */}
      {(
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5, duration: 0.5 }}
          style={styles.promptsGrid}
        >
          {prompts.map((item, index) => (
            <motion.button
              key={item.prompt}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ 
                delay: 1.8 + index * 0.1,
                duration: 0.5,
                type: "spring",
                stiffness: 100,
              }}
              whileHover={{ 
                scale: 1.03,
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderColor: 'rgba(16, 185, 129, 0.5)',
              }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onPromptSelect(item.prompt)}
              style={styles.promptCard}
            >
              <div style={styles.promptIcon}>
                {(() => {
                  const IconComponent = iconComponents[item.icon as keyof typeof iconComponents]
                  return <IconComponent className="w-7 h-7 text-emerald-400" />
                })()}
              </div>
              <div style={styles.promptTitle}>{item.title}</div>
              <div style={styles.promptText}>{item.prompt}</div>
            </motion.button>
          ))}
        </motion.div>
      )}
    </div>
  )
}

const styles = {
  container: {
    position: 'relative' as const,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '500px',
    padding: '24px 16px',
    overflow: 'hidden',
    width: '100%',
  },
  circlesContainer: {
    position: 'absolute' as const,
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    pointerEvents: 'none' as const,
  },
  circle: {
    position: 'absolute' as const,
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    border: '1.5px solid rgb(16, 185, 129)',
    borderRadius: '50%',
  },
  scanContainer: {
    position: 'absolute' as const,
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: 'min(400px, 80vw)',
    height: 'min(400px, 80vw)',
    pointerEvents: 'none' as const,
  },
  scanLine: {
    position: 'absolute' as const,
    top: '50%',
    left: '50%',
    width: '2px',
    height: '200px',
    background: 'linear-gradient(to bottom, transparent, rgb(16, 185, 129), transparent)',
    transformOrigin: 'top center',
    filter: 'blur(1px)',
  },
  needleContainer: {
    position: 'relative' as const,
    zIndex: 10,
    marginBottom: 'clamp(40px, 10vw, 80px)',
  },
  needleOuter: {
    position: 'relative' as const,
    width: 'min(120px, 25vw)',
    height: 'min(120px, 25vw)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  outerRing: {
    position: 'absolute' as const,
    width: 'min(110px, 23vw)',
    height: 'min(110px, 23vw)',
    borderRadius: '50%',
    border: '2px solid rgba(16, 185, 129, 0.3)',
  },
  ringTick: {
    position: 'absolute' as const,
    top: '50%',
    left: '50%',
    width: '3px',
    height: '12px',
    backgroundColor: 'rgb(16, 185, 129)',
    transformOrigin: 'center center',
  },
  needleInner: {
    position: 'absolute' as const,
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  needlePointer: {
    position: 'absolute' as const,
    top: '10px',
    left: '50%',
    transform: 'translateX(-50%)',
    width: '0',
    height: '0',
    borderLeft: '5px solid transparent',
    borderRight: '5px solid transparent',
    borderBottom: '45px solid rgb(16, 185, 129)',
    filter: 'drop-shadow(0 0 10px rgba(16, 185, 129, 0.8))',
  },
  centerDot: {
    position: 'absolute' as const,
    width: '18px',
    height: '18px',
    borderRadius: '50%',
    backgroundColor: 'rgb(16, 185, 129)',
    boxShadow: '0 0 20px rgba(16, 185, 129, 0.8), inset 0 0 10px rgba(255, 255, 255, 0.5)',
  },
  titleContainer: {
    textAlign: 'center' as const,
    marginBottom: 'clamp(24px, 6vw, 48px)',
    position: 'relative' as const,
    zIndex: 10,
    width: '100%',
  },
  title: {
    fontSize: 'clamp(24px, 5vw, 32px)',
    fontWeight: 'bold' as const,
    color: 'white',
    marginBottom: '12px',
    letterSpacing: '-0.5px',
  },
  subtitle: {
    fontSize: 'clamp(14px, 3vw, 16px)',
    color: 'rgba(255, 255, 255, 0.6)',
    maxWidth: '500px',
    margin: '0 auto',
    lineHeight: '1.6',
    padding: '0 16px',
  },
  promptsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))',
    gap: '16px',
    maxWidth: '1200px',
    width: '100%',
    padding: '0 16px',
    position: 'relative' as const,
    zIndex: 10,
  },
  promptCard: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'flex-start',
    padding: '20px',
    backgroundColor: 'rgba(31, 41, 55, 0.5)',
    border: '1px solid rgba(75, 85, 99, 0.5)',
    borderRadius: '12px',
    textAlign: 'left' as const,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    backdropFilter: 'blur(10px)',
  },
  promptIcon: {
    marginBottom: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-start',
  },
  promptTitle: {
    fontSize: '16px',
    fontWeight: '600' as const,
    color: 'white',
    marginBottom: '8px',
  },
  promptText: {
    fontSize: '14px',
    color: 'rgba(255, 255, 255, 0.6)',
    lineHeight: '1.5',
  },
}

