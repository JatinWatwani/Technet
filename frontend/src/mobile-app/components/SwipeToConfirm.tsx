import React, { useState, useRef } from 'react'
import { motion, useMotionValue, useTransform } from 'framer-motion'
import { Icon } from '../../components/Icon'

interface SwipeToConfirmProps {
  onConfirm: () => void
  label?: string
  confirmedLabel?: string
  disabled?: boolean
}

export function SwipeToConfirm({
  onConfirm,
  label = 'Slide to confirm handoff',
  confirmedLabel = 'Verified & Locked ✓',
  disabled = false,
}: SwipeToConfirmProps) {
  const [isConfirmed, setIsConfirmed] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const x = useMotionValue(0)
  const opacity = useTransform(x, [0, 180], [1, 0])

  const handleDragEnd = (_: any, info: any) => {
    if (disabled || isConfirmed) return
    const containerWidth = containerRef.current?.offsetWidth || 280
    const threshold = containerWidth - 75

    if (info.offset.x >= threshold) {
      setIsConfirmed(true)
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate([40, 60, 40])
      }
      onConfirm()
    } else {
      x.set(0)
    }
  }

  return (
    <div
      ref={containerRef}
      className={`swipe-track ${isConfirmed ? 'is-confirmed' : ''} ${disabled ? 'is-disabled' : ''}`}
    >
      <motion.span className="swipe-text" style={{ opacity }}>
        {isConfirmed ? confirmedLabel : label}
      </motion.span>

      <motion.div
        className="swipe-handle"
        drag={isConfirmed || disabled ? false : 'x'}
        dragConstraints={{ left: 0, right: 230 }}
        dragElastic={0.08}
        dragSnapToOrigin={!isConfirmed}
        onDragEnd={handleDragEnd}
        animate={isConfirmed ? { x: 230 } : undefined}
        style={{ x }}
        whileTap={{ scale: 0.95 }}
      >
        {isConfirmed ? (
          <span className="handle-check">✓</span>
        ) : (
          <Icon name="arrowRight" size={18} />
        )}
      </motion.div>
    </div>
  )
}
