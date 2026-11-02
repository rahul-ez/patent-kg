import test from 'node:test'
import assert from 'node:assert/strict'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import RecommendationMarkdown from '../src/components/RecommendationMarkdown.ts'

const render = text => renderToStaticMarkup(createElement(RecommendationMarkdown, { children: text }))

test('recommendations render headings, emphasis and nested numbered/bulleted lists', () => {
  const output = render(`### Diagnosis summary

There is **high overlap** with the retrieved sensor descriptions.

#### Suggested changes

1. **Define calibration**: describe the mechanism.
   - Measure signal drift.
   - Record the response time.
2. Compare the *low-power* operating mode.

### Alternative directions

- Motion-aware calibration.
- Event-triggered communication.`)
  assert.match(output, /<h3>Diagnosis summary<\/h3>/)
  assert.match(output, /<h4>Suggested changes<\/h4>/)
  assert.match(output, /<strong>high overlap<\/strong>/)
  assert.match(output, /<em>low-power<\/em>/)
  assert.match(output, /<ol>/)
  assert.match(output, /<ul>/)
  assert.match(output, /<li>Measure signal drift\.<\/li>/)
  assert.doesNotMatch(output, /###|\*\*/)
})

test('plain-text paragraphs and numerical evidence stay readable without rewriting content', () => {
  const output = render('Similarity is 0.749.\n\nKeep the calibration target at 0.7.')
  assert.match(output, /<p>Similarity is 0\.749\.<\/p>/)
  assert.match(output, /<p>Keep the calibration target at 0\.7\.<\/p>/)
  assert.doesNotMatch(output, /<h[1-6]>/)
})

test('GitHub-style tables, quotes, code and safe links render as semantic elements', () => {
  const output = render(`> Compare each change with the retrieved evidence.

| Change | Impact |
| --- | --- |
| Calibration | High |

Use \`threshold\` as a parameter. [Reference](https://example.com/patent).`)
  assert.match(output, /<blockquote>/)
  assert.match(output, /class="recommendation-table"><table>/)
  assert.match(output, /<th>Change<\/th>/)
  assert.match(output, /<code>threshold<\/code>/)
  assert.match(output, /href="https:\/\/example\.com\/patent" target="_blank" rel="noopener noreferrer"/)
})

test('generated markup cannot inject raw HTML, unsafe links or remote images', () => {
  const output = render(`<script>alert('unsafe')</script>

[Unsafe link](javascript:alert%281%29)

![Tracking image](https://example.com/pixel.png)

<img src=x onerror=alert(1)>

**Retained guidance**`)
  assert.doesNotMatch(output, /<script|<img|onerror|javascript:|pixel\.png/)
  assert.match(output, /Unsafe link/)
  assert.match(output, /<strong>Retained guidance<\/strong>/)
})

test('model headings stay inside the existing page/section heading hierarchy', () => {
  const output = render('# Model title\n\n## Main section\n\n##### Fine detail')
  assert.doesNotMatch(output, /<h[1256]>/)
  assert.match(output, /<h3>Model title<\/h3>/)
  assert.match(output, /<h4>Fine detail<\/h4>/)
})
