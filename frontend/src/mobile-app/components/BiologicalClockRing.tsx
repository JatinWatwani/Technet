import React from 'react'

interface BiologicalClockRingProps {
  remainingSeconds: number
  totalSeconds: number
  size?: number
  strokeWidth?: number
  label?: string
}

export function BiologicalClockRing({
  remainingSeconds,
  totalSeconds,
  size = 72,
  strokeWidth = 6,
  label = 'Safe Bio Window',
}: BiologicalClockRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const progress = Math.max(0, Math.min(1, remainingSeconds / totalSeconds))
  const strokeDashoffset = circumference - progress * circumference

  const mins = Math.floor(remainingSeconds / 60)
  const secs = remainingSeconds % 60
  const timeFormatted = `${mins}:${secs.toString().padStart(2, '0')}`

  // Color transitions from emerald -> amber -> coral red
  let color = '#10B981'
  if (remainingSeconds < 15 * 60) color = '#F59E0B'
  if (remainingSeconds < 5 * 60) color = '#EF4444'

  return (
    <div className="bio-clock-root" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255, 255, 255, 0.12)"
          strokeWidth={strokeWidth}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="none"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dashoffset 1s linear, stroke 0.5s ease' }}
        />
      </svg>
      <div className="bio-clock-center">
        <span className="bio-clock-time" style={{ color }}>{timeFormatted}</span>
        <span className="bio-clock-unit">min</span>
      </div>
    </div>
  )
}
