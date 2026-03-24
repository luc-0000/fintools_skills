# Components

## Source Anchors

- Source: src/components/PopupForm/index.tsx
- Source: src/layouts/ProLayout.tsx
- Source: src/pages/Pools/components/PoolList.tsx
- Source: src/pages/Pools/components/StockList.tsx
- Source: src/pages/Rules/components/RuleList.tsx
- Source: src/pages/Pools/components/PoolList.tsx
- Source: src/pages/Pools/components/StockList.tsx
- Source: src/pages/Simulators/components/SimulatorAgent.tsx
- Source: src/pages/AgentLog/index.tsx

## Inventory

- `ProLayoutWrapper`
- `PopupForm`
- `ProTable`-based management grids
- modal create/edit/delete forms
- tabbed section shells
- rule execution progress expander
- rule schema modal
- simulator configuration strip
- simulator config edit modal
- agent log console
- simulator chart panels

## Component Catalog

### `ProLayoutWrapper`

- Purpose: main application shell
- Structure:
  - ProLayout root
  - left navigation items for Pools / Rules / Simulators
  - content outlet
- States:
  - collapsed / expanded sidebar
- Interaction:
  - route navigation handled through custom clickable menu item render
  - menu items are rendered as anchors with `preventDefault()` and imperative navigation
- Theming:
  - `realDark` nav
  - no logo
  - title `Fintools`

### `PopupForm`

- Purpose: reusable modal wrapper for forms
- Structure:
  - Antd `Modal`
  - title
  - no footer
  - arbitrary children body
- States:
  - open / closed
  - destroyed on close
- Usage:
  - pool create
  - pool edit
  - simulator create

### Management Grid

- Purpose: default list-management primitive across the app
- Structure:
  - outer `Spin`
  - `ProTable`
  - optional toolbar CTA
  - row actions inline
- Behavior:
  - pagination always on
  - search often off; when on, usually targeted at one field
  - toolbars usually expose one primary `Create` CTA
  - actions render inline as text links or small buttons

### Rule Schema Modal

- Parent: `src/pages/Rules/index.tsx`
- Purpose: explain remote agent input/output contract in plain operator language
- Structure:
  - link-styled button trigger
  - Antd modal
  - short paragraph stack with bold labels
- Content:
  - stock code input example
  - boolean indicating output
  - buy-signal interpretation

### Rule Progress Expander

- Parent: expanded row in `RuleList`
- Structure:
  - summary row with progress and last run time
  - `Collapse`
  - scrollable list of stock execution rows
  - tags for state
  - inline `Run` action
  - placeholder popup window bootstrap before async execution call
- States:
  - loading
  - never run
  - not run today
  - indicating
  - not indicating
  - popup blocked
  - runtime token missing

### Simulator Config Strip

- Purpose: high-visibility summary of current sell conditions
- Structure:
  - dark horizontal bar
  - label plus three emphasized metrics
- Visual style:
  - white and gray text on dark background
  - green/red/blue emphasis for different config categories

### Simulator Config Modal

- Parent: `src/pages/Simulators/index.tsx`
- Purpose: edit global sell-condition parameters
- Structure:
  - modal title
  - three vertically stacked labeled `InputNumber` fields
  - helper text below each field
- Constraints:
  - profit threshold `0..100`
  - stop loss `0..100`
  - max holding days `1..30`

### Agent Log Console

- Purpose: focused run-monitoring screen
- Structure:
  - standalone dark page
  - header title
  - progress tags
  - close button
  - monospaced scrollable log pane
- Behavior:
  - auto-appends logs from SSE
  - auto-scrolls downward
  - shows waiting state with spinner
  - closes via `window.close()`
  - rule mode shows progress tags
  - single-stock mode omits aggregate progress tags

### Chart Panel

- Purpose: visualize simulator performance
- Structure:
  - heading
  - fixed-height chart area
  - repeated for comparison chart
- Rendering:
  - ECharts initialized imperatively after tab activation

## Shared Visual Traits

- Plain operator-first UI
- Minimal decorative treatment
- Heavy use of tables, tabs, modals, selects, and inline actions
- Desktop density prioritized over responsive reflow
- UI reuse is mostly compositional rather than token-system-driven
