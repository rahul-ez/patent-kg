import { createElement, Fragment } from 'react'
import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

// The page and recommendation section already supply h1/h2 headings.
const components: Components = {
  h1: 'h3',
  h2: 'h3',
  h3: 'h3',
  h4: 'h4',
  h5: 'h4',
  h6: 'h4',
  a: ({ href, children }) => href
    ? createElement('a', { href, target: '_blank', rel: 'noopener noreferrer' }, children)
    : createElement(Fragment, null, children),
  table: ({ children }) => createElement('div', { className: 'recommendation-table' },
    createElement('table', null, children)),
}

export default function RecommendationMarkdown({ children }: { children: string }) {
  return createElement('div', { className: 'recommendation-markdown' },
    createElement(Markdown, {
      remarkPlugins: [remarkGfm],
      components,
      skipHtml: true,
      disallowedElements: ['img'],
    }, children))
}
