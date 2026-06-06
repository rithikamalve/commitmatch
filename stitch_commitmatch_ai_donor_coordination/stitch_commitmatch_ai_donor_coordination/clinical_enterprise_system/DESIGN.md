---
name: Clinical Enterprise System
colors:
  surface: '#f9f9ff'
  surface-dim: '#cfdaf1'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f0f3ff'
  surface-container: '#e7eeff'
  surface-container-high: '#dee8ff'
  surface-container-highest: '#d8e3fa'
  on-surface: '#111c2c'
  on-surface-variant: '#3f4949'
  inverse-surface: '#263142'
  inverse-on-surface: '#ebf1ff'
  outline: '#6f7979'
  outline-variant: '#bec9c8'
  surface-tint: '#13696a'
  primary: '#006162'
  on-primary: '#ffffff'
  primary-container: '#2c7a7b'
  on-primary-container: '#c1ffff'
  inverse-primary: '#89d3d4'
  secondary: '#0061a5'
  on-secondary: '#ffffff'
  secondary-container: '#66affe'
  on-secondary-container: '#004172'
  tertiary: '#4c595e'
  on-tertiary: '#ffffff'
  tertiary-container: '#657177'
  on-tertiary-container: '#e9f6fd'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#a5eff0'
  primary-fixed-dim: '#89d3d4'
  on-primary-fixed: '#002020'
  on-primary-fixed-variant: '#004f50'
  secondary-fixed: '#d2e4ff'
  secondary-fixed-dim: '#9fcaff'
  on-secondary-fixed: '#001d37'
  on-secondary-fixed-variant: '#00497e'
  tertiary-fixed: '#d8e4eb'
  tertiary-fixed-dim: '#bcc8cf'
  on-tertiary-fixed: '#111d22'
  on-tertiary-fixed-variant: '#3c494e'
  background: '#f9f9ff'
  on-background: '#111c2c'
  surface-variant: '#d8e3fa'
typography:
  display:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-bold:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 24px
---

## Brand & Style
The design system is engineered for life-critical healthcare logistics, prioritizing precision, trust, and rapid information processing. It adopts a **Modern Corporate** aesthetic—refined, functional, and cloud-native—optimized for high-density SaaS environments where data clarity is paramount.

The visual narrative balances the sterility of a clinical environment with the accessibility of modern web software. It utilizes a disciplined hierarchy, heavy use of whitespace for grouping rather than separation, and a "function over flourish" philosophy that mirrors the reliability required by blood donation and matching workflows.

## Colors
This design system utilizes a palette rooted in deep teals and soft blues to establish an atmosphere of professional calm. 

- **Primary (Deep Teal):** Used for navigation, primary buttons, and brand reinforcement.
- **Secondary (Blue):** Employed for interactive elements, links, and selection states.
- **Surface (Soft Blue & White):** Backgrounds use a tiered approach with #EBF8FF for container backgrounds and crisp white for cards to create subtle depth.
- **Semantic Logic:** Green is reserved strictly for "Available" or "Matched" states. Red is utilized for "Critical Shortage" or "Urgent Action Required." These colors should maintain high contrast ratios against white backgrounds for accessibility.

## Typography
The typography system relies exclusively on **Inter** to ensure maximum legibility at small sizes and high-density views. 

The scale is tailored for dashboard environments:
- **Data Densities:** Use `body-sm` for table cell content and metadata.
- **Section Headers:** Use `headline-md` for card titles.
- **Labels:** Use `label-bold` for status indicators and table column headers to provide clear distinction from the data itself.
- **Numerical Data:** For blood counts or critical metrics, use a medium or semi-bold weight to ensure they are the first thing a user notices.

## Layout & Spacing
The layout follows a **Fluid Grid** model with a 12-column system for desktop views. It is designed for maximum efficiency, utilizing an 8px base grid with 4px sub-steps for tight component alignment.

- **Desktop:** 24px outer margins, 16px gutters between cards.
- **Sidebars:** Fixed-width navigation (240px) to maximize the horizontal space for data tables.
- **Density:** Components use `sm` (12px) padding as the default for internal card layouts to maintain a high-density, "at-a-glance" information architecture.

## Elevation & Depth
In this design system, depth is primarily conveyed through **Tonal Layers** and **Low-Contrast Outlines** rather than heavy shadows, maintaining a clean, medical-grade appearance.

- **Level 0 (Background):** #EBF8FF (Soft Blue) for the primary application canvas.
- **Level 1 (Cards/Tables):** White (#FFFFFF) with a 1px solid border (#E2E8F0).
- **Level 2 (Popovers/Dropdowns):** White with a soft ambient shadow (0px 4px 12px rgba(0,0,0,0.05)) and a border.
- **Special Case (AI Insights):** Uses a very soft secondary blue tint (#F0F7FF) with a slightly more pronounced blue-tinted shadow to differentiate machine-generated suggestions from standard patient records.

## Shapes
The shape language is **Soft (0.25rem)**, providing a subtle hint of approachability while maintaining a professional, structured edge.

- **Buttons & Inputs:** 4px radius.
- **Cards:** 8px (rounded-lg) to separate distinct data modules.
- **Status Badges:** 4px radius or fully pill-shaped depending on the prominence required (e.g., status badges are often pills for quick identification).

## Components
Consistent implementation of these core components ensures the system remains scalable:

- **Data Tables:** Use a "Sticky Header" for vertical scrolling. Row height should be compact (40px-48px). Use 1px horizontal borders; avoid vertical borders to reduce visual noise.
- **Status Badges:**
  - *Recommended:* Subtle blue background with dark blue text.
  - *High Reliability:* Soft green background with dark green text.
  - *Urgent:* Solid red background with white text for maximum attention.
- **High-Density Cards:** Use a top-aligned label/value pair system for displaying patient or donor vitals.
- **AI-Insight Callouts:** Encapsulate in a border with a specific blue-to-white gradient or a subtle "Sparkle" icon. These should appear as floating overlays or inline alerts with slightly increased elevation.
- **Buttons:**
  - *Primary:* Deep teal with white text.
  - *Secondary:* Ghost style (teal border/text).
  - *Tertiary:* Clear (text-only) for low-priority dashboard actions.
- **Inputs:** Crisp white background with a 1px #CBD5E0 border. On focus, use a 2px #3182CE outer ring.