import { useState, useEffect, useRef } from 'react'
import L from 'leaflet'
import { Icon } from '../Icon'

interface LandingHeroMapProps {
  onOpenFullMap?: () => void
}

export function LandingHeroMap({ onOpenFullMap }: LandingHeroMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const courierMarkerRef = useRef<L.Marker | null>(null)
  const animFrameRef = useRef<number | null>(null)

  const [isDivertActive, setIsDivertActive] = useState<boolean>(true)
  const [telemetryCoords, setTelemetryCoords] = useState<[number, number]>([40.7210, -73.9920])
  const [bioSafeSeconds, setBioSafeSeconds] = useState<number>(19 * 60 + 42)

  // Real GPS Coordinates matching the disaster response network
  const donorBanquet: [number, number] = [40.7100, -74.0120]
  const shelterNorthBlocked: [number, number] = [40.7480, -73.9720]
  const reliefCampB: [number, number] = [40.7250, -73.9800]
  const junctionDivert: [number, number] = [40.7190, -74.0010]

  // Countdown timer for biological window
  useEffect(() => {
    const timer = setInterval(() => {
      setBioSafeSeconds((prev) => (prev > 60 ? prev - 1 : 19 * 60))
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Initialize interactive Leaflet map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return

    const map = L.map(mapContainerRef.current, {
      center: [40.7270, -73.9920],
      zoom: 13,
      zoomControl: false,
      attributionControl: false,
      scrollWheelZoom: true,
      dragging: true,
    })

    // Add OpenStreetMap tiles with custom dark/emerald filter
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      subdomains: ['a', 'b', 'c'],
      className: 'landing-leaflet-tile',
    }).addTo(map)

    // Add minimal zoom controls on bottom right
    L.control.zoom({ position: 'bottomright' }).addTo(map)

    // 1. Origin: Banquet Hall Donor Kitchen Marker
    const originIcon = L.divIcon({
      className: 'custom-leaflet-marker',
      html: `
        <div class="landing-pin-origin">
          <div class="pin-pulse pin-pulse-green"></div>
          <div class="pin-core pin-core-green">🍲</div>
          <div class="pin-label">Donor Kitchen</div>
        </div>
      `,
      iconSize: [44, 44],
      iconAnchor: [22, 22],
    })
    L.marker(donorBanquet, { icon: originIcon })
      .bindPopup('<strong>Banquet Hall A</strong><br/>Surplus: 40 Fresh Hot Meals<br/>Safe window: 55 mins')
      .addTo(map)

    // 2. Blocked Shelter A (Overcapacity) Marker
    const blockedIcon = L.divIcon({
      className: 'custom-leaflet-marker',
      html: `
        <div class="landing-pin-shelter pin-shelter-blocked">
          <div class="pin-pulse pin-pulse-red"></div>
          <div class="pin-core pin-core-red">⛔</div>
          <div class="pin-label-warning">Shelter A (100% Full)</div>
        </div>
      `,
      iconSize: [44, 44],
      iconAnchor: [22, 22],
    })
    L.marker(shelterNorthBlocked, { icon: blockedIcon })
      .bindPopup('<strong>Downtown Shelter A</strong><br/><span style="color:#ef4444;font-weight:bold;">100% OVERCAPACITY (50/50)</span><br/>Autonomous diversion active')
      .addTo(map)

    // 3. Rerouted Destination: Relief Camp B Marker
    const reliefCampIcon = L.divIcon({
      className: 'custom-leaflet-marker',
      html: `
        <div class="landing-pin-shelter pin-shelter-target">
          <div class="pin-pulse pin-pulse-emerald"></div>
          <div class="pin-core pin-core-emerald">🏕️</div>
          <div class="pin-label-emerald">Relief Camp B (+138)</div>
        </div>
      `,
      iconSize: [44, 44],
      iconAnchor: [22, 22],
    })
    L.marker(reliefCampB, { icon: reliefCampIcon })
      .bindPopup('<strong>Relief Camp B</strong><br/><span style="color:#10b981;font-weight:bold;">AVAILABLE CAPACITY: 138</span><br/>Destination accepted')
      .addTo(map)

    // 4. Cancelled Route Polyline (Dashed Red to Blocked Shelter)
    L.polyline([donorBanquet, junctionDivert, [40.7350, -73.9850], shelterNorthBlocked], {
      color: '#ef4444',
      weight: 3.5,
      opacity: 0.6,
      dashArray: '6, 8',
    }).addTo(map)

    // 5. Active Divert Polyline (Glowing Neon Emerald to Relief Camp B)
    const divertPolyline = L.polyline([donorBanquet, junctionDivert, [40.7220, -73.9910], reliefCampB], {
      color: '#10b981',
      weight: 5,
      opacity: 0.95,
      className: 'glowing-reroute-polyline',
    }).addTo(map)

    // 6. Courier Marker (Vikram Sharma on E-Bike)
    const courierIcon = L.divIcon({
      className: 'custom-leaflet-marker',
      html: `
        <div class="landing-courier-marker">
          <div class="courier-radar-pulse"></div>
          <div class="courier-vehicle-icon">🚴</div>
          <div class="courier-tag-badge">#07 Vikram</div>
        </div>
      `,
      iconSize: [48, 48],
      iconAnchor: [24, 24],
    })

    const courierMarker = L.marker([40.7210, -73.9920], { icon: courierIcon })
      .bindPopup('<strong>Courier #07 • Vikram Sharma</strong><br/>Cargo: 40 Fresh Meals<br/>Speed: 26 km/h<br/>Status: Diverted to Relief Camp B')
      .addTo(map)

    courierMarkerRef.current = courierMarker
    mapInstanceRef.current = map

    // Smooth real-time courier gliding animation along diversion path
    let step = 0
    const divertPath = [
      donorBanquet,
      [40.7145, -74.0065],
      junctionDivert,
      [40.7205, -73.9960],
      [40.7215, -73.9920],
      [40.7230, -73.9860],
      reliefCampB,
    ]

    const interval = setInterval(() => {
      step = (step + 1) % 180
      const progress = (Math.sin((step / 180) * Math.PI * 2 - Math.PI / 2) + 1) / 2
      const pathIdx = progress * (divertPath.length - 1)
      const baseIdx = Math.floor(pathIdx)
      const frac = pathIdx - baseIdx
      const nextIdx = Math.min(baseIdx + 1, divertPath.length - 1)

      const p1 = divertPath[baseIdx]
      const p2 = divertPath[nextIdx]

      const currentLat = p1[0] + (p2[0] - p1[0]) * frac
      const currentLng = p1[1] + (p2[1] - p1[1]) * frac

      if (courierMarkerRef.current) {
        courierMarkerRef.current.setLatLng([currentLat, currentLng])
      }
      setTelemetryCoords([
        Number(currentLat.toFixed(4)),
        Number(currentLng.toFixed(4)),
      ])
    }, 120)

    // Trigger map resize after DOM mount
    setTimeout(() => {
      map.invalidateSize()
    }, 250)

    return () => {
      clearInterval(interval)
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  const formatBioTimer = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60)
    const secs = totalSec % 60
    return `${mins}m ${secs.toString().padStart(2, '0')}s remaining`
  }

  return (
    <div className="landing-hero-map-wrapper">
      {/* 1. Real Interactive Leaflet Street & Dispatch Map */}
      <div
        id="landing-hero-leaflet-map"
        ref={mapContainerRef}
        className="landing-leaflet-container"
        style={{ width: '100%', height: '420px', borderRadius: '28px' }}
      />

      {/* 2. Top-Left HUD: Coordinator Profile Pill */}
      <div className="landing-map-top-left-hud">
        <div className="coordinator-avatar-badge">
          <Icon name="bike" size={22} />
        </div>
        <div className="photo-info-strip">
          <strong>Vikram Sharma</strong>
          <span>Rapid Relief Lead • Sector 4 Corridor</span>
        </div>
      </div>

      {/* 3. Top-Right HUD: Real-time Live Radar & Telemetry Badges */}
      <div className="landing-map-top-right-hud">
        <div className="landing-radar-status-chip">
          <span className="live-radar-dot"></span>
          <span>LIVE GPS TELEMETRY</span>
        </div>
        <div className="landing-coords-badge">
          <span>{telemetryCoords[0]}° N, {Math.abs(telemetryCoords[1])}° W</span>
          <span className="badge-speed">26 km/h</span>
        </div>
        {onOpenFullMap && (
          <button
            className="landing-expand-map-btn"
            onClick={onOpenFullMap}
            title="Open Full Screen Interactive Fleet Radar"
          >
            <span>Full Map</span>
            <Icon name="arrowUp" size={12} />
          </button>
        )}
      </div>

      {/* 4. Bottom-Left Floating Custody Card (Enhanced Glassmorphism) */}
      <div className="floating-custody-card landing-custody-card-enhanced">
        <div className="custody-card-top">
          <span className="custody-chip">
            <Icon name="zap" size={13} />
            <span>Real-Time Divert</span>
          </span>
          <span className="custody-pct text-green">+40 Meals</span>
        </div>
        <div className="custody-card-body">
          <small>Auto-Reroute Activated</small>
          <strong>Relief Camp B (Capacity 138)</strong>
        </div>
        <div className="custody-time-row">
          <span>Bio-Safe Buffer: <strong>{formatBioTimer(bioSafeSeconds)}</strong></span>
          <span className="verified-badge">✓ Verified</span>
        </div>

        {/* Real-time diversion rationale indicator */}
        <div className="custody-alert-callout">
          <span className="callout-icon">⚠️</span>
          <span className="callout-text">
            Avoided Downtown Shelter (100% capacity). Diverted +1.4km along clear bypass.
          </span>
        </div>
      </div>
    </div>
  )
}
