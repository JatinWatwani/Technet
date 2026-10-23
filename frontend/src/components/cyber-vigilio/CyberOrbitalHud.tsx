import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'

export interface HudNode {
  id: string
  label: string
  sublabel?: string
  angleDeg: number
  radius: number
  hasWarning?: boolean
  severityChip?: 'C' | 'M' | 'H'
  logoType?: 'apache' | 'okta' | 'vultr' | 'aws' | 'alibaba' | 'endpoints' | 'sources'
  detail: string
  metrics: string
  domainMapping: string
}

interface CyberOrbitalHudProps {
  onNodeSelect?: (node: HudNode) => void
  onTriggerReroute?: () => void
  isRerouting?: boolean
  rerouteResolved?: boolean
}

export function CyberOrbitalHud({
  onNodeSelect,
  onTriggerReroute,
  isRerouting = false,
  rerouteResolved = false,
}: CyberOrbitalHudProps) {
  const [activeNode, setActiveNode] = useState<HudNode | null>(null)
  const [rateMode, setRateMode] = useState<'manual' | 'auto'>('manual')
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null)
  const [solverToast, setSolverToast] = useState<string>('')

  // Master node registry with real-time humanitarian logistics telemetry
  const NODES: HudNode[] = [
    {
      id: 'endpoints',
      label: '4.7k',
      sublabel: 'Endpoints',
      angleDeg: 90,
      radius: 255,
      hasWarning: true,
      logoType: 'endpoints',
      detail: '4.7k Perishable Units Active in Cold-Chain Logistics',
      metrics: '75m safe bio-window · 0 spoiled · 100% custody track',
      domainMapping: 'Master Aid Inventory Grid · Autonomous Fleet',
    },
    {
      id: 'sources',
      label: '+68',
      sublabel: 'Sources',
      angleDeg: 126,
      radius: 255,
      hasWarning: false,
      logoType: 'sources',
      detail: '+68 Verified Commercial Donor Surplus Kitchens',
      metrics: 'Banquet Hall A (180 meals), Mess Hall, Hospital Kitchen',
      domainMapping: 'Live Ingestion Pool · High-Reliability Donors',
    },
    {
      id: 'okta',
      label: 'okta',
      angleDeg: 150,
      radius: 255,
      hasWarning: false,
      logoType: 'okta',
      detail: 'City Pharmacy Cold-Chain Cryptographic Key',
      metrics: '24 Short-Life Insulin Kits · Verified Escort Couriers',
      domainMapping: 'Medical Cold-Chain Sentinel Node',
    },
    {
      id: 'apache',
      label: 'APACHE',
      angleDeg: 172,
      radius: 285,
      hasWarning: true,
      severityChip: 'M',
      logoType: 'apache',
      detail: 'Hostel Mess Raw Ration Dispatch (96 Portions)',
      metrics: 'Requires Clean Water prerequisite at Shelter C before dispatch',
      domainMapping: 'Prerequisite Rule Guard · Dependency Engine',
    },
    {
      id: 'vultr',
      label: 'VULTR',
      angleDeg: 52,
      radius: 255,
      hasWarning: false,
      severityChip: 'M',
      logoType: 'vultr',
      detail: 'Banquet Hall A Hot Meal Surplus Dispatch',
      metrics: '180 Portions · 48m bio-safe timer · 3 Couriers active',
      domainMapping: 'Primary Perishable Origin Hub',
    },
    {
      id: 'aws',
      label: 'aws',
      angleDeg: 28,
      radius: 255,
      hasWarning: !rerouteResolved,
      logoType: 'aws',
      detail: rerouteResolved
        ? 'Shelter A Diverted · Capacity safely capped at 50/50'
        : 'Shelter A Walk-In Overflow! Capacity 50/50 Full · Diverting Courier #07',
      metrics: rerouteResolved
        ? 'Courier #07 rerouted to Relief Camp B (+40 Meals delivered)'
        : 'Courier #07 (40 Meals) in physical custody · 19m buffer',
      domainMapping: 'Shelter A Receiving Node (Walk-In Overflow State)',
    },
    {
      id: 'alibaba',
      label: 'Alibaba Cloud',
      angleDeg: 4,
      radius: 310,
      hasWarning: false,
      severityChip: 'C',
      logoType: 'alibaba',
      detail: rerouteResolved
        ? 'Relief Camp B: +40 Meals Received (Capacity 58/138)'
        : 'Relief Camp B: 120 Meals Needed (Current capacity 18/138)',
      metrics: rerouteResolved
        ? '58/138 capacity · 0 Meals Wasted · Delivery Confirmed'
        : '18/138 capacity · Designated Fallback Destination',
      domainMapping: 'Relief Camp B Fallback Receiving Node',
    },
  ]

  useEffect(() => {
    if (isRerouting) {
      setSolverToast('Constraint Solver: Rerouting Courier #07 (Shelter A ──► Relief Camp B)...')
      const t = setTimeout(() => {
        setRateMode('auto')
        setSolverToast('✓ Reroute Locked: 40 Meals committed to Relief Camp B inside 19m safe buffer!')
      }, 1500)
      return () => clearTimeout(t)
    } else if (rerouteResolved) {
      setRateMode('auto')
      setSolverToast('✓ Autonomous Self-Healing Active · 0 Perishables Lost')
    } else {
      setSolverToast('')
    }
  }, [isRerouting, rerouteResolved])

  // Center baseline geometry
  const cx = 380
  const cy = 412

  // Concentric ring radii
  const rRing1 = 190 // Inner
  const rRing2 = 255 // Middle (Primary node orbit)
  const rRing3 = 320 // Outer

  // Helper for polar coordinates
  const polar = (angleDeg: number, radius: number) => {
    const rad = (angleDeg * Math.PI) / 180
    return {
      x: cx + radius * Math.cos(rad),
      y: cy - radius * Math.sin(rad),
    }
  }

  // 1. Generate dense outer radial tick halo (160 ticks from 185° down to -5°)
  const outerTicks = []
  const totalTicks = 160
  for (let i = 0; i <= totalTicks; i++) {
    const angle = 185 - (i / totalTicks) * 190
    const rad = (angle * Math.PI) / 180
    const isMajor = i % 5 === 0
    const r1 = 340
    const r2 = isMajor ? 368 : 358
    outerTicks.push({
      x1: cx + r1 * Math.cos(rad),
      y1: cy - r1 * Math.sin(rad),
      x2: cx + r2 * Math.cos(rad),
      y2: cy - r2 * Math.sin(rad),
      isMajor,
      key: i,
    })
  }

  // 2. Generate fine dome teeth micro-ticks (72 ticks around the dome perimeter)
  const domeTicks = []
  const totalDomeTicks = 72
  for (let i = 0; i <= totalDomeTicks; i++) {
    const angle = 180 - (i / totalDomeTicks) * 180
    const rad = (angle * Math.PI) / 180
    const r1 = 136
    const r2 = 145
    domeTicks.push({
      x1: cx + r1 * Math.cos(rad),
      y1: cy - r1 * Math.sin(rad),
      x2: cx + r2 * Math.cos(rad),
      y2: cy - r2 * Math.sin(rad),
      key: i,
    })
  }

  // Key coordinate anchors for nodes and reroute path
  const posApex = polar(90, rRing2)     // 4.7k Endpoints
  const posSources = polar(126, rRing2) // +68 Sources
  const posOkta = polar(150, rRing2)    // okta
  const posVultr = polar(52, rRing2)    // VULTR
  const posAws = polar(28, rRing2)      // aws (Shelter A)
  const posAlibaba = polar(4, 310)      // Alibaba Cloud (Relief Camp B)

  return (
    <div className="cyber-hud-container exact-dial-layout">
      <svg
        className="cyber-radar-svg"
        viewBox="0 0 760 420"
        preserveAspectRatio="xMidYMax meet"
      >
        <defs>
          {/* Neon Mint Green Arc Gradient */}
          <linearGradient id="neon-green-arc" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#18B880" />
            <stop offset="60%" stopColor="#00FFAC" />
            <stop offset="100%" stopColor="#25FFA9" />
          </linearGradient>

          {/* Radial Dome Gradient */}
          <radialGradient id="center-dome-grad" cx="50%" cy="100%" r="95%">
            <stop offset="0%" stopColor="#2a2d2c" />
            <stop offset="55%" stopColor="#1e201f" />
            <stop offset="100%" stopColor="#131413" />
          </radialGradient>

          {/* Subtle Atmospheric Emerald Ambient Glow */}
          <radialGradient id="ambient-hud-glow" cx="35%" cy="30%" r="65%">
            <stop offset="0%" stopColor="rgba(24, 184, 128, 0.16)" />
            <stop offset="50%" stopColor="rgba(24, 184, 128, 0.04)" />
            <stop offset="100%" stopColor="rgba(0, 0, 0, 0)" />
          </radialGradient>

          {/* Neon Glow Filter */}
          <filter id="neon-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="4" result="blur1" />
            <feGaussianBlur stdDeviation="9" result="blur2" />
            <feMerge>
              <feMergeNode in="blur2" />
              <feMergeNode in="blur1" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Subtle Warning Triangle Glow */}
          <filter id="orange-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* -------------------------------------------------------------
            1. Background Ambient Lighting
            ------------------------------------------------------------- */}
        <ellipse cx="280" cy="180" rx="260" ry="200" fill="url(#ambient-hud-glow)" />

        {/* -------------------------------------------------------------
            2. Dense Outer Radial Tick Halo (Matches screenshot precision)
            ------------------------------------------------------------- */}
        <g className="outer-tick-halo">
          {outerTicks.map((t) => (
            <line
              key={t.key}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              stroke={t.isMajor ? 'rgba(255, 255, 255, 0.32)' : 'rgba(255, 255, 255, 0.11)'}
              strokeWidth={t.isMajor ? '1.2' : '0.8'}
            />
          ))}
        </g>

        {/* -------------------------------------------------------------
            3. Three Concentric Circular Orbit Tracks
            ------------------------------------------------------------- */}
        {/* Ring 1 (Inner) */}
        <path
          d={`M ${cx - rRing1} ${cy} A ${rRing1} ${rRing1} 0 0 1 ${cx + rRing1} ${cy}`}
          fill="none"
          stroke="rgba(255, 255, 255, 0.12)"
          strokeWidth="1.2"
        />
        {/* Ring 2 (Middle - Main Node Orbit) */}
        <path
          d={`M ${cx - rRing2} ${cy} A ${rRing2} ${rRing2} 0 0 1 ${cx + rRing2} ${cy}`}
          fill="none"
          stroke="rgba(255, 255, 255, 0.16)"
          strokeWidth="1.3"
        />
        {/* Ring 3 (Outer) */}
        <path
          d={`M ${cx - rRing3} ${cy} A ${rRing3} ${rRing3} 0 0 1 ${cx + rRing3} ${cy}`}
          fill="none"
          stroke="rgba(255, 255, 255, 0.11)"
          strokeWidth="1.1"
        />

        {/* -------------------------------------------------------------
            4. Animated Reroute Vector Flight Arc (AWS ──► Alibaba)
            ------------------------------------------------------------- */}
        {(isRerouting || rerouteResolved) && (
          <g className="reroute-flight-vector">
            <motion.path
              d={`M ${posAws.x} ${posAws.y} Q 660 330 ${posAlibaba.x} ${posAlibaba.y}`}
              fill="none"
              stroke="#F9771D"
              strokeWidth="3.5"
              strokeDasharray="6 4"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1.1, ease: 'easeInOut' }}
            />
            {/* Courier 07 moving marker */}
            <motion.circle
              r="5.5"
              fill="#F9771D"
              stroke="#ffffff"
              strokeWidth="2"
              animate={{
                cx: [posAws.x, 650, posAlibaba.x],
                cy: [posAws.y, 330, posAlibaba.y],
              }}
              transition={{
                duration: 2.2,
                repeat: rerouteResolved ? 0 : Infinity,
                ease: 'easeInOut',
              }}
            />
          </g>
        )}

        {/* -------------------------------------------------------------
            5. Center Semicircular Dome & Gauge
            ------------------------------------------------------------- */}
        {/* Dome teeth micro-ticks */}
        <g className="dome-micro-ticks">
          {domeTicks.map((t) => (
            <line
              key={t.key}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              stroke="rgba(255, 255, 255, 0.18)"
              strokeWidth="0.85"
            />
          ))}
        </g>

        {/* Solid Center Dome Hemisphere */}
        <path
          d={`M ${cx - 135} ${cy} A 135 135 0 0 1 ${cx + 135} ${cy} Z`}
          fill="url(#center-dome-grad)"
          stroke="rgba(255, 255, 255, 0.18)"
          strokeWidth="1.2"
          style={{ cursor: 'pointer' }}
          onClick={() => setRateMode(rateMode === 'manual' ? 'auto' : 'manual')}
        />

        {/* Base Track Line for Emerald Arc */}
        <path
          d={`M ${cx} ${cy - 146} A 146 146 0 0 1 ${cx + 146} ${cy}`}
          fill="none"
          stroke="rgba(255, 255, 255, 0.08)"
          strokeWidth="6.5"
          strokeLinecap="round"
        />

        {/* Glowing Mint Emerald Progress Arc */}
        <motion.path
          d={
            rateMode === 'manual'
              ? `M ${cx} ${cy - 146} A 146 146 0 0 1 ${cx + 146 * Math.cos((54 * Math.PI) / 180)} ${cy - 146 * Math.sin((54 * Math.PI) / 180)}`
              : `M ${cx} ${cy - 146} A 146 146 0 0 1 ${cx + 146 * Math.cos((2 * Math.PI) / 180)} ${cy - 146 * Math.sin((2 * Math.PI) / 180)}`
          }
          fill="none"
          stroke="url(#neon-green-arc)"
          strokeWidth="6.5"
          strokeLinecap="round"
          filter="url(#neon-glow)"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.9, ease: 'easeOut' }}
        />

        {/* Center Dome Text (Clickable toggle between Manual 10% & Autonomous 98%) */}
        <g
          className="center-dome-text-group"
          style={{ cursor: 'pointer' }}
          onClick={() => setRateMode(rateMode === 'manual' ? 'auto' : 'manual')}
        >
          <text
            x={cx}
            y={cy - 48}
            textAnchor="middle"
            fill="#ffffff"
            style={{
              fontFamily: "'Outfit', -apple-system, sans-serif",
              fontSize: '44px',
              fontWeight: 400,
              letterSpacing: '-0.04em',
            }}
          >
            {rateMode === 'manual' ? '10%' : '98%'}
          </text>

          <text
            x={cx}
            y={cy - 20}
            textAnchor="middle"
            fill="#8e9491"
            style={{
              fontFamily: "'Outfit', -apple-system, sans-serif",
              fontSize: '12.5px',
              fontWeight: 500,
              letterSpacing: '0.02em',
            }}
          >
            {rateMode === 'manual' ? 'Manually Resolved' : 'Autonomous Resolved'}
          </text>
        </g>

        {/* -------------------------------------------------------------
            6. Static Severity Chips on Rings
            ------------------------------------------------------------- */}
        {/* Chip [C] near 118° on Ring 1 */}
        {(() => {
          const p = polar(118, rRing1)
          return (
            <g transform={`translate(${p.x - 8}, ${p.y - 8})`}>
              <rect width="16" height="16" rx="4" fill="#222423" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
              <text x="8" y="12" textAnchor="middle" fill="#8c8c8c" style={{ fontFamily: "'Outfit', sans-serif", fontSize: '9px', fontWeight: 700 }}>C</text>
            </g>
          )
        })()}

        {/* Chip [M] near 68° on Ring 2 */}
        {(() => {
          const p = polar(68, rRing2)
          return (
            <g transform={`translate(${p.x - 8}, ${p.y - 8})`}>
              <rect width="16" height="16" rx="4" fill="#222423" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
              <text x="8" y="12" textAnchor="middle" fill="#8c8c8c" style={{ fontFamily: "'Outfit', sans-serif", fontSize: '9px', fontWeight: 700 }}>M</text>
            </g>
          )
        })()}

        {/* Chip [M] near 18° on Ring 1 */}
        {(() => {
          const p = polar(18, rRing1)
          return (
            <g transform={`translate(${p.x - 8}, ${p.y - 8})`}>
              <rect width="16" height="16" rx="4" fill="#222423" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
              <text x="8" y="12" textAnchor="middle" fill="#8c8c8c" style={{ fontFamily: "'Outfit', sans-serif", fontSize: '9px', fontWeight: 700 }}>M</text>
            </g>
          )
        })()}

        {/* Chip [C] near 10° on Ring 1 */}
        {(() => {
          const p = polar(10, rRing1)
          return (
            <g transform={`translate(${p.x - 8}, ${p.y - 8})`}>
              <rect width="16" height="16" rx="4" fill="#222423" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
              <text x="8" y="12" textAnchor="middle" fill="#8c8c8c" style={{ fontFamily: "'Outfit', sans-serif", fontSize: '9px', fontWeight: 700 }}>C</text>
            </g>
          )
        })()}

        {/* Chip [M] near 160° on Ring 1 */}
        {(() => {
          const p = polar(160, rRing1)
          return (
            <g transform={`translate(${p.x - 8}, ${p.y - 8})`}>
              <rect width="16" height="16" rx="4" fill="#222423" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
              <text x="8" y="12" textAnchor="middle" fill="#8c8c8c" style={{ fontFamily: "'Outfit', sans-serif", fontSize: '9px', fontWeight: 700 }}>M</text>
            </g>
          )
        })()}

        {/* -------------------------------------------------------------
            7. Interactive Precision Telemetry Nodes (SVG Vector Art)
            ------------------------------------------------------------- */}

        {/* =============================================================
            NODE 1: 4.7k Endpoints (Apex - 12 o'clock, on Ring 2)
            ============================================================= */}
        <g
          className="hud-node-group"
          style={{ cursor: 'pointer' }}
          onClick={() => {
            setActiveNode(NODES[0])
            onNodeSelect?.(NODES[0])
          }}
          onMouseEnter={() => setHoveredNodeId('endpoints')}
          onMouseLeave={() => setHoveredNodeId(null)}
        >
          {/* Label 4.7k */}
          <text
            x={posApex.x}
            y={posApex.y - 34}
            textAnchor="middle"
            fill="#ffffff"
            style={{
              fontFamily: "'Outfit', sans-serif",
              fontSize: '15px',
              fontWeight: 600,
              letterSpacing: '-0.02em',
            }}
          >
            4.7k
          </text>
          {/* Sublabel Endpoints */}
          <text
            x={posApex.x}
            y={posApex.y - 19}
            textAnchor="middle"
            fill="#8c908e"
            style={{
              fontFamily: "'Outfit', sans-serif",
              fontSize: '11px',
              fontWeight: 400,
            }}
          >
            Endpoints
          </text>

          {/* Desktop Monitor Screen Icon sitting directly on the ring */}
          <g transform={`translate(${posApex.x - 7}, ${posApex.y - 6})`}>
            <rect x="0" y="0" width="14" height="9" rx="1.5" stroke="#ffffff" strokeWidth="1.2" fill="#181818" />
            <line x1="7" y1="9" x2="7" y2="12" stroke="#ffffff" strokeWidth="1.2" />
            <line x1="4" y1="12" x2="10" y2="12" stroke="#ffffff" strokeWidth="1.2" />
          </g>

          {/* Orange Warning Triangle ⚠ directly below screen icon */}
          <g transform={`translate(${posApex.x - 8}, ${posApex.y + 14})`} filter="url(#orange-glow)">
            <path d="M8 1L1 13H15L8 1Z" fill="#F9771D" />
            <path d="M8 5V8.5M8 10.8H8.01" stroke="#ffffff" strokeWidth="1.4" strokeLinecap="round" />
          </g>
        </g>

        {/* =============================================================
            NODE 2: +68 Sources (Top-Left, on Ring 2)
            ============================================================= */}
        <g
          className="hud-node-group"
          style={{ cursor: 'pointer' }}
          onClick={() => {
            setActiveNode(NODES[1])
            onNodeSelect?.(NODES[1])
          }}
          onMouseEnter={() => setHoveredNodeId('sources')}
          onMouseLeave={() => setHoveredNodeId(null)}
        >
          <text
            x={posSources.x}
            y={posSources.y - 28}
            textAnchor="middle"
            fill="#ffffff"
            style={{
              fontFamily: "'Outfit', sans-serif",
              fontSize: '15px',
              fontWeight: 600,
              letterSpacing: '-0.02em',
            }}
          >
            +68
          </text>
          <text
            x={posSources.x}
            y={posSources.y - 13}
            textAnchor="middle"
            fill="#8c908e"
            style={{
              fontFamily: "'Outfit', sans-serif",
              fontSize: '11px',
              fontWeight: 400,
            }}
          >
            Sources
          </text>
          {/* Node Dot on the Ring line */}
          <circle cx={posSources.x} cy={posSources.y} r="3.5" fill="#ffffff" />
        </g>

        {/* =============================================================
            NODE 3: okta (Mid-Left, on Ring 2)
            ============================================================= */}
        <g
          className="hud-node-group"
          style={{ cursor: 'pointer' }}
          onClick={() => {
            setActiveNode(NODES[2])
            onNodeSelect?.(NODES[2])
          }}
          onMouseEnter={() => setHoveredNodeId('okta')}
          onMouseLeave={() => setHoveredNodeId(null)}
        >
          <text
            x={posOkta.x - 12}
            y={posOkta.y + 6}
            textAnchor="middle"
            fill="#ffffff"
            style={{
              fontFamily: "'Outfit', sans-serif",
              fontSize: '17px',
              fontWeight: 700,
              letterSpacing: '-0.04em',
            }}
          >
            okta
          </text>
          {/* Tiny node dot on the track */}
          <circle cx={posOkta.x + 16} cy={posOkta.y} r="3" fill="#ffffff" />
        </g>

        {/* =============================================================
            NODE 4: APACHE (Far Bottom-Left)
            ============================================================= */}
        <g
          className="hud-node-group"
          style={{ cursor: 'pointer' }}
          onClick={() => {
            setActiveNode(NODES[3])
            onNodeSelect?.(NODES[3])
          }}
          onMouseEnter={() => setHoveredNodeId('apache')}
          onMouseLeave={() => setHoveredNodeId(null)}
        >
          {/* Warning Triangle near 166° */}
          {(() => {
            const p = polar(166, 215)
            return (
              <g transform={`translate(${p.x - 7}, ${p.y - 6})`} filter="url(#orange-glow)">
                <path d="M7 1L1 11H13L7 1Z" fill="#F9771D" />
                <path d="M7 4.5V7M7 9H7.01" stroke="#ffffff" strokeWidth="1.2" strokeLinecap="round" />
              </g>
            )
          })()}

          {/* Apache Feather + Wordmark */}
          <g transform="translate(85, 380)">
            {/* Stylized Feather */}
            <path
              d="M12 0C10 4 6 12 0 18C4 16 9 14 11 11L13 14C14 11 15 6 12 0Z"
              fill="#ffffff"
              opacity="0.9"
            />
            <line x1="0" y1="18" x2="14" y2="2" stroke="#ffffff" strokeWidth="0.8" opacity="0.6" />
            <text
              x="18"
              y="11"
              fill="#ffffff"
              style={{
                fontFamily: "'Outfit', sans-serif",
                fontSize: '12.5px',
                fontWeight: 700,
                letterSpacing: '0.08em',
              }}
            >
              APACHE
            </text>
            <text
              x="18"
              y="18"
              fill="#8c8c8c"
              style={{
                fontFamily: "'Outfit', sans-serif",
                fontSize: '6.5px',
                fontWeight: 600,
                letterSpacing: '0.04em',
              }}
            >
              SOFTWARE FOUNDATION
            </text>
          </g>
        </g>

        {/* =============================================================
            NODE 5: VULTR (Top-Right, on Ring 2)
            ============================================================= */}
        <g
          className="hud-node-group"
          style={{ cursor: 'pointer' }}
          onClick={() => {
            setActiveNode(NODES[4])
            onNodeSelect?.(NODES[4])
          }}
          onMouseEnter={() => setHoveredNodeId('vultr')}
          onMouseLeave={() => setHoveredNodeId(null)}
        >
          {/* Vultr Chevron Icon + Wordmark */}
          <g transform={`translate(${posVultr.x - 6}, ${posVultr.y - 7})`}>
            {/* Vultr Stylized 'V' Chevron */}
            <path d="M8 12L0 0H5L8 5L11 0H16L8 12Z" fill="#ffffff" />
            <text
              x="22"
              y="10"
              fill="#ffffff"
              style={{
                fontFamily: "'Outfit', sans-serif",
                fontSize: '13.5px',
                fontWeight: 700,
                letterSpacing: '0.04em',
              }}
            >
              VULTR
            </text>
          </g>
        </g>

        {/* =============================================================
            NODE 6: aws (Mid-Right, on Ring 2)
            ============================================================= */}
        <g
          className="hud-node-group"
          style={{ cursor: 'pointer' }}
          onClick={() => {
            setActiveNode(NODES[5])
            onNodeSelect?.(NODES[5])
          }}
          onMouseEnter={() => setHoveredNodeId('aws')}
          onMouseLeave={() => setHoveredNodeId(null)}
        >
          {/* Warning Triangle on line before AWS (if not resolved) */}
          {!rerouteResolved && (
            <g transform={`translate(${posAws.x - 22}, ${posAws.y - 7})`} filter="url(#orange-glow)">
              <path d="M7 1L1 11H13L7 1Z" fill="#F9771D" />
              <path d="M7 4.5V7M7 9H7.01" stroke="#ffffff" strokeWidth="1.2" strokeLinecap="round" />
            </g>
          )}

          {/* AWS Logo with Signature Orange Smile */}
          <g transform={`translate(${posAws.x + 6}, ${posAws.y - 12})`}>
            <text
              x="14"
              y="14"
              fill="#ffffff"
              style={{
                fontFamily: "'Outfit', sans-serif",
                fontSize: '17px',
                fontWeight: 700,
                letterSpacing: '-0.02em',
              }}
            >
              aws
            </text>
            {/* Orange Curved Arrow Smile */}
            <path
              d="M2 19C10 23 20 23 27 19"
              stroke="#F9771D"
              strokeWidth="1.8"
              strokeLinecap="round"
              fill="none"
            />
            <path d="M25 18L28 19L27 22" fill="#F9771D" />
          </g>
        </g>

        {/* =============================================================
            NODE 7: Alibaba Cloud (Far Bottom-Right)
            ============================================================= */}
        <g
          className="hud-node-group"
          style={{ cursor: 'pointer' }}
          onClick={() => {
            setActiveNode(NODES[6])
            onNodeSelect?.(NODES[6])
          }}
          onMouseEnter={() => setHoveredNodeId('alibaba')}
          onMouseLeave={() => setHoveredNodeId(null)}
        >
          <g transform={`translate(${posAlibaba.x - 30}, ${posAlibaba.y - 6})`}>
            {/* Alibaba Cloud [-] Bracket Mark */}
            <g transform="translate(0, 0)">
              <rect x="0" y="2" width="2.5" height="8" rx="1" fill="#ffffff" />
              <rect x="13.5" y="2" width="2.5" height="8" rx="1" fill="#ffffff" />
              <line x1="4.5" y1="6" x2="11.5" y2="6" stroke="#ffffff" strokeWidth="1.6" />
            </g>
            <text
              x="22"
              y="9.5"
              fill="#ffffff"
              style={{
                fontFamily: "'Outfit', sans-serif",
                fontSize: '12px',
                fontWeight: 500,
                letterSpacing: '0.01em',
              }}
            >
              Alibaba Cloud
            </text>
          </g>
        </g>
      </svg>

      {/* -------------------------------------------------------------
          Live Toast Banner over the Radar
          ------------------------------------------------------------- */}
      <AnimatePresence>
        {solverToast && (
          <motion.div
            className="hud-live-solver-pill"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <span className="solver-emerald-dot" />
            <span>{solverToast}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* -------------------------------------------------------------
          Interactive Detail Popover when clicking on any Node
          ------------------------------------------------------------- */}
      <AnimatePresence>
        {activeNode && (
          <motion.div
            className="hud-node-detail-card"
            initial={{ opacity: 0, scale: 0.94, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 8 }}
          >
            <div className="detail-card-top">
              <div>
                <strong>
                  {activeNode.label} {activeNode.sublabel && `· ${activeNode.sublabel}`}
                </strong>
                <span>{activeNode.domainMapping}</span>
              </div>
              <button
                className="popover-close"
                onClick={() => setActiveNode(null)}
                aria-label="Close"
              >
                <Icon name="x" size={13} />
              </button>
            </div>
            <p className="detail-text">{activeNode.detail}</p>
            <div className="detail-card-metric">
              <Icon name="activity" size={13} />
              <span>{activeNode.metrics}</span>
            </div>
            {activeNode.id === 'aws' && !rerouteResolved && onTriggerReroute && (
              <button
                className="hud-execute-reroute-btn"
                onClick={() => {
                  onTriggerReroute()
                  setActiveNode(null)
                }}
              >
                <Icon name="zap" size={13} />
                <span>Execute Reroute to Alibaba (Relief Camp B)</span>
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
