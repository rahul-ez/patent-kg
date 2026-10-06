import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { PatentDocIcon } from '../assets/PatentIcons'

export default function AppHeader({ children }: { children?: ReactNode }) {
  return (
    <header className="app-header">
      <Link to="/" className="app-brand" aria-label="Patent Intelligence home">
        <span className="brand-mark"><PatentDocIcon size={21} animate={false} /></span>
        <span>Patent Intelligence</span>
      </Link>
      <nav className="header-actions" aria-label="Workspace">
        {children ?? <Link to="/results/cases" className="text-link">Saved cases</Link>}
      </nav>
    </header>
  )
}
