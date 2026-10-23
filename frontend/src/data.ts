import type { Batch, Lease, Shelter, FeedEvent, NavItem } from './types'

export const NAV_ITEMS: NavItem[] = [
  { id: 'command', label: 'Command Center', icon: 'command' },
  { id: 'supply', label: 'Supply Exchange', icon: 'box' },
  { id: 'rider', label: 'Rider Console', icon: 'bike' },
  { id: 'shelter', label: 'Shelter Ops', icon: 'home' },
  { id: 'library', label: 'Rule Library', icon: 'book' },
]

export const INITIAL_BATCHES: Batch[] = [
  {
    id: 'meals',
    name: 'Cooked meals',
    origin: 'Banquet Hall A',
    quantity: 180,
    detail: '48m safe window · splits across 5 riders',
    status: 'Split ready',
    accent: 'lavender',
    progress: 72,
    icon: 'box',
  },
  {
    id: 'insulin',
    name: 'Short-life insulin kits',
    origin: 'City Pharmacy',
    quantity: 24,
    detail: 'Cold-chain verified · 2 riders assigned',
    status: 'Protected',
    accent: 'blue',
    progress: 44,
    icon: 'shield',
  },
  {
    id: 'rations',
    name: 'Raw ration kits',
    origin: 'Hostel Mess',
    quantity: 96,
    detail: 'Needs clean water + cooking fuel',
    status: 'Dependency check',
    accent: 'mint',
    progress: 28,
    icon: 'layers',
  },
]

export const INITIAL_LEASES: Lease[] = [
  { id: '14', name: 'Rider #14', destination: 'Shelter A', time: '02:15', progress: 68, status: 'In transit', tone: 'purple' },
  { id: '07', name: 'Rider #07', destination: 'Shelter B', time: '04:42', progress: 52, status: 'In transit', tone: 'blue' },
  { id: '12', name: 'Rider #12', destination: 'Shelter C', time: '00:48', progress: 31, status: 'Claimed', tone: 'orange' },
]

export const INITIAL_SHELTERS: Shelter[] = [
  { name: 'Shelter A', city: 'Downtown East', capacity: '50 / 50', demand: 'Full · receiving paused', readiness: ['water', 'fuel'], state: 'At capacity', tone: 'orange' },
  { name: 'Relief Camp B', city: 'Riverside', capacity: '18 / 138', demand: '120 meals needed', readiness: ['water', 'fuel'], state: 'Ready', tone: 'mint' },
  { name: 'Shelter C', city: 'North Market', capacity: '42 / 90', demand: '48 meals needed', readiness: ['water', 'fuel'], state: 'Review', tone: 'rose' },
]

export const INITIAL_EVENTS: FeedEvent[] = [
  { time: '2m ago', title: 'Reroute preflight complete', detail: 'Rider #07 has Shelter B as a verified fallback.', tone: 'purple' },
  { time: '6m ago', title: 'Cold-chain heartbeat received', detail: 'City Pharmacy handoff remains inside its safety buffer.', tone: 'mint' },
  { time: '11m ago', title: 'Demand signal changed', detail: 'Relief Camp B requested 40 additional meal portions.', tone: 'orange' },
]
