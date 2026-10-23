import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'

interface LiveFleetMapViewProps {
  onTriggerReroute: () => void
  rerouteResolved: boolean
}

export function LiveFleetMapView({
  onTriggerReroute,
  rerouteResolved,
}: LiveFleetMapViewProps) {
  const [selectedCourier, setSelectedCourier] = useState<string | null>('courier-07')
  const [selectedShelter, setSelectedShelter] = useState<string | null>(null)
  const [mapFilter, setMapFilter] = useState<'all' | 'couriers' | 'shelters'>('all')

  // Shelter nodes across the city grid
  const SHELTERS = [
    {
      id: 'shelter-a',
      name: 'Shelter A (North Hub)',
      current: 50,
      capacity: 50,
      status: 'Critical · Capacity Capped at 50/50',
      x: 320,
      y: 90,
      isWarning: true,
      type: 'shelter',
      address: 'Sector 4, North Relief Corridor',
    },
    {
      id: 'shelter-b',
      name: 'Relief Camp B (Fallback Hub)',
      current: rerouteResolved ? 58 : 18,
      capacity: 138,
      status: rerouteResolved ? 'Committed: +40 Meals Received' : 'Available · Receiving Hub',
      x: 620,
      y: 280,
      isWarning: false,
      isRecommended: true,
      type: 'shelter',
      address: 'Sector 9, Eastern Highway Junction',
    },
    {
      id: 'shelter-c',
      name: 'Shelter C (Cooking Station)',
      current: 65,
      capacity: 100,
      status: 'Prerequisite Active: Clean Water',
      x: 140,
      y: 310,
      isWarning: false,
      type: 'shelter',
      address: 'Sector 2, West Canal Road',
    },
    {
      id: 'riverside',
      name: 'Riverside Camp',
      current: 20,
      capacity: 80,
      status: 'Reception Nominal',
      x: 430,
      y: 390,
      isWarning: false,
      type: 'shelter',
      address: 'Sector 7, South Embankment',
    },
  ]

  // Food origin hubs
  const DONORS = [
    { id: 'donor-banquet', name: 'Banquet Hall A', x: 220, y: 190, cargo: '180 Cooked Meals' },
    { id: 'donor-pharmacy', name: 'City Pharmacy Central', x: 490, y: 150, cargo: '24 Insulin Kits' },
    { id: 'donor-hostel', name: 'Hostel Mess Kitchen', x: 100, y: 180, cargo: '96 Raw Rations' },
  ]

  // Volunteer couriers (Swiggy / Zomato order tracking style)
  const COURIERS = [
    {
      id: 'courier-07',
      name: 'Courier #07 (Rider Vikram S.)',
      vehicle: 'Bajaj Pulsar 150 • Bike',
      cargo: '40 Portions Hot Meals',
      bioBuffer: '19m safe bio-window',
      origin: 'Banquet Hall A',
      destination: rerouteResolved ? 'Relief Camp B (Rerouted)' : 'Shelter A (Over Capacity)',
      status: rerouteResolved ? 'En Route to Relief Camp B' : 'Reroute Recommended',
      speed: '28 km/h',
      x: rerouteResolved ? 480 : 280,
      y: rerouteResolved ? 230 : 130,
      isHero: true,
      battery: '82%',
    },
    {
      id: 'courier-14',
      name: 'Courier #14 (Rider Ananya P.)',
      vehicle: 'Hero E-Bike • Cargo',
      cargo: '60 Bread & Fruit Kits',
      bioBuffer: '65m buffer',
      origin: 'Banquet Hall A',
      destination: 'Riverside Camp',
      status: 'Normal Delivery Transit',
      speed: '22 km/h',
      x: 350,
      y: 320,
      isHero: false,
      battery: '94%',
    },
    {
      id: 'courier-02',
      name: 'Courier #02 (Driver R. Sharma)',
      vehicle: 'Insulated Refrigerated Van',
      cargo: '24 Insulin Kits (Cold-Chain 3.8°C)',
      bioBuffer: '42m bio-safe window',
      origin: 'City Pharmacy',
      destination: 'Relief Camp B',
      status: 'Cold-Chain Secure',
      speed: '34 km/h',
      x: 550,
      y: 210,
      isHero: false,
      battery: '100%',
    },
  ]

  const activeCourierData = COURIERS.find((c) => c.id === selectedCourier) || COURIERS[0]
  const activeShelterData = SHELTERS.find((s) => s.id === selectedShelter)

  return (
    <div className="fleet-map-container">
      {/* Top Map Control Bar */}
      <div className="map-control-header">
        <div className="map-title-block">
          <div className="map-pulse-wrap">
            <span className="live-gps-pulse" />
            <Icon name="map" size={15} />
          </div>
          <div>
            <h3>Live Volunteer Fleet & Shelter Map</h3>
            <p>Real-time Swiggy/Zomato style courier tracking, capacity monitoring, and in-transit rerouting</p>
          </div>
        </div>

        <div className="map-filter-pills">
          <button
            className={`map-filter-btn ${mapFilter === 'all' ? 'is-active' : ''}`}
            onClick={() => setMapFilter('all')}
          >
            All Network Nodes
          </button>
          <button
            className={`map-filter-btn ${mapFilter === 'couriers' ? 'is-active' : ''}`}
            onClick={() => setMapFilter('couriers')}
          >
            Volunteer Couriers (3)
          </button>
          <button
            className={`map-filter-btn ${mapFilter === 'shelters' ? 'is-active' : ''}`}
            onClick={() => setMapFilter('shelters')}
          >
            Shelter Capacities (4)
          </button>
        </div>
      </div>

      {/* Main Map Stage */}
      <div className="map-stage-wrapper">
        <svg
          viewBox="0 0 800 480"
          className="city-grid-svg"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <linearGradient id="road-grad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="rgba(255, 255, 255, 0.08)" />
              <stop offset="100%" stopColor="rgba(255, 255, 255, 0.04)" />
            </linearGradient>

            <linearGradient id="river-grad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="rgba(57, 153, 206, 0.08)" />
              <stop offset="50%" stopColor="rgba(57, 153, 206, 0.16)" />
              <stop offset="100%" stopColor="rgba(57, 153, 206, 0.08)" />
            </linearGradient>

            <filter id="courier-glow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* 1. City River */}
          <path
            d="M 0 360 Q 200 340 400 370 T 800 330 L 800 420 L 0 450 Z"
            fill="url(#river-grad)"
          />
          <text x="30" y="420" fill="rgba(57, 153, 206, 0.4)" fontSize="11" fontFamily="'Outfit', sans-serif">
            South Relief River Canal
          </text>

          {/* 2. City Grid Road Network */}
          <g className="city-roads" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="6" strokeLinecap="round">
            {/* Main Arterials */}
            <line x1="60" y1="90" x2="740" y2="90" />
            <line x1="60" y1="190" x2="740" y2="190" />
            <line x1="60" y1="280" x2="740" y2="280" />
            <line x1="60" y1="390" x2="740" y2="390" />
            {/* North-South Corridors */}
            <line x1="140" y1="60" x2="140" y2="440" />
            <line x1="320" y1="60" x2="320" y2="440" />
            <line x1="490" y1="60" x2="490" y2="440" />
            <line x1="620" y1="60" x2="620" y2="440" />
            {/* Diagonal Bypass */}
            <line x1="220" y1="190" x2="620" y2="280" strokeDasharray="3 3" strokeWidth="2.5" />
          </g>

          {/* Road Labels */}
          <text x="145" y="80" fill="rgba(255, 255, 255, 0.25)" fontSize="10" fontFamily="'DM Mono', monospace">CORRIDOR 01</text>
          <text x="325" y="80" fill="rgba(255, 255, 255, 0.25)" fontSize="10" fontFamily="'DM Mono', monospace">CENTRAL ARTERIAL</text>
          <text x="625" y="80" fill="rgba(255, 255, 255, 0.25)" fontSize="10" fontFamily="'DM Mono', monospace">EAST EXPRESSWAY</text>

          {/* 3. Original Route (Banquet Hall A ──► Shelter A) */}
          <path
            d="M 220 190 L 320 190 L 320 90"
            fill="none"
            stroke={rerouteResolved ? 'rgba(255, 255, 255, 0.12)' : '#F9771D'}
            strokeWidth="3"
            strokeDasharray={rerouteResolved ? '4 4' : '6 3'}
          />

          {/* 4. Active Swiggy/Zomato Reroute Path (Courier 07 ──► Relief Camp B) */}
          {rerouteResolved && (
            <motion.path
              d="M 280 130 Q 420 190 620 280"
              fill="none"
              stroke="#18B880"
              strokeWidth="4"
              strokeDasharray="6 4"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1.2, ease: 'easeInOut' }}
            />
          )}

          {/* 5. Food Donor Hubs */}
          {DONORS.map((d) => (
            <g key={d.id} className="donor-hub-node">
              <circle cx={d.x} cy={d.y} r="10" fill="#252726" stroke="#ffffff" strokeWidth="1.5" />
              <rect x={d.x - 4} y={d.y - 4} width="8" height="8" rx="1.5" fill="#F9771D" />
              <text x={d.x + 14} y={d.y + 4} fill="#ffffff" fontSize="11" fontWeight="700" fontFamily="'Outfit', sans-serif">
                {d.name}
              </text>
            </g>
          ))}

          {/* 6. Shelter Destination Nodes */}
          {(mapFilter === 'all' || mapFilter === 'shelters') &&
            SHELTERS.map((s) => {
              const pct = Math.round((s.current / s.capacity) * 100)
              const isSelected = selectedShelter === s.id
              return (
                <g
                  key={s.id}
                  className="shelter-map-node"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelectedShelter(s.id)}
                >
                  {/* Warning pulse if full */}
                  {s.isWarning && (
                    <circle cx={s.x} cy={s.y} r="22" fill="none" stroke="#CE6969" strokeWidth="1.5" opacity="0.6">
                      <animate attributeName="r" values="16;28;16" dur="2s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.8;0.1;0.8" dur="2s" repeatCount="indefinite" />
                    </circle>
                  )}

                  {/* Recommended green halo for fallback */}
                  {s.isRecommended && (
                    <circle cx={s.x} cy={s.y} r="22" fill="none" stroke="#18B880" strokeWidth="1.5" opacity="0.5">
                      <animate attributeName="r" values="18;26;18" dur="2.4s" repeatCount="indefinite" />
                    </circle>
                  )}

                  <circle
                    cx={s.x}
                    cy={s.y}
                    r="15"
                    fill={s.isWarning ? '#341a1a' : s.isRecommended ? '#182f24' : '#222423'}
                    stroke={s.isWarning ? '#CE6969' : s.isRecommended ? '#18B880' : '#888888'}
                    strokeWidth={isSelected ? '3' : '1.8'}
                  />

                  {/* Shelter Building Icon */}
                  <path
                    d={`M ${s.x - 6} ${s.y + 5} V ${s.y - 2} L ${s.x} ${s.y - 7} L ${s.x + 6} ${s.y - 2} V ${s.y + 5} Z`}
                    fill={s.isWarning ? '#CE6969' : s.isRecommended ? '#18B880' : '#ffffff'}
                  />

                  {/* Label & Capacity Badge */}
                  <text
                    x={s.x}
                    y={s.y - 22}
                    textAnchor="middle"
                    fill="#ffffff"
                    fontSize="11"
                    fontWeight="700"
                    fontFamily="'Outfit', sans-serif"
                  >
                    {s.name.split(' (')[0]}
                  </text>
                  <text
                    x={s.x}
                    y={s.y + 30}
                    textAnchor="middle"
                    fill={s.isWarning ? '#CE6969' : s.isRecommended ? '#18B880' : '#8c908e'}
                    fontSize="10"
                    fontWeight="700"
                    fontFamily="'DM Mono', monospace"
                  >
                    {s.current}/{s.capacity} ({pct}%)
                  </text>
                </g>
              )
            })}

          {/* 7. Live Volunteer Couriers with Pulsing GPS (Swiggy/Zomato style) */}
          {(mapFilter === 'all' || mapFilter === 'couriers') &&
            COURIERS.map((c) => {
              const isSelected = selectedCourier === c.id
              return (
                <g
                  key={c.id}
                  className="courier-marker-group"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelectedCourier(c.id)}
                >
                  {/* Swiggy/Zomato Style GPS Pulse Ring */}
                  <circle
                    cx={c.x}
                    cy={c.y}
                    r="18"
                    fill={c.isHero ? 'rgba(249, 119, 29, 0.2)' : 'rgba(24, 184, 128, 0.15)'}
                    stroke={c.isHero ? '#F9771D' : '#18B880'}
                    strokeWidth="1.2"
                  >
                    <animate attributeName="r" values="12;24;12" dur="1.8s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.9;0.2;0.9" dur="1.8s" repeatCount="indefinite" />
                  </circle>

                  {/* Courier Marker Disc */}
                  <circle
                    cx={c.x}
                    cy={c.y}
                    r="11"
                    fill={c.isHero ? '#F9771D' : '#18B880'}
                    stroke="#ffffff"
                    strokeWidth="2"
                    filter="url(#courier-glow)"
                  />

                  {/* Mini Bike Icon */}
                  <circle cx={c.x - 3.5} cy={c.y + 2.5} r="2" fill="#ffffff" />
                  <circle cx={c.x + 3.5} cy={c.y + 2.5} r="2" fill="#ffffff" />
                  <path d={`M ${c.x - 1} ${c.y + 2} L ${c.x} ${c.y - 3} L ${c.x + 2} ${c.y + 2}`} stroke="#ffffff" strokeWidth="1.2" />

                  {/* Courier Name Tag */}
                  <g transform={`translate(${c.x + 14}, ${c.y - 10})`}>
                    <rect width="90" height="22" rx="6" fill="#181818" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                    <text x="6" y="14" fill="#ffffff" fontSize="10" fontWeight="700" fontFamily="'Outfit', sans-serif">
                      {c.id.toUpperCase()} • {c.speed}
                    </text>
                  </g>
                </g>
              )
            })}
        </svg>

        {/* Live Swiggy/Zomato Tracking Drawer Card (Bottom Right Floating Card) */}
        <div className="live-delivery-tracking-card">
          <div className="tracking-top-row">
            <div className="rider-avatar-block">
              <span className="rider-bike-badge">
                <Icon name="bike" size={16} />
              </span>
              <div>
                <h4>{activeCourierData.name}</h4>
                <small>{activeCourierData.vehicle}</small>
              </div>
            </div>
            <span className="live-gps-tag">
              <span className="dot-pulse" />
              <span>GPS Live</span>
            </span>
          </div>

          <div className="tracking-consignment-box">
            <div className="consignment-row">
              <Icon name="box" size={13} />
              <strong>{activeCourierData.cargo}</strong>
            </div>
            <div className="bio-deadline-row">
              <Icon name="clock" size={12} />
              <span>Bio-Safe Buffer: <strong className="text-orange">{activeCourierData.bioBuffer}</strong></span>
            </div>
          </div>

          <div className="tracking-route-steps">
            <div className="step-item">
              <span className="step-dot" />
              <div className="step-info">
                <small>Origin Donor</small>
                <span>{activeCourierData.origin}</span>
              </div>
            </div>
            <div className="step-item">
              <span className={`step-dot ${rerouteResolved ? 'green' : 'orange'}`} />
              <div className="step-info">
                <small>{rerouteResolved ? 'Rerouted Fallback Destination' : 'Target Receiving Shelter'}</small>
                <strong>{activeCourierData.destination}</strong>
              </div>
            </div>
          </div>

          {/* Reroute Trigger Action */}
          {activeCourierData.id === 'courier-07' && (
            <div className="tracking-action-footer">
              {rerouteResolved ? (
                <div className="reroute-confirmed-pill">
                  <Icon name="check" size={13} />
                  <span>Reroute Committed · Relief Camp B (+1.4km locked)</span>
                </div>
              ) : (
                <button
                  className="btn-swiggy-reroute"
                  onClick={onTriggerReroute}
                >
                  <Icon name="zap" size={14} />
                  <span>Execute Reroute to Relief Camp B</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
