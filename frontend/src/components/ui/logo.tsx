import React from 'react'

interface LogoProps {
  className?: string
  variant?: 'default' | 'minimal'
}

export function Logo({ className = '', variant = 'default' }: LogoProps) {
  if (variant === 'minimal') {
    return (
      <svg
        viewBox="0 0 40 40"
        className={className}
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#10b981', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#059669', stopOpacity: 1 }} />
          </linearGradient>
        </defs>
        <path
          d="M20 5 L35 15 L35 30 L20 40 L5 30 L5 15 Z"
          fill="url(#logoGradient)"
          opacity="0.1"
        />
        <path
          d="M20 8 L32 16 L32 29 L20 37 L8 29 L8 16 Z"
          stroke="url(#logoGradient)"
          strokeWidth="1.5"
          fill="none"
        />
        <path
          d="M15 18 L20 15 L25 18 L25 27 L20 30 L15 27 Z"
          fill="url(#logoGradient)"
        />
        <circle cx="20" cy="22.5" r="2" fill="#030712" />
      </svg>
    )
  }

  return (
    <svg
      viewBox="0 0 200 50"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="logoGradientFull" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{ stopColor: '#10b981', stopOpacity: 1 }} />
          <stop offset="100%" style={{ stopColor: '#059669', stopOpacity: 1 }} />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      
      {/* Icon */}
      <g transform="translate(5, 5)">
        <path
          d="M20 5 L35 15 L35 30 L20 40 L5 30 L5 15 Z"
          fill="url(#logoGradientFull)"
          opacity="0.1"
        />
        <path
          d="M20 8 L32 16 L32 29 L20 37 L8 29 L8 16 Z"
          stroke="url(#logoGradientFull)"
          strokeWidth="1.5"
          fill="none"
          filter="url(#glow)"
        />
        <path
          d="M15 18 L20 15 L25 18 L25 27 L20 30 L15 27 Z"
          fill="url(#logoGradientFull)"
        />
        <circle cx="20" cy="22.5" r="2" fill="#030712" />
      </g>
      
      {/* Text */}
      <text
        x="55"
        y="32"
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="22"
        fontWeight="700"
        fill="#ffffff"
        letterSpacing="0.5"
      >
        Needle
      </text>
      <text
        x="139"
        y="32"
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="22"
        fontWeight="300"
        fill="#10b981"
      >
        AI
      </text>
    </svg>
  )
}

