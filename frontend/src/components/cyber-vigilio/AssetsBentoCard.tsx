import { Icon } from '../Icon'
import { Rider } from '../../api/client'

interface AssetsBentoCardProps {
  onSelectAsset?: (id: string) => void
  onOpenFleetMap?: () => void
  riders?: Rider[]
}

export function AssetsBentoCard({ onSelectAsset, onOpenFleetMap, riders }: AssetsBentoCardProps) {
  const liveRiderAssets = riders && riders.length > 0 ? riders.slice(0, 3).map((r, idx) => ({
    id: r.id,
    code: `r-${idx + 1}`,
    name: `Courier #${r.id.replace('rider_', '')} (${r.status})`,
    status: r.status === 'AVAILABLE' ? 'active' : r.status === 'IN_TRANSIT' ? 'rerouted' : 'recovery',
    buffer: `Cap: ${r.remaining_capacity}/${r.capacity}`,
    progress: Math.round(((r.capacity - r.remaining_capacity) / r.capacity) * 100),
  })) : null

  const FLEET_ASSETS = liveRiderAssets || [
    {
      id: 'rider-14',
      code: 'pc1',
      name: 'Rider #14 (Transit: Shelter A)',
      status: 'active',
      buffer: '02:15 left',
      progress: 68,
    },
    {
      id: 'rider-07',
      code: 'ws-it20',
      name: 'Rider #07 (Preserving Custody · Shelter B)',
      status: 'rerouted',
      buffer: '04:42 left',
      progress: 52,
    },
    {
      id: 'rider-12',
      code: 'ip-4',
      name: 'Rider #12 (Stalled · Inventory Recovered)',
      status: 'recovery',
      buffer: 'Revoked',
      progress: 12,
    },
  ]

  return (
    <div className="cyber-bento-card card-assets">
      {/* Card Header */}
      <div className="card-header-row">
        <h3>Assets</h3>
        <button
          className="card-arrow-btn"
          onClick={onOpenFleetMap}
          title="Open Full Fleet Map"
          aria-label="View fleet map"
        >
          <Icon name="arrowUp" size={13} />
        </button>
      </div>

      {/* Fleet Asset Rows */}
      <div className="assets-list">
        {FLEET_ASSETS.map((asset) => (
          <div
            key={asset.id}
            className="asset-row-item"
            onClick={() => onSelectAsset?.(asset.id)}
            title={`${asset.name} · ${asset.buffer}`}
          >
            <div className="asset-left">
              <span className="asset-device-icon">
                <Icon name="bike" size={14} />
              </span>
              <span
                className={`asset-status-dot ${
                  asset.status === 'active'
                    ? 'is-green'
                    : asset.status === 'rerouted'
                    ? 'is-orange'
                    : 'is-coral'
                }`}
              />
              <span className="asset-code">{asset.code}</span>
              <span className="asset-name-tooltip">{asset.name.split(' (')[0]}</span>
            </div>
            <span className="asset-buffer-badge">{asset.buffer}</span>
          </div>
        ))}
      </div>

      {/* Large 12 New Counter at bottom right */}
      <div className="assets-footer-row">
        <div className="assets-meta">
          <span>Active Couriers</span>
          <small>GPS Lock: Verified</small>
        </div>

        <div className="assets-big-count">
          <span className="count-number">{riders && riders.length > 0 ? riders.length : 12}</span>
          <span className="count-label">Fleet</span>
        </div>
      </div>
    </div>
  )
}
