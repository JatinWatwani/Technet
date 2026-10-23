import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'
import { Shelter } from '../../api/client'

interface QuickCreateModalProps {
  isOpen: boolean
  onClose: () => void
  onCreateConsignment: (data: any) => void
  shelters?: Shelter[]
}

export function QuickCreateModal({
  isOpen,
  onClose,
  onCreateConsignment,
  shelters,
}: QuickCreateModalProps) {
  const [cargoName, setCargoName] = useState('Cooked Meals Surplus')
  const [quantity, setQuantity] = useState('180')
  const [donorHub, setDonorHub] = useState('Banquet Hall A')
  const [targetShelter, setTargetShelter] = useState(shelters?.[0]?.id || 'shelter_central')
  const [safeWindow, setSafeWindow] = useState('48')

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onCreateConsignment({
      cargoName,
      quantity: Number(quantity) || 100,
      donorHub,
      targetShelter,
      safeWindow: Number(safeWindow) || 60,
    })
    onClose()
  }

  return (
    <AnimatePresence>
      <div className="cyber-modal-backdrop" onClick={onClose}>
        <motion.div
          className="quick-create-modal"
          onClick={(e) => e.stopPropagation()}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.2 }}
        >
          <div className="modal-header">
            <div>
              <h2>Create New Perishable Consignment</h2>
              <p>Register aid surplus into Vigilio autonomous batch-splitting network.</p>
            </div>
            <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
              <Icon name="x" size={16} />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="modal-form-body">
            <div className="form-group">
              <label>Cargo Description</label>
              <input
                type="text"
                value={cargoName}
                onChange={(e) => setCargoName(e.target.value)}
                required
              />
            </div>

            <div className="form-row-2">
              <div className="form-group">
                <label>Total Portions / Units</label>
                <input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Safe Bio-Expiry Window (Minutes)</label>
                <input
                  type="number"
                  value={safeWindow}
                  onChange={(e) => setSafeWindow(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-row-2">
              <div className="form-group">
                <label>Origin / Donor Kitchen</label>
                <input
                  type="text"
                  value={donorHub}
                  onChange={(e) => setDonorHub(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Primary Destination Hub</label>
                {shelters && shelters.length > 0 ? (
                  <select
                    value={targetShelter}
                    onChange={(e) => setTargetShelter(e.target.value)}
                    required
                    style={{ background: '#242424', color: '#fff', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '6px', padding: '0.6rem 0.8rem' }}
                  >
                    {shelters.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} (Cap: {s.demand_remaining}/{s.receiving_capacity_remaining})
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={targetShelter}
                    onChange={(e) => setTargetShelter(e.target.value)}
                    required
                  />
                )}
              </div>
            </div>

            <div className="modal-form-actions">
              <button type="button" className="btn-cancel" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn-submit-orange">
                <Icon name="plus" size={14} />
                <span>Dispatch into Network</span>
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
