import { Icon } from '../Icon'

interface BottomTimelineBarProps {
  onOpenFullTimeline: () => void
  onQuickAddAlert: () => void
  lastAlertTime?: string
}

export function BottomTimelineBar({
  onOpenFullTimeline,
  onQuickAddAlert,
  lastAlertTime = 'Oct 23rd 2026 13:42:11',
}: BottomTimelineBarProps) {
  return (
    <div className="cyber-timeline-bar">
      {/* Created On Segment */}
      <div className="timeline-segment">
        <div className="timeline-avatar">
          <span>MC</span>
        </div>
        <div className="timeline-copy">
          <small>Created on</small>
          <strong>Sep 24th 2026 11:05:02</strong>
        </div>
      </div>

      <div className="timeline-divider" />

      {/* Last Alert Added Segment + Add Button */}
      <div className="timeline-segment center-segment">
        <button
          className="timeline-add-btn"
          onClick={onQuickAddAlert}
          title="Inject Real-Time Alert Event"
          aria-label="Add alert event"
        >
          <Icon name="plus" size={13} />
        </button>
        <div className="timeline-copy">
          <small>Last alert added on</small>
          <strong>{lastAlertTime}</strong>
        </div>
      </div>

      <div className="timeline-divider" />

      {/* Assignee Segment */}
      <div className="timeline-segment">
        <div className="timeline-avatar assignee-avatar">
          <span>HQ</span>
        </div>
        <div className="timeline-copy">
          <small>Coordinator Active</small>
          <strong>Oct 23rd 2026 14:02:11</strong>
        </div>
      </div>

      {/* Solid Vibrant Orange Hero Button: Full timeline */}
      <button
        className="timeline-hero-orange-btn"
        onClick={onOpenFullTimeline}
        title="Open Full Transactional Event Log"
      >
        <span>Full timeline</span>
        <Icon name="chevron" size={14} />
      </button>
    </div>
  )
}
