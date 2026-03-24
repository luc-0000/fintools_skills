# Engineering Constraints

## Source Anchors

- Source: package.json
- Source: src/main.tsx
- Source: src/router/index.tsx
- Source: src/layouts/ProLayout.tsx
- Source: src/store/index.ts
- Source: src/global.css
- Source: vite.config.ts

## Stack

- Vite
- TypeScript
- React 19
- React Router
- Ant Design 5
- ProComponents / ProLayout
- Zustand
- ECharts

## Styling Constraints

- Active styling is split between:
  - Antd built-in theming
  - ProLayout preset styling
  - `global.css`
  - inline style objects
- No custom token package, CSS Modules, or Tailwind layer is present in active UI code.
- `index.css` is present but not part of the active entry styling chain.

## UI Architecture Constraints

- Pages are route-centric and tightly coupled to page-specific data hooks.
- Reusable UI primitives are sparse.
- Most reuse happens at the library level, not via local design-system components.
- The frontend depends on Vite proxying `/api` to `http://localhost:8888`.
- Standalone log pages intentionally bypass the admin shell route tree.

## Spec Boundary

This spec excludes:

- API/service behavior
- domain workflows
- backend response semantics
- Zustand/model data logic

## Refactor Direction

If this UI is normalized later, the lowest-risk path would be:

- formalize Antd theme tokens in `ConfigProvider`
- replace repeated inline page shell styles with a shared admin-page wrapper
- standardize modal/table/action-bar compositions
- retire or remove unused starter CSS and assets
- replace anchor-click pseudo-buttons with semantic button/link primitives
