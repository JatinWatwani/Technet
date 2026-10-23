import type { ReactNode } from 'react'
import { Icon } from '../Icon'
import type { IconName } from '../../types'

interface SectionHeadingProps {
  icon: IconName
  eyebrow: string
  title: string
  action?: ReactNode
}

export function SectionHeading({ icon, eyebrow, title, action }: SectionHeadingProps) {
  return (
    <div className="section-heading">
      <div className="section-title">
        <div className="section-icon">
          <Icon name={icon} size={16} />
        </div>
        <div>
          <span>{eyebrow}</span>
          <h2>{title}</h2>
        </div>
      </div>
      {action}
    </div>
  )
}
