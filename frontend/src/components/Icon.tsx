import type { ReactNode } from 'react'
import type { IconName } from '../types'

export function Icon({ name, size = 18, strokeWidth = 1.8 }: { name: IconName; size?: number; strokeWidth?: number }) {
  const common = { stroke: 'currentColor', strokeWidth, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none' }

  const content: Record<IconName, ReactNode> = {
    activity: <><path {...common} d="M3 12h4l2.2-6 3.6 12 2.3-6H21" /></>,
    alert: <><path {...common} d="M10.3 4.2 3.8 16a1.5 1.5 0 0 0 1.3 2.2h13.8a1.5 1.5 0 0 0 1.3-2.2L13.7 4.2a2 2 0 0 0-3.4 0Z" /><path {...common} d="M12 9v3.7M12 15.6h.01" /></>,
    arrowDown: <><path {...common} d="M12 4v15M6.5 13.5 12 19l5.5-5.5" /></>,
    arrowUp: <><path {...common} d="M12 20V5M6.5 10.5 12 5l5.5 5.5" /></>,
    bell: <><path {...common} d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4" /></>,
    bike: <><circle {...common} cx="5.5" cy="17" r="2.8" /><circle {...common} cx="18.5" cy="17" r="2.8" /><path {...common} d="m8.5 17 3-7 3.5 7m-6.5 0h6.5l-3.3-6H15l2 3M11.5 10H9" /></>,
    book: <><path {...common} d="M4.5 5.5A2.5 2.5 0 0 1 7 3h12v16H7a2.5 2.5 0 0 0-2.5 2.5v-16Z" /><path {...common} d="M7 19h12" /></>,
    box: <><path {...common} d="m4 7 8-4 8 4-8 4-8-4Z" /><path {...common} d="M4 7v10l8 4 8-4V7M12 11v10" /></>,
    check: <><path {...common} d="m5 12 4.2 4.2L19 6.5" /></>,
    chevron: <><path {...common} d="m7 10 5 5 5-5" /></>,
    clock: <><circle {...common} cx="12" cy="12" r="8.5" /><path {...common} d="M12 7v5l3.5 2" /></>,
    command: <><rect {...common} x="4" y="4" width="6" height="6" rx="1.5" /><rect {...common} x="14" y="4" width="6" height="6" rx="1.5" /><rect {...common} x="4" y="14" width="6" height="6" rx="1.5" /><rect {...common} x="14" y="14" width="6" height="6" rx="1.5" /></>,
    flame: <><path {...common} d="M12.2 21c4 0 6.8-2.5 6.8-6.2 0-3-1.6-5.2-4.7-7.7.2 2.1-.6 3.2-1.6 4.1.1-4.1-1.7-6.9-4.1-8.7.1 3.1-2.6 5.3-2.6 9.3 0 5.1 2.6 9.2 6.2 9.2Z" /></>,
    grid: <><path {...common} d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" /></>,
    home: <><path {...common} d="m4 10 8-6 8 6v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-9Z" /><path {...common} d="M9 20v-6h6v6" /></>,
    layers: <><path {...common} d="m12 3 8 4-8 4-8-4 8-4ZM4 12l8 4 8-4M4 17l8 4 8-4" /></>,
    lock: <><rect {...common} x="5" y="10" width="14" height="10" rx="2" /><path {...common} d="M8 10V7a4 4 0 0 1 8 0v3" /></>,
    map: <><path {...common} d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Z" /><path {...common} d="M9 3v15M15 6v15" /></>,
    more: <><circle cx="5" cy="12" r="1" fill="currentColor" /><circle cx="12" cy="12" r="1" fill="currentColor" /><circle cx="19" cy="12" r="1" fill="currentColor" /></>,
    pause: <><path {...common} d="M8 5v14M16 5v14" /></>,
    people: <><circle {...common} cx="9" cy="8" r="3" /><path {...common} d="M3.5 19c.4-3 2.2-5 5.5-5s5.1 2 5.5 5M16 5.5a2.6 2.6 0 0 1 0 5M16 14c2.5.2 3.9 1.8 4.5 4" /></>,
    plus: <><path {...common} d="M12 5v14M5 12h14" /></>,
    refresh: <><path {...common} d="M20 11a8 8 0 0 0-14-4.9L4 8M4 4v4h4M4 13a8 8 0 0 0 14 4.9l2-1.9M20 20v-4h-4" /></>,
    route: <><circle {...common} cx="6" cy="18" r="2" /><circle {...common} cx="18" cy="6" r="2" /><path {...common} d="M8 18c5 0 2-8 8-8M8 6c3 0 3 4 4 5" /></>,
    search: <><circle {...common} cx="10.8" cy="10.8" r="6.3" /><path {...common} d="m16 16 4 4" /></>,
    settings: <><path {...common} d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z" /><path {...common} d="m19 13 .1-2 1.8-1.3-2-3.4-2.1.7-1.5-1.3-.3-2.2H10l-.3 2.2-1.5 1.3-2.1-.7-2 3.4L5.9 11 6 13l-1.8 1.3 2 3.4 2.1-.7 1.5 1.3.3 2.2h4l.3-2.2 1.5-1.3 2.1.7 2-3.4L19 13Z" /></>,
    shield: <><path {...common} d="M12 3 19 6v5c0 4.7-2.8 8-7 10-4.2-2-7-5.3-7-10V6l7-3Z" /><path {...common} d="m9 12 2 2 4-4" /></>,
    spark: <><path {...common} d="m12 3 1.4 5.6L19 10l-5.6 1.4L12 17l-1.4-5.6L5 10l5.6-1.4L12 3ZM19 16l.6 2.4L22 19l-2.4.6L19 22l-.6-2.4L16 19l2.4-.6L19 16Z" /></>,
    sun: <><circle {...common} cx="12" cy="12" r="4" /><path {...common} d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" /></>,
    moon: <><path {...common} d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" /></>,
    target: <><circle {...common} cx="12" cy="12" r="8.5" /><circle {...common} cx="12" cy="12" r="4" /><path {...common} d="M12 3.5V6M20.5 12H18M12 20.5V18M3.5 12H6" /></>,
    truck: <><path {...common} d="M3 6h11v10H3zM14 10h4l3 3v3h-7z" /><circle {...common} cx="7" cy="18" r="2" /><circle {...common} cx="18" cy="18" r="2" /></>,
    water: <><path {...common} d="M12 3S6.5 9.1 6.5 13.2a5.5 5.5 0 0 0 11 0C17.5 9.1 12 3 12 3Z" /><path {...common} d="M9.5 14.5c.3 1.1 1 1.8 2.2 2" /></>,
    x: <><path {...common} d="m6 6 12 12M18 6 6 18" /></>,
    zap: <><path {...common} d="m13 2-8 11h6l-1 9 8-11h-6l1-9Z" /></>,
  }

  return <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">{content[name]}</svg>
}
