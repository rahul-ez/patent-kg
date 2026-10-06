# Patent research workspace

Primary user: an inventor or researcher comparing an invention against technical prior art. Workflow: describe, retrieve, inspect relationships/ranking, evaluate, refine, revisit saved cases. This is an evidence-review tool, not a legal decision service.

## Direction

A quiet technical workspace, not a marketing dashboard or simulated examiner's desk. The invention is the main object on intake; publications and their evidence are the main objects in results. Left-aligned copy, modest headings, tabular scores, and whitespace establish hierarchy without wrapping every section in cards.

```text
Brand                                    Saved cases / New analysis
Page title + concise explanation
Writing area / research content          Guidance / context
Search settings
Primary action                           Examples
```

## Tokens and rules

- Background #F3F5F5; surface #FFFFFF; text #26343A; secondary #5B6870; divider #D9E0E2; primary action #11675F.
- IBM Plex Sans for headings, controls, and prose. IBM Plex Mono only for publication IDs, technical query text, and numerical comparisons. Legible system fallbacks offline.
- Type: 12px metadata, 14px controls/supporting text, 16px prose, 20px section titles, 30px page titles. No decorative uppercase labels or enormous display headings.
- Spacing: 4, 8, 12, 16, 24, 32, 48px. Content maximum 1120px; prose maximum 76ch. Columns collapse on smaller screens; tables scroll within their own container.
- Radii: 6px controls, 8px editing/graph surfaces, 3px tags. No pill navigation or glass effects.
- Flat sections and separated list rows by default. Borders identify editors, visualizations, or distinct status. No nested shadows.
- Teal for actions/selection; slate for graph context, amber for caution, red for errors. Accompany color with text.
- Visible focus, native labels/radios, 44px primary controls, reduced motion. No page-entry animation; retain interaction feedback and actual loading indicators.

## Boundaries

The `/analyze` screen establishes the language first. Shared tokens, navigation, page headers, results, landing, progress, and saved cases then follow. Preserve route paths, store behavior, request parameters, source links, scores, grouping, error/fallback warnings, and persistence status. No login additions or API changes in this pass.

## Visual verification

Run `npm run build`, then `node tests/serve-ui-fixture.mjs`. Open `http://127.0.0.1:5181` for synthetic, in-memory UI verification, isolated from the real backend and the live workspace's saved state. This is test data, not a live patent analysis. Stop the server after testing.

The fixture supports populated results, graph expansion, evaluation, improvement, saved-run restoration and draft creation. Submit `UI failure test` for the error screen, or `UI fallback test` for missing-results and unsaved/fallback warnings. `GET /__fixture/requests` exposes fixture-only requests for contract checks. Never point this fixture at a real API or database.

Verified in this redesign: production build; TypeScript including unused declarations; existing six state tests; lint; desktop intake and populated results; 390px result layouts and 320px patent/graph/refinement layouts; keyboard weighting and eligibility disclosure; example selection; submission; draft creation; saved-run restoration; evaluation and improvement requests; error recovery and unsaved/no-result warnings. This verifies presentation and fixture interactions, not the live backend or database availability. Source-link and delete handlers remain unchanged.
