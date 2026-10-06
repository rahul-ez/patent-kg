import { Link } from 'react-router-dom'

export default function EmptyAnalysis() {
  return <section className="empty-analysis"><h1>No analysis selected</h1><p>Describe an invention to start researching, or reopen a saved case.</p><div><Link to="/analyze" className="btn-primary">New analysis</Link><Link to="/results/cases" className="btn-secondary">Open saved cases</Link></div></section>
}
