import { Link, useNavigate } from 'react-router-dom'
import { usePipelineStore } from '../store/usePipelineStore'
import AppHeader from '../components/AppHeader'

const STAGES = [
  ['Extract concepts', 'spaCy and Gemini identify the technical content in your description.'],
  ['Embed the description', 'PatentSBERTa represents the idea in a 768-dimensional space.'],
  ['Retrieve related patents', 'FAISS searches the indexed patent descriptions.'],
  ['Explore relationships', 'Neo4j expands patent families and shared CPC classifications.'],
  ['Review ranking', 'GraphSAGE adds structural context to semantic similarity.'],
  ['Evaluate the evidence', 'Review novelty, non-obviousness, landscape, claim breadth and timing.'],
  ['Refine the invention', 'Explore suggestions grounded in retrieved prior art.'],
]
const STATS = [
  ['58,428', 'Patent publications'],
  ['36,353', 'Distinct texts indexed'],
  ['768', 'Embedding dimensions'],
  ['GraphSAGE', 'Graph model'],
]
export default function LandingPage() {
  const navigate = useNavigate()
  const { reset } = usePipelineStore()
  const handleAnalyze = () => { reset(); navigate('/analyze') }
  return (
    <div className="standalone-page">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <AppHeader />
      <main id="main-content" className="home-main">
        <header className="home-intro">
          <h1>A clearer view of your invention’s prior art.</h1>
          <p>Describe a technical idea, find related patents and examine the connections that a keyword search can miss.</p>
          <div className="home-actions">
            <button id="cta-analyze" className="btn-primary" onClick={handleAnalyze}>Analyze an idea</button>
            <button id="cta-architecture" className="text-button" onClick={() => document.getElementById('architecture')?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })}>How analysis works</button>
          </div>
          <p className="advisory-note">Evidence for early research. Not a legal opinion.</p>
        </header>
        <section className="home-resume">
          <h2>Pick up your research</h2><p>Reopen a saved analysis, compare its evidence, or run a revised description in the same case.</p>
          <Link className="text-link" to="/results/cases">Open saved cases</Link>
        </section>
        <section id="architecture" className="home-process">
          <div><h2>How analysis works</h2><p>Follow the evidence from your description to possible refinements.</p></div>
          <ol className="process-list">{STAGES.map(([title, detail]) => <li key={title}><h3>{title}</h3><p>{detail}</p></li>)}</ol>
        </section>
        <section className="dataset-reference" aria-label="Dataset reference">
          <h2>Dataset reference</h2><dl>{STATS.map(([value, label]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
        </section>
      </main>
      <footer className="app-footer">Patent Intelligence Platform <span>Python, Gemini, spaCy, FAISS, Neo4j, PyTorch Geometric and React</span></footer>
    </div>
  )
}
