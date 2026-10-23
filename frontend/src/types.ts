import type { ReactNode } from 'react'

export type Mode = 'live' | 'chaos'
export type NavId = 'command' | 'supply' | 'rider' | 'shelter' | 'map' | 'library'
export type IconName =
  | 'activity'
  | 'alert'
  | 'arrowDown'
  | 'arrowUp'
  | 'bell'
  | 'bike'
  | 'book'
  | 'box'
  | 'check'
  | 'chevron'
  | 'clock'
  | 'command'
  | 'flame'
  | 'grid'
  | 'home'
  | 'layers'
  | 'lock'
  | 'map'
  | 'more'
  | 'pause'
  | 'people'
  | 'plus'
  | 'refresh'
  | 'route'
  | 'search'
  | 'settings'
  | 'shield'
  | 'spark'
  | 'sun'
  | 'moon'
  | 'target'
  | 'truck'
  | 'water'
  | 'x'
  | 'zap'

export type Batch = {
  id: string
  name: string
  origin: string
  quantity: number
  detail: string
  status: string
  accent: 'lavender' | 'blue' | 'mint'
  progress: number
  icon: IconName
}

export type Lease = {
  id: string
  name: string
  destination: string
  time: string
  progress: number
  status: 'In transit' | 'Claimed' | 'Recovery'
  tone: 'purple' | 'blue' | 'orange'
}

export type Shelter = {
  name: string
  city: string
  capacity: string
  demand: string
  readiness: string[]
  state: 'Ready' | 'At capacity' | 'Review'
  tone: 'mint' | 'orange' | 'rose'
}

export type FeedEvent = {
  time: string
  title: string
  detail: string
  tone: 'purple' | 'orange' | 'mint'
}

export type NavItem = {
  id: NavId
  label: string
  icon: IconName
}

export type SectionHeadingProps = {
  icon: IconName
  eyebrow: string
  title: string
  action?: ReactNode
}
