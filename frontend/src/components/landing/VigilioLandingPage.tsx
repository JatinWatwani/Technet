import { useState } from 'react'
import { motion } from 'framer-motion'
import { Icon } from '../Icon'

interface VigilioLandingPageProps {
  onEnterDashboard: (tab?: string) => void
}

export function VigilioLandingPage({ onEnterDashboard }: VigilioLandingPageProps) {
  const [hoveredCard, setHoveredCard] = useState<number | null>(null)

  return (
    <div className="landing-page-root">
      {/* 1. Header Navigation */}
      <header className="landing-navbar">
        <div className="landing-brand-wrap" onClick={() => onEnterDashboard('overview')}>
          <div className="landing-logo-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2L4 6V12C4 17.5 7.4 22.6 12 24C16.6 22.6 20 17.5 20 12V6L12 2Z"
                stroke="#18B880"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="12" cy="12" r="3" fill="#18B880" />
            </svg>
          </div>
          <span className="landing-brand-cursive">Vigilio</span>
        </div>

        {/* Center Pill Menu */}
        <nav className="landing-nav-pills">
          <a href="#features" className="nav-pill-link">Product</a>
          <a href="#solutions" className="nav-pill-link">Solutions</a>
          <a href="#security" className="nav-pill-link">Security</a>
          <a href="#mesh" className="nav-pill-link">Fleet Mesh</a>
          <button
            className="nav-pill-cta"
            onClick={() => onEnterDashboard('overview')}
          >
            Launch Mission Control ↗
          </button>
        </nav>
      </header>

      {/* 2. Hero Section with Floating Orbiting Cards */}
      <section className="landing-hero-section">
        {/* Eyebrow Tag */}
        <motion.div
          className="hero-eyebrow-pill"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <span>AUTONOMOUS RESILIENCE ENGINE</span>
        </motion.div>

        {/* Main Headline */}
        <motion.h1
          className="hero-headline"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          Disaster Logistics <br />
          <span className="hero-headline-highlight">Made Simple</span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          className="hero-subheadline"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          Accept real-time surplus rations instantly, eliminate transit spoilage with biological deadlines, and coordinate volunteer couriers with mathematical precision.
        </motion.p>

        {/* Primary CTA Button */}
        <motion.div
          className="hero-cta-wrapper"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <button
            className="hero-primary-cta"
            onClick={() => onEnterDashboard('overview')}
          >
            <span>Explore Vigilio</span>
            <span className="cta-arrow-circle">
              <Icon name="arrowUp" size={13} />
            </span>
          </button>
        </motion.div>

        {/* Floating Orbiting 3D/Glass Cards (Exact pattern from video) */}
        <div className="hero-floating-cards-layer">
          {/* Card 1: Top-Left (Built to Scale / Zero Spoilage) */}
          <motion.div
            className="orbit-card card-top-left"
            animate={{
              y: [0, -12, 0],
              rotate: [-2, 1, -2],
            }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
            whileHover={{ scale: 1.08, rotate: 0 }}
            onClick={() => onEnterDashboard('insights')}
          >
            <div className="orbit-card-visual bg-lavender">
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L15 9H22L16.5 13.5L18.5 20.5L12 16L5.5 20.5L7.5 13.5L2 9H9L12 2Z" fill="#8B5CF6" />
              </svg>
            </div>
            <span className="orbit-card-title">Built to Scale</span>
          </motion.div>

          {/* Card 2: Top-Right (Easy Payments / Dynamic Rerouting) */}
          <motion.div
            className="orbit-card card-top-right"
            animate={{
              y: [0, 14, 0],
              rotate: [3, -1, 3],
            }}
            transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
            whileHover={{ scale: 1.08, rotate: 0 }}
            onClick={() => onEnterDashboard('map')}
          >
            <div className="orbit-card-visual bg-emerald-light">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" fill="#18B880" fillOpacity="0.2" stroke="#18B880" strokeWidth="2" />
                <path d="M8 12L11 15L16 9" stroke="#18B880" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span className="orbit-card-title">Easy Handoffs</span>
          </motion.div>

          {/* Card 3: Middle-Left (More Revenue / Mathematical Invariants) */}
          <motion.div
            className="orbit-card card-mid-left"
            animate={{
              y: [0, -10, 0],
              rotate: [-3, 2, -3],
            }}
            transition={{ duration: 5.5, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
            whileHover={{ scale: 1.08, rotate: 0 }}
            onClick={() => onEnterDashboard('executions')}
          >
            <div className="orbit-card-visual bg-indigo-dark">
              <div className="nested-discs-graphic">
                <span className="disc disc-1" />
                <span className="disc disc-2" />
                <span className="disc disc-3" />
              </div>
            </div>
            <span className="orbit-card-title">Zero Inventory Loss</span>
          </motion.div>

          {/* Card 4: Bottom-Left (Mascot / Volunteer Mesh) */}
          <motion.div
            className="orbit-card card-bot-left"
            animate={{
              y: [0, 12, 0],
              rotate: [-4, 0, -4],
            }}
            transition={{ duration: 6.5, repeat: Infinity, ease: 'easeInOut', delay: 1.5 }}
            whileHover={{ scale: 1.08, rotate: 0 }}
            onClick={() => onEnterDashboard('map')}
          >
            <div className="orbit-card-visual bg-sky-soft">
              <svg width="42" height="42" viewBox="0 0 24 24" fill="none">
                <circle cx="5.5" cy="17" r="2.8" stroke="#3B82F6" strokeWidth="2" />
                <circle cx="18.5" cy="17" r="2.8" stroke="#3B82F6" strokeWidth="2" />
                <path d="m8.5 17 3-7 3.5 7m-6.5 0h6.5l-3.3-6H15l2 3M11.5 10H9" stroke="#3B82F6" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </div>
            <span className="orbit-card-title">Swiggy & Zomato Mesh</span>
          </motion.div>

          {/* Card 5: Bottom-Right (Instant Settlement / Cryptographic Custody) */}
          <motion.div
            className="orbit-card card-bot-right"
            animate={{
              y: [0, -14, 0],
              rotate: [4, -2, 4],
            }}
            transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
            whileHover={{ scale: 1.08, rotate: 0 }}
            onClick={() => onEnterDashboard('alerts')}
          >
            <div className="orbit-card-visual bg-dark-slate">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="#F9771D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M9 12l2 2 4-4" stroke="#F9771D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span className="orbit-card-title">Instant Settlement</span>
          </motion.div>
        </div>
      </section>

      {/* 3. Deep Forest Teal Organic Wavy Section (Frame 00:02-00:03) */}
      <section className="landing-dark-forest-section" id="solutions">
        <div className="dark-forest-container">
          <div className="dark-forest-left">
            <span className="forest-tag">GUARANTEED PHYSICAL CUSTODY</span>
            <h2 className="forest-heading">
              Deliver relief without losing any custody
            </h2>
            <p className="forest-copy">
              Your donors dispatch perishable hot meals and emergency insulin while Vigilio autonomously matches volunteer couriers, enforces biological windows, and dynamically diverts around overcapacity shelters.
            </p>
            <div className="forest-cta-row">
              <button
                className="forest-primary-btn"
                onClick={() => onEnterDashboard('overview')}
              >
                <span>Start Coordinating</span>
              </button>

              {/* Hand-drawn curved arrow annotation */}
              <div className="curved-annotation-wrap">
                <span className="annotation-text">Surplus from donors, meals for communities</span>
                <svg className="curved-arrow-svg" width="46" height="32" viewBox="0 0 46 32" fill="none">
                  <path d="M4 4C14 28 32 28 42 22M42 22L36 18M42 22L38 28" stroke="#18B880" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </div>
          </div>

          <div className="dark-forest-right">
            {/* Photo Card with Floating Glass Overlay */}
            <div className="forest-photo-card">
              <div className="photo-backdrop">
                <div className="coordinator-avatar-badge">
                  <Icon name="bike" size={24} />
                </div>
                <div className="photo-info-strip">
                  <strong>Vikram Sharma</strong>
                  <span>Rapid Relief Lead • Sector 4 Corridor</span>
                </div>
              </div>

              {/* Floating Instant Conversion / Custody Card */}
              <motion.div
                className="floating-custody-card"
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
              >
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
                  <span>Bio-Safe Buffer: <strong>19m remaining</strong></span>
                  <span className="verified-badge">✓ Verified</span>
                </div>
              </motion.div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Horizontal Showcase Section: "Everything in one place" (Frame 00:04-00:06) */}
      <section className="landing-showcase-section" id="features">
        <div className="showcase-header">
          <span className="showcase-step-num">01 — 06</span>
          <h2 className="showcase-title">Everything in one place</h2>
          <p className="showcase-subtext">All emergency supply chains, volunteer couriers, and algorithmic verifications synced live.</p>
        </div>

        <div className="showcase-cards-marquee">
          {/* Showcase Card 1: Consignment QR Scan */}
          <motion.div
            className="showcase-card card-scan"
            whileHover={{ y: -8, scale: 1.02 }}
            onClick={() => onEnterDashboard('overview')}
          >
            <div className="card-top-icon-pill bg-mint">
              <Icon name="target" size={16} />
              <span>Instant Verification</span>
            </div>
            <h4>Accept Consignments</h4>
            <p>Scan incoming donor surplus in seconds. Instant QR & GPS handoff tokens ensure zero double-booking.</p>
            <div className="mini-qr-demo">
              <div className="qr-box">
                <span className="qr-corner top-l" />
                <span className="qr-corner top-r" />
                <span className="qr-corner bot-l" />
                <span className="qr-corner bot-r" />
                <Icon name="command" size={28} />
              </div>
              <span className="scan-label">Scan to verify custody</span>
            </div>
          </motion.div>

          {/* Showcase Card 2: 3D Asset Stack */}
          <motion.div
            className="showcase-card card-tokens"
            whileHover={{ y: -8, scale: 1.02 }}
            onClick={() => onEnterDashboard('insights')}
          >
            <div className="card-top-icon-pill bg-lavender-pill">
              <Icon name="box" size={16} />
              <span>Multi-Cargo Types</span>
            </div>
            <h4>Perishables, Medical & Rations</h4>
            <div className="floating-cargo-badges">
              <div className="cargo-badge-coin coin-meals">
                <Icon name="box" size={16} />
                <span>Cooked Meals (48m)</span>
              </div>
              <div className="cargo-badge-coin coin-insulin">
                <Icon name="shield" size={16} />
                <span>Insulin (2°–8°C)</span>
              </div>
              <div className="cargo-badge-coin coin-rations">
                <Icon name="layers" size={16} />
                <span>Raw Rations (Dry)</span>
              </div>
            </div>
          </motion.div>

          {/* Showcase Card 3: Recent Payments / Invariant Ledger */}
          <motion.div
            className="showcase-card card-ledger"
            whileHover={{ y: -8, scale: 1.02 }}
            onClick={() => onEnterDashboard('executions')}
          >
            <div className="ledger-card-header">
              <div>
                <h4>Recent Allocations</h4>
                <small>Track every consignment</small>
              </div>
              <span className="arrow-btn">↗</span>
            </div>
            <div className="mini-ledger-list">
              <div className="mini-ledger-item">
                <div className="ledger-icon bg-orange">
                  <Icon name="box" size={14} />
                </div>
                <div className="ledger-info">
                  <strong>Banquet Hall A (180 Meals)</strong>
                  <small>Split into 5 sub-tickets</small>
                </div>
                <span className="ledger-val text-green">180 = 180</span>
              </div>
              <div className="mini-ledger-item">
                <div className="ledger-icon bg-blue">
                  <Icon name="shield" size={14} />
                </div>
                <div className="ledger-info">
                  <strong>City Pharmacy (24 Insulin)</strong>
                  <small>Cold-chain thermal lock</small>
                </div>
                <span className="ledger-val text-blue">3.8°C</span>
              </div>
            </div>
          </motion.div>

          {/* Showcase Card 4: Network Telemetry Overview */}
          <motion.div
            className="showcase-card card-analytics"
            whileHover={{ y: -8, scale: 1.02 }}
            onClick={() => onEnterDashboard('insights')}
          >
            <div className="analytics-top-row">
              <h4>Supply Overview</h4>
              <span className="see-all-link">See all ↗</span>
            </div>
            <div className="analytics-big-num">
              <span>$48,250</span>
              <span className="stat-growth-tag">+24% this week</span>
            </div>
            <div className="mini-bar-chart">
              {[40, 65, 30, 85, 95, 60, 100, 75].map((h, i) => (
                <div key={i} className="bar-col">
                  <div className="bar-fill" style={{ height: `${h}%` }} />
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* 5. Bottom Call to Action Section (Frame 00:07-00:08) */}
      <section className="landing-bottom-cta-section">
        <div className="cta-content-box">
          <span className="cta-eyebrow">READY TO DEPLOY</span>
          <h2 className="cta-big-heading">
            Make disaster logistics <br />
            work for you
          </h2>
          <div className="cta-action-container">
            <button
              className="cta-huge-button"
              onClick={() => onEnterDashboard('overview')}
            >
              <span>Get Started</span>
            </button>

            {/* Hand-drawn arrow */}
            <div className="cta-annotation-note">
              <span>Start coordinating relief today</span>
              <svg width="40" height="26" viewBox="0 0 40 26" fill="none">
                <path d="M4 4C12 24 28 24 36 18M36 18L30 14M36 18L32 24" stroke="#18B880" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Footer with Giant Bleed Brand Name */}
      <footer className="landing-footer">
        <div className="footer-top-row">
          <div className="footer-bio-text">
            <p>
              Autonomous disaster logistics made simple for modern resilient communities.
              Distribute donor surplus, preserve physical custody, protect cold-chains, and achieve zero spoilage.
            </p>
          </div>
          <div className="footer-social-icons">
            <button className="social-icon-btn" aria-label="X / Twitter">
              <Icon name="spark" size={16} />
            </button>
            <button className="social-icon-btn" aria-label="GitHub">
              <Icon name="command" size={16} />
            </button>
            <button className="social-icon-btn" aria-label="Network Map">
              <Icon name="map" size={16} />
            </button>
            <button className="social-icon-btn" aria-label="Security">
              <Icon name="shield" size={16} />
            </button>
          </div>
        </div>

        {/* Giant Bottom Bleed Typography */}
        <div className="footer-giant-brand">
          <span>Vigilio</span>
        </div>
      </footer>
    </div>
  )
}
