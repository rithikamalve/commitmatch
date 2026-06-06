---
name: CommitMatch Operations
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1b1b1c'
  on-surface-variant: '#5b403d'
  inverse-surface: '#303030'
  inverse-on-surface: '#f3f0ef'
  outline: '#8f6f6c'
  outline-variant: '#e4beba'
  surface-tint: '#ba1a20'
  primary: '#af101a'
  on-primary: '#ffffff'
  primary-container: '#d32f2f'
  on-primary-container: '#fff2f0'
  inverse-primary: '#ffb3ac'
  secondary: '#005faf'
  on-secondary: '#ffffff'
  secondary-container: '#54a0fe'
  on-secondary-container: '#003567'
  tertiary: '#715300'
  on-tertiary: '#ffffff'
  tertiary-container: '#8f6a00'
  on-tertiary-container: '#fff3e3'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad6'
  primary-fixed-dim: '#ffb3ac'
  on-primary-fixed: '#410003'
  on-primary-fixed-variant: '#930010'
  secondary-fixed: '#d4e3ff'
  secondary-fixed-dim: '#a5c8ff'
  on-secondary-fixed: '#001c3a'
  on-secondary-fixed-variant: '#004786'
  tertiary-fixed: '#ffdfa0'
  tertiary-fixed-dim: '#f8bd2a'
  on-tertiary-fixed: '#261a00'
  on-tertiary-fixed-variant: '#5c4300'
  background: '#fcf9f8'
  on-background: '#1b1b1c'
  surface-variant: '#e5e2e1'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 14px
  code:
    fontFamily: jetbrainsMono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  gutter: 16px
  margin-desktop: 32px
  container-max: 1440px
---

## Brand & Style
The design system is engineered for **CommitMatch**, a mission-critical operations platform. The brand personality shifts away from clinical softness toward **authoritative urgency** and **operational excellence**. It targets professional administrators and healthcare coordinators who require high-density information environments.

The visual style is **Corporate / Modern** with a lean toward **High-Contrast Professionalism**. It prioritizes clarity, data density, and trust. The aesthetic follows a "cloud-native enterprise" approach: clean lines, systematic hierarchy, and purposeful use of color to signal action and status. The emotional response should be one of reliability, precision, and the gravity of the mission.

## Colors
The palette is anchored by **Blood Warriors Red (#D32F2F)**, used strategically for primary actions, branding, and urgent status indicators. This is a high-chroma red balanced by a sophisticated grayscale ramp to prevent visual fatigue in high-density interfaces.

- **Primary:** #D32F2F (Urgency, Action, Brand Identity)
- **Secondary:** #1976D2 (Technical reliability, Information, Secondary actions)
- **Neutral:** A range of cool grays (Surface #F8F9FA, Border #E0E0E0, Text #1E1E1E)
- **Semantic:** Success is a deep emerald (#2E7D32); Warning is an amber (#F57C00); Error utilizes the Primary Red.

The default mode is **Light**, utilizing high-contrast text ratios to ensure maximum readability in daylight office environments.

## Typography
**Inter** is the sole typeface for this design system to ensure a systematic, utilitarian aesthetic. It is chosen for its exceptional legibility in data-heavy tables and small-scale labels.

- **Headlines:** Use Bold (700) or SemiBold (600) weights with slight negative letter spacing to maintain a compact, "newsroom" feel.
- **Body:** Regular (400) weight is standard. For data dense grids, `body-sm` (14px) is the primary workhorse.
- **Labels:** Use `label-md` for headers within sidebars or data categories to create clear sections.
- **Numbers:** Tabular lining should be enabled to ensure numerical data aligns perfectly in tables.

## Layout & Spacing
This design system utilizes a **fixed-fluid hybrid grid** optimized for 1440px desktop displays. 

- **The 4px Grid:** All spacing must be a multiple of 4px. Use `md` (16px) for standard component spacing and `lg` (24px) for layout sections.
- **Desktop (12-column):** 16px gutters, 32px side margins. Max container width of 1440px.
- **Tablet (8-column):** 16px gutters, 24px side margins.
- **Mobile (4-column):** 12px gutters, 16px side margins.

Content density should be high. Information should be grouped into cards or logical sections to minimize excessive scrolling in operational dashboards.

## Elevation & Depth
Depth is communicated through **Tonal Layers** and **Crisp Outlines** rather than heavy shadows, maintaining a clean SaaS look.

- **Level 0 (Background):** #F8F9FA.
- **Level 1 (Cards/Containers):** Pure white (#FFFFFF) with a 1px border (#E0E0E0).
- **Level 2 (Dropdowns/Modals):** Pure white with a subtle 1px border and a tight, low-opacity shadow (0px 4px 12px rgba(0,0,0,0.08)).
- **Interactions:** Hover states on interactive elements should use a slight darken or a subtle background shift (e.g., #F0F0F0) rather than an elevation lift.

## Shapes
The design system employs a **Soft** shape language. This provides a balance between the precision of sharp corners and the approachability of modern software.

- **Standard Elements (Buttons, Inputs):** 0.25rem (4px) corner radius.
- **Large Containers (Cards, Modals):** 0.5rem (8px) corner radius.
- **Special Elements:** Status badges and chips may use a pill-shape (full round) to distinguish them from interactive buttons.

## Components
- **Buttons:** Primary buttons use the Blood Warriors Red with white text. Secondary buttons use a transparent background with a 1px neutral-400 border. Transitions should be instant (150ms) to feel responsive.
- **Input Fields:** Use 1px borders (#E0E0E0) that turn Primary Red or Secondary Blue on focus. Labels must always be visible (no floating labels that disappear).
- **Data Tables:** The core of the platform. Use `body-sm` (14px) typography. Row height should be 48px for standard density. Use alternating row stripes or subtle borders.
- **Status Chips:** High-contrast background with dark text for accessibility. E.g., "Urgent" uses a light red background with the Primary Red text.
- **Sidebar:** A dark-themed sidebar (Neutral #1E1E1E) is recommended to frame the content and provide a high-trust, enterprise navigation experience.
- **Action Banners:** Full-width banners at the top of pages for system-wide alerts, using the Primary Red for critical updates.