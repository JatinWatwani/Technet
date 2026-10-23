import { useState, useEffect, useRef } from 'react'
import L from 'leaflet'
import { Icon } from '../Icon'
import { Shelter, Rider } from '../../api/client'

interface LiveFleetMapViewProps {
  onTriggerReroute: () => void
  rerouteResolved: boolean
  shelters?: Shelter[]
  riders?: Rider[]
}

interface CourierNode {
  id: string
  name: string
  vehicle: string
  cargo: string
  bioBuffer: string
  origin: string
  destination: string
  status: string
  speed: string
  battery: string
  isHero: boolean
  coords: [number, number]
  targetCoords: [number, number]
  routeWaypoints: [number, number][]
}

export function LiveFleetMapView({
  onTriggerReroute,
  rerouteResolved,
  shelters,
  riders,
}: LiveFleetMapViewProps) {
  const [selectedCourier, setSelectedCourier] = useState<string>('courier-07')
  const [selectedShelter, setSelectedShelter] = useState<string | null>(null)
  const [mapFilter, setMapFilter] = useState<'all' | 'couriers' | 'shelters'>('all')

  const mapContainerRef = useRef<HTMLDivElement | null>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const courierMarkersRef = useRef<Record<string, L.Marker>>({})
  const routePolylineRef = useRef<L.Polyline | null>(null)
  const animFrameRef = useRef<number | null>(null)

  // Real GPS Waypoint Nodes
  const donorBanquet: [number, number] = [40.7100, -74.0120]
  const donorPharmacy: [number, number] = [40.7280, -74.0020]
  const donorHostel: [number, number] = [40.7380, -74.0080]

  const shelterNorthPos: [number, number] = [40.7500, -73.9700]
  const shelterCentralPos: [number, number] = [40.7150, -74.0000]
  const shelterEastPos: [number, number] = [40.7250, -73.9800] // Relief Camp B
  const shelterWestPos: [number, number] = [40.7350, -74.0150]

  // Live shelter lookup from backend if available
  const shelterCentral = shelters?.find((s) => s.id === 'shelter_central' || s.name.includes('Central'))
  const shelterEast = shelters?.find((s) => s.id === 'shelter_eastside' || s.name.includes('East'))
  const shelterNorth = shelters?.find((s) => s.id === 'shelter_north' || s.name.includes('North'))

  // Real GPS-mapped shelters
  const SHELTER_NODES = [
    {
      id: 'shelter-a',
      name: shelterNorth?.name || 'Shelter A (North Hub)',
      current: shelterNorth?.demand_remaining ?? 50,
      capacity: shelterNorth?.receiving_capacity_remaining ?? 50,
      status: shelterNorth?.status === 'CLOSED' ? 'CLOSED · Overflow divert triggered' : 'Critical · Capacity Capped at 50/50',
      latLng: shelterNorthPos,
      isWarning: true,
      address: 'Sector 4, North Relief Corridor',
    },
    {
      id: 'shelter-b',
      name: shelterEast?.name || 'Relief Camp B (Fallback Hub)',
      current: rerouteResolved ? (shelterEast?.demand_remaining ?? 58) : 18,
      capacity: shelterEast?.receiving_capacity_remaining ?? 138,
      status: rerouteResolved ? 'Committed: +40 Meals Received' : 'Available · Receiving Hub',
      latLng: shelterEastPos,
      isWarning: false,
      isRecommended: true,
      address: 'Sector 9, Eastern Highway Junction',
    },
    {
      id: 'shelter-central',
      name: shelterCentral?.name || 'Downtown Central Emergency Shelter',
      current: shelterCentral?.demand_remaining ?? 30,
      capacity: shelterCentral?.receiving_capacity_remaining ?? 120,
      status: 'Prerequisite Active: Clean Water',
      latLng: shelterCentralPos,
      isWarning: false,
      address: 'Downtown Sector 1, Central Hub',
    },
    {
      id: 'shelter-west',
      name: 'Westside Relief Station',
      current: 40,
      capacity: 80,
      status: 'Reception Nominal',
      latLng: shelterWestPos,
      isWarning: false,
      address: 'Sector 7, Westside Embankment',
    },
  ]

  // Real GPS Courier Fleet Data
  const COURIERS: CourierNode[] = [
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
      battery: '82%',
      isHero: true,
      coords: rerouteResolved ? [40.7210, -73.9920] : [40.7320, -73.9880],
      targetCoords: rerouteResolved ? shelterEastPos : shelterNorthPos,
      routeWaypoints: rerouteResolved
        ? [donorBanquet, [40.7180, -74.0040], [40.7210, -73.9920], shelterEastPos]
        : [donorBanquet, [40.7250, -74.0000], [40.7350, -73.9880], shelterNorthPos],
    },
    {
      id: 'courier-14',
      name: 'Courier #14 (Rider Ananya P.)',
      vehicle: 'Hero E-Bike • Cargo',
      cargo: '60 Bread & Fruit Kits',
      bioBuffer: '65m buffer',
      origin: 'Banquet Hall A',
      destination: 'Westside Relief Station',
      status: 'Normal Delivery Transit',
      speed: '22 km/h',
      battery: '94%',
      isHero: false,
      coords: [40.7220, -74.0110],
      targetCoords: shelterWestPos,
      routeWaypoints: [donorBanquet, [40.7220, -74.0110], shelterWestPos],
    },
    {
      id: 'courier-02',
      name: 'Courier #02 (Driver R. Sharma)',
      vehicle: 'Insulated Refrigerated Van',
      cargo: '24 Insulin Kits (Cold-Chain 3.8°C)',
      bioBuffer: '42m bio-safe window',
      origin: 'City Pharmacy Central',
      destination: 'Downtown Central Shelter',
      status: 'Cold-Chain Secure',
      speed: '34 km/h',
      battery: '100%',
      isHero: false,
      coords: [40.7210, -74.0020],
      targetCoords: shelterCentralPos,
      routeWaypoints: [donorPharmacy, [40.7210, -74.0020], shelterCentralPos],
    },
  ]

  const activeCourierData = COURIERS.find((c) => c.id === selectedCourier) || COURIERS[0]

  // Initialize Real Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return

    // Ensure previous instance is wiped
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove()
      mapInstanceRef.current = null
    }

    const map = L.map(mapContainerRef.current, {
      center: [40.7280, -73.9980],
      zoom: 13,
      zoomControl: true,
      attributionControl: false,
    })

    // High-resolution OpenStreetMap tiles (No API key required)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      subdomains: ['a', 'b', 'c'],
    }).addTo(map)

    mapInstanceRef.current = map

    // 1. Render Donor Kitchens
    const donorLayer = L.layerGroup().addTo(map)
    const donors = [
      { name: 'Banquet Hall A (180 Meals)', pos: donorBanquet },
      { name: 'City Pharmacy Central', pos: donorPharmacy },
      { name: 'Hostel Mess Kitchen', pos: donorHostel },
    ]

    donors.forEach((d) => {
      const donorIcon = L.divIcon({
        className: 'custom-leaflet-marker',
        html: `
          <div class="marker-donor-wrapper">
            <div class="donor-pin-badge">
              <span>🏬</span>
              <strong>${d.name}</strong>
            </div>
          </div>
        `,
        iconSize: [120, 30],
        iconAnchor: [60, 28],
      })
      L.marker(d.pos, { icon: donorIcon }).addTo(donorLayer)
    })

    // 2. Render Shelters
    const shelterLayer = L.layerGroup().addTo(map)
    SHELTER_NODES.forEach((s) => {
      const isCrit = s.isWarning && !rerouteResolved
      const isRec = s.isRecommended
      const shelterIcon = L.divIcon({
        className: 'custom-leaflet-marker',
        html: `
          <div class="marker-shelter-wrapper" id="marker-${s.id}">
            <div class="shelter-pin-badge ${isCrit ? 'is-critical' : isRec ? 'is-recommended' : ''}">
              <span>${isCrit ? '⚠' : isRec ? '✓' : '🏥'}</span>
              <strong>${s.name.split(' (')[0]}</strong>
              <span class="shelter-capacity-pill">${s.current}/${s.capacity}</span>
            </div>
          </div>
        `,
        iconSize: [160, 36],
        iconAnchor: [80, 36],
      })

      const marker = L.marker(s.latLng, { icon: shelterIcon }).addTo(shelterLayer)
      marker.on('click', () => {
        setSelectedShelter(s.id)
      })
    })

    // 3. Render Couriers
    const courierLayer = L.layerGroup().addTo(map)
    courierMarkersRef.current = {}

    COURIERS.forEach((c) => {
      const isHero = c.isHero
      const icon = L.divIcon({
        className: 'custom-leaflet-marker',
        html: `
          <div class="marker-courier-wrapper" id="courier-pin-${c.id}">
            ${isHero ? '<div class="courier-pulse-ring"></div>' : ''}
            <div class="courier-disc-badge ${isHero ? '' : 'is-green'}">
              <span>🚴</span>
            </div>
            <div class="courier-label-pill">
              ${c.id.toUpperCase()} • ${c.speed}
            </div>
          </div>
        `,
        iconSize: [90, 48],
        iconAnchor: [45, 24],
      })

      const marker = L.marker(c.coords, { icon }).addTo(courierLayer)
      marker.on('click', () => {
        setSelectedCourier(c.id)
      })
      courierMarkersRef.current[c.id] = marker
    })

    // 4. Render Active Delivery Polyline Route
    const activeCourier = COURIERS.find((c) => c.id === selectedCourier) || COURIERS[0]
    const routeColor = rerouteResolved ? '#18B880' : '#F9771D'

    const polyline = L.polyline(activeCourier.routeWaypoints, {
      color: routeColor,
      weight: 4,
      dashArray: '8, 8',
      opacity: 0.9,
    }).addTo(map)

    routePolylineRef.current = polyline

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      map.remove()
      mapInstanceRef.current = null
    }
  }, [rerouteResolved])

  // Real-time animated GPS pulse movement simulation
  useEffect(() => {
    let t = 0
    const interval = setInterval(() => {
      t += 0.04
      const heroMarker = courierMarkersRef.current['courier-07']
      if (heroMarker) {
        // Micro-oscillate/glide along route
        const baseLat = rerouteResolved ? 40.7225 : 40.7320
        const baseLng = rerouteResolved ? -73.9900 : -73.9880
        const deltaLat = Math.sin(t) * 0.0018
        const deltaLng = Math.cos(t) * 0.0022
        heroMarker.setLatLng([baseLat + deltaLat, baseLng + deltaLng])
      }

      const courier14 = courierMarkersRef.current['courier-14']
      if (courier14) {
        const deltaLat = Math.cos(t * 0.8) * 0.0012
        const deltaLng = Math.sin(t * 0.8) * 0.0015
        courier14.setLatLng([40.7220 + deltaLat, -74.0110 + deltaLng])
      }
    }, 120)

    return () => clearInterval(interval)
  }, [rerouteResolved])

  // Center on selected courier
  const handleSelectCourier = (id: string) => {
    setSelectedCourier(id)
    const c = COURIERS.find((item) => item.id === id)
    if (c && mapInstanceRef.current) {
      mapInstanceRef.current.panTo(c.coords, { animate: true, duration: 0.8 })
    }
  }

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
            <h3>Live Volunteer Fleet & Geospatial Shelter Map</h3>
            <p>Real-time OpenStreetMap Swiggy/Zomato GPS courier tracking, dynamic bio-window buffers, and in-transit rerouting</p>
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
            Volunteer Couriers ({riders && riders.length > 0 ? riders.length : 3})
          </button>
          <button
            className={`map-filter-btn ${mapFilter === 'shelters' ? 'is-active' : ''}`}
            onClick={() => setMapFilter('shelters')}
          >
            Shelter Capacities ({shelters && shelters.length > 0 ? shelters.length : 4})
          </button>
        </div>
      </div>

      {/* Main Realtime Map Stage */}
      <div className="map-stage-wrapper">
        <div
          ref={mapContainerRef}
          id="leaflet-fleet-map"
          style={{ width: '100%', height: '560px' }}
        />

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
export default LiveFleetMapView
