import React, { useState, useEffect, useRef } from 'react'
import L from 'leaflet'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../../components/Icon'
import { BiologicalClockRing } from '../components/BiologicalClockRing'
import { SwipeToConfirm } from '../components/SwipeToConfirm'

interface MobileActiveRunViewProps {
  onOpenScanHandoff: () => void
  onTriggerDivert: () => void
  isDiverted?: boolean
}

export function MobileActiveRunView({
  onOpenScanHandoff,
  onTriggerDivert,
  isDiverted = true,
}: MobileActiveRunViewProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const courierMarkerRef = useRef<L.Marker | null>(null)

  const [bioSeconds, setBioSeconds] = useState<number>(18 * 60 + 25)
  const [speed, setSpeed] = useState<number>(28)
  const [etaMins, setEtaMins] = useState<number>(9)
  const [isDivertModalOpen, setIsDivertModalOpen] = useState<boolean>(false)

  // Countdown bio timer
  useEffect(() => {
    const timer = setInterval(() => {
      setBioSeconds((prev) => (prev > 10 ? prev - 1 : 18 * 60))
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Initialize Mobile Leaflet Navigation Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return

    const courierPos: [number, number] = [40.7215, -73.9920]
    const reliefCampBPos: [number, number] = [40.7250, -73.9800]
    const donorKitchenPos: [number, number] = [40.7100, -74.0120]
    const blockedShelterPos: [number, number] = [40.7480, -73.9720]

    const map = L.map(mapContainerRef.current, {
      center: courierPos,
      zoom: 14,
      zoomControl: false,
      attributionControl: false,
    })

    // High-contrast clean OpenStreetMap street tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      subdomains: ['a', 'b', 'c'],
      className: 'mobile-leaflet-tiles',
    }).addTo(map)

    // Diverted Path (Active)
    L.polyline([[40.7180, -74.0040], courierPos, [40.7230, -73.9860], reliefCampBPos], {
      color: '#10B981',
      weight: 6,
      opacity: 0.95,
    }).addTo(map)

    // Aborted Path to Blocked Shelter (Red dashed)
    L.polyline([courierPos, [40.7350, -73.9850], blockedShelterPos], {
      color: '#EF4444',
      weight: 3.5,
      dashArray: '6, 8',
      opacity: 0.6,
    }).addTo(map)

    // Destination Pin: Relief Camp B
    const destIcon = L.divIcon({
      className: 'custom-leaflet-marker',
      html: `
        <div class="mobile-map-pin pin-camp">
          <div class="pin-pulse pin-pulse-emerald"></div>
          <div class="pin-symbol">🏕️</div>
          <span class="pin-tag">Relief Camp B (+138)</span>
        </div>
      `,
      iconSize: [44, 44],
      iconAnchor: [22, 22],
    })
    L.marker(reliefCampBPos, { icon: destIcon }).addTo(map)

    // Blocked Pin: Shelter A
    const blockedIcon = L.divIcon({
      className: 'custom-leaflet-marker',
      html: `
        <div class="mobile-map-pin pin-blocked">
          <div class="pin-symbol">⛔</div>
          <span class="pin-tag tag-red">Shelter A (100% Full)</span>
        </div>
      `,
      iconSize: [44, 44],
      iconAnchor: [22, 22],
    })
    L.marker(blockedShelterPos, { icon: blockedIcon }).addTo(map)

    // Courier Marker (Self) with animated heading pulse
    const selfIcon = L.divIcon({
      className: 'custom-leaflet-marker',
      html: `
        <div class="mobile-self-courier-marker">
          <div class="self-radar-wave"></div>
          <div class="self-bike-icon">🚴</div>
          <div class="self-heading-arrow">▲</div>
        </div>
      `,
      iconSize: [52, 52],
      iconAnchor: [26, 26],
    })
    const courierMarker = L.marker(courierPos, { icon: selfIcon }).addTo(map)
    courierMarkerRef.current = courierMarker
    mapInstanceRef.current = map

    // Real-time micro-gliding along street path
    let step = 0
    const navPath = [
      [40.7200, -73.9960],
      [40.7215, -73.9920],
      [40.7228, -73.9880],
      [40.7240, -73.9830],
      reliefCampBPos,
    ]

    const interval = setInterval(() => {
      step = (step + 1) % 150
      const progress = step / 150
      const idx = progress * (navPath.length - 1)
      const baseIdx = Math.floor(idx)
      const nextIdx = Math.min(baseIdx + 1, navPath.length - 1)
      const frac = idx - baseIdx

      const p1 = navPath[baseIdx]
      const p2 = navPath[nextIdx]

      const lat = p1[0] + (p2[0] - p1[0]) * frac
      const lng = p1[1] + (p2[1] - p1[1]) * frac

      if (courierMarkerRef.current) {
        courierMarkerRef.current.setLatLng([lat, lng])
      }
    }, 150)

    setTimeout(() => map.invalidateSize(), 200)

    return () => {
      clearInterval(interval)
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  return (
    <div className="mobile-active-run-view">
      {/* 1. Turn-by-Turn Instruction Banner */}
      <div className="mobile-turn-banner">
        <div className="turn-direction-icon">
          <Icon name="arrowRight" size={24} />
        </div>
        <div className="turn-instruction-text">
          <div className="turn-dist-num">In 350m</div>
          <strong className="turn-street-name">Turn right onto Relief Bypass Corridor</strong>
        </div>
        <div className="turn-eta-pill">
          <span>{etaMins}m</span>
          <small>ETA</small>
        </div>
      </div>

      {/* 2. Interactive Mobile Full-Screen Map Container */}
      <div className="mobile-run-map-container" ref={mapContainerRef} />

      {/* 3. Floating In-Transit Resilience HUD */}
      <div className="mobile-run-floating-hud">
        {/* Dynamic Divert Notice */}
        <div className="mobile-divert-callout">
          <span className="callout-zap">⚡</span>
          <div className="callout-text-wrap">
            <strong>AUTONOMOUS DIVERT ACTIVE</strong>
            <span>Avoided Shelter A (100% full). Proceeding to Relief Camp B (+138 slots).</span>
          </div>
        </div>

        {/* Speed & Biological Window Metrics */}
        <div className="mobile-run-telemetry-row">
          <div className="telemetry-speed-box">
            <span className="speed-val">{speed}</span>
            <span className="speed-unit">km/h</span>
            <small>Bajaj Pulsar 150</small>
          </div>

          <div className="telemetry-cargo-box">
            <div className="cargo-type-tag">40 COOKED MEALS</div>
            <div className="cargo-route-line">Donor Kitchen → Camp B</div>
            <span className="cargo-safe-badge">✓ Protected Custody</span>
          </div>

          {/* Biological Countdown Ring */}
          <div className="telemetry-clock-box">
            <BiologicalClockRing
              remainingSeconds={bioSeconds}
              totalSeconds={48 * 60}
              size={64}
              strokeWidth={5}
            />
          </div>
        </div>

        {/* 4. Delivery Handoff Slide or Scanner Trigger */}
        <div className="mobile-run-action-dock">
          <button
            className="mobile-qr-scan-btn"
            onClick={onOpenScanHandoff}
            title="Scan Camp Manager QR to Verify Delivery"
          >
            <Icon name="shield" size={18} />
            <span>Scan Handoff QR</span>
          </button>

          <SwipeToConfirm
            label="Slide on Arrival at Camp B"
            confirmedLabel="Arrived! Launching Signature..."
            onConfirm={onOpenScanHandoff}
          />
        </div>
      </div>
    </div>
  )
}
