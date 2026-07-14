---
name: Trust & Integrity
colors:
  surface: '#f9f9ff'
  surface-dim: '#d9d9df'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f9'
  surface-container: '#ededf3'
  surface-container-high: '#e8e8ed'
  surface-container-highest: '#e2e2e8'
  on-surface: '#1a1c20'
  on-surface-variant: '#424750'
  inverse-surface: '#2e3035'
  inverse-on-surface: '#f0f0f6'
  outline: '#737781'
  outline-variant: '#c2c6d1'
  surface-tint: '#2f5f9c'
  primary: '#00386c'
  on-primary: '#ffffff'
  primary-container: '#1a4f8b'
  on-primary-container: '#9bc2ff'
  inverse-primary: '#a6c8ff'
  secondary: '#505f76'
  on-secondary: '#ffffff'
  secondary-container: '#d0e1fb'
  on-secondary-container: '#54647a'
  tertiary: '#582c00'
  on-tertiary: '#ffffff'
  tertiary-container: '#793f00'
  on-tertiary-container: '#ffae6b'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d5e3ff'
  primary-fixed-dim: '#a6c8ff'
  on-primary-fixed: '#001c3b'
  on-primary-fixed-variant: '#0c4783'
  secondary-fixed: '#d3e4fe'
  secondary-fixed-dim: '#b7c8e1'
  on-secondary-fixed: '#0b1c30'
  on-secondary-fixed-variant: '#38485d'
  tertiary-fixed: '#ffdcc3'
  tertiary-fixed-dim: '#ffb77e'
  on-tertiary-fixed: '#2f1500'
  on-tertiary-fixed-variant: '#6e3900'
  background: '#f9f9ff'
  on-background: '#1a1c20'
  surface-variant: '#e2e2e8'
typography:
  display-lg:
    fontFamily: Noto Sans JP
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Noto Sans JP
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.3'
  headline-sm:
    fontFamily: Noto Sans JP
    fontSize: 18px
    fontWeight: '700'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Noto Sans JP
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Noto Sans JP
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
  data-tabular:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.5'
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.05em
  caption:
    fontFamily: Noto Sans JP
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 24px
  gutter: 16px
  sidebar-width: 260px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style
This design system is engineered for a high-stakes B2B banking environment, focusing on the rigorous demands of loan management. The brand personality is rooted in **Reliability, Precision, and Institutional Trust**. The UI must evoke a sense of calm authority, ensuring that loan officers and underwriters can process complex financial data without cognitive fatigue.

The design style follows a **Modern Corporate / Minimalist** approach. It avoids decorative flourishes in favor of structural clarity. By utilizing a "White & Light Gray" foundation, the system emphasizes content hierarchy through hairline borders and purposeful whitespace rather than elevation or shadows. The aesthetic is "Paper-digital"—clean, flat, and highly organized, mimicking the precision of professional financial documentation.

## Colors
The palette is dominated by **Trust Blue (#1A4F8B)**, a deep, stable primary hue that signals security and institutional backing.

- **Primary:** Used for primary actions, active navigation states, and key brand moments.
- **Surfaces:** A binary system of pure White (#FFFFFF) for primary content cards and Light Gray (#F8F9FA) for page backgrounds and sidebar areas to create subtle contrast.
- **Semantic Palette:** Standardized for immediate risk assessment:
    - **Amber:** Pending reviews or cautionary loan ratios.
    - **Red:** Overdue payments, rejected applications, or critical system errors.
    - **Green:** Approved status, active loans, and successful submissions.
    - **Gray:** Inactive states, drafted items, or secondary metadata.

## Typography
The typography strategy prioritizes legibility for bilingual and data-heavy contexts.

- **Japanese Text:** Noto Sans JP is the primary typeface, providing a modern, clean, and highly readable sans-serif feel across all UI labels and body text.
- **Numerical Data:** Inter is used exclusively for financial figures, interest rates, and dates. The `tabular-nums` (tnum) feature must be enabled to ensure that numbers align vertically in data tables, facilitating easy comparison of loan amounts.
- **Scale:** Headings use a bold weight to establish clear section hierarchy. Body text is kept at a comfortable 14px or 16px to accommodate the density of loan information.

## Layout & Spacing
The layout utilizes a **Fixed-Fluid Hybrid** model optimized for desktop workflows.

- **Navigation:** A persistent **Left Sidebar (260px)** houses the primary navigation. It uses the Subtle Background (#F8F9FA) to separate system-level controls from the work area.
- **Grid:** Content is housed in a flexible main area with a 24px outer margin. Internal spacing follows a strict 4px/8px baseline grid to maintain alignment.
- **Density:** Given the nature of loan processing, a "Compact" density is preferred. Information is grouped in cards with 16px gutters between them. 
- **Breakpoints:**
    - Desktop (Default): 1280px+
    - Tablet: 1024px (Sidebar collapses to icons)
    - Mobile: Not prioritized, but follows a single-column reflow for urgent approvals.

## Elevation & Depth
This design system avoids shadows to maintain a professional, flat aesthetic. Depth is communicated via **Tonal Layering** and **Hairline Outlines**:

- **Tier 0 (Base):** #F8F9FA (Background of the application).
- **Tier 1 (Surface):** #FFFFFF (Cards, Whiteboards, Data Tables). These are defined by a 1px solid border (#E2E8F0) rather than a shadow.
- **Tier 2 (Interactive):** Elements like dropdowns or modals use a slightly darker border (#CBD5E1) or a very subtle 2px blur shadow only when necessary to separate overlapping layers.
- **Active State:** Selected items or focused inputs use the Primary Color (#1A4F8B) for the border to indicate focus.

## Shapes
In alignment with the banking industry's need for stability and precision, the shape language is conservative.

- **Corner Radius:** A universal **4px (Soft)** radius is applied to all buttons, input fields, cards, and badges. This provides a modern touch without appearing overly casual or "bubbly."
- **Tables:** Rows remain sharp-cornered to maximize data density and maintain the grid structure of financial reports.

## Components
Consistent component styling ensures the interface remains predictable.

- **Status Badges:** Use a "Tint & Text" approach. The background is a 10% opacity version of the semantic color, while the text is the full-saturation version of that same color. No borders on badges.
- **Buttons:** 
    - *Primary:* Solid #1A4F8B with white text. 4px radius.
    - *Secondary:* White background with #E2E8F0 1px border and dark text.
- **Input Fields:** 1px border (#E2E8F0). Focus state uses a 1px #1A4F8B border. Labels are Noto Sans JP (12px Bold) positioned above the field.
- **Data Tables:** The core of the system. Use 1px horizontal dividers. Header rows should have a subtle #F8F9FA background. Use Inter with tabular-nums for all currency columns.
- **Sidebar Nav:** High-contrast active state using a left-accent 4px border in Trust Blue and a light blue tint background for the active row.
- **Loan Progress Indicator:** A horizontal stepper using thin lines and 4px rounded nodes to track the application lifecycle from "Submission" to "Disbursement."