---
version: v3
name: slb-whimsical
description: Whimsical-inspired design system for 申论帮 (SLB) — a civil service exam preparation platform. Light, clean, friendly aesthetic with purple accent, Manrope typography, rounded corners, and warm purple-tinted neutrals. Optimized for focused reading and writing with generous whitespace.
---

## Overview

申论帮 adopts Whimsical's friendly, approachable design language — a light canvas where content breathes, purple accent provides clear hierarchy, and rounded shapes create warmth. The design prioritizes readability for long study sessions while maintaining a modern, professional feel that doesn't intimidate.

**Key Characteristics:**
- Light-mode canvas: `#FFFFFF` primary, `#F7F7F8` secondary surfaces
- Deep purple-black text: `#220A33` — warmer than pure black
- Vibrant purple accent: `#9E39E5` for CTAs, links, active states
- Manrope font family — rounded, friendly, excellent Chinese fallback
- Generous whitespace — 80px+ section gaps
- Rounded corners: 8px cards, 12px panels, 9999px pills
- Purple-tinted subtle backgrounds: `rgba(34, 10, 51, 0.04)`
- GSAP ScrollTrigger animations with prefers-reduced-motion support

## Color Palette

### Background Surfaces
| Token | Hex | Use |
|-------|-----|-----|
| `--bg-primary` | `#FFFFFF` | Page background, cards |
| `--bg-secondary` | `#F7F7F8` | Sections, sidebars |
| `--bg-subtle` | `rgba(34, 10, 51, 0.04)` | Hover states, subtle fills |
| `--bg-muted` | `rgba(34, 10, 51, 0.08)` | Active states, selected items |

### Text
| Token | Hex | Use |
|-------|-----|-----|
| `--text-primary` | `#220A33` | Headings, primary content |
| `--text-secondary` | `#685C70` | Body text, descriptions |
| `--text-tertiary` | `#8F8497` | Placeholders, metadata |
| `--text-inverse` | `#FFFFFF` | Text on dark/purple surfaces |

### Brand & Accent
| Token | Hex | Use |
|-------|-----|-----|
| `--accent` | `#9E39E5` | CTA buttons, links, active states |
| `--accent-hover` | `#8230C4` | Hover on accent elements |
| `--accent-soft` | `rgba(158, 57, 229, 0.08)` | Accent background tints |
| `--accent-medium` | `rgba(158, 57, 229, 0.15)` | Accent badges, tags |

### Status
| Token | Hex | Use |
|-------|-----|-----|
| `--success` | `#22C55E` | Correct answers, completion |
| `--success-soft` | `rgba(34, 197, 94, 0.1)` | Success background |
| `--warning` | `#F59E0B` | Needs attention, medium scores |
| `--warning-soft` | `rgba(245, 158, 11, 0.1)` | Warning background |
| `--error` | `#EF4444` | Errors, low scores |
| `--error-soft` | `rgba(239, 68, 68, 0.1)` | Error background |

### Borders
| Token | Value | Use |
|-------|-------|-----|
| `--border` | `rgba(34, 10, 51, 0.08)` | Standard borders |
| `--border-subtle` | `rgba(34, 10, 51, 0.04)` | Subtle dividers |
| `--border-accent` | `rgba(158, 57, 229, 0.2)` | Focus states |

## Typography

### Font Stack
```css
font-family: 'Manrope', 'Noto Sans SC', system-ui, -apple-system, sans-serif;
```

### Hierarchy
| Token | Size | Weight | Line Height | Letter Spacing | Use |
|-------|------|--------|-------------|----------------|-----|
| `display-xl` | 56px | 700 | 1.1 | -0.02em | Hero headline |
| `display-lg` | 40px | 700 | 1.15 | -0.015em | Section opener |
| `display-md` | 32px | 700 | 1.2 | -0.01em | Page title |
| `heading-1` | 24px | 700 | 1.3 | -0.01em | Section heading |
| `heading-2` | 20px | 600 | 1.4 | normal | Card title |
| `heading-3` | 18px | 600 | 1.4 | normal | Sub-section |
| `body-lg` | 18px | 400 | 1.7 | normal | Lead text, 申论材料 |
| `body` | 16px | 400 | 1.6 | normal | Standard reading |
| `body-sm` | 14px | 400 | 1.6 | normal | Secondary body |
| `caption` | 13px | 500 | 1.5 | normal | Labels, metadata |
| `label` | 12px | 600 | 1.4 | 0.02em | Buttons, tags |
| `mono` | 14px | 400 | 1.5 | normal | Code, scores |

### Principles
- **700 for headlines** — bold, confident, friendly
- **600 for emphasis** — card titles, labels, navigation
- **400 for body** — comfortable reading
- **500 for UI elements** — buttons, tags, captions
- **No negative letter-spacing below 24px** — Manrope reads well at default tracking

## Spacing

Base unit: 8px

| Token | Value | Use |
|-------|-------|-----|
| `--space-1` | 4px | Tight gaps |
| `--space-2` | 8px | Default gap |
| `--space-3` | 12px | Card padding |
| `--space-4` | 16px | Section padding |
| `--space-5` | 24px | Card internal |
| `--space-6` | 32px | Section gap |
| `--space-8` | 48px | Large section gap |
| `--space-12` | 64px | Hero padding |
| `--space-16` | 80px | Major section break |

## Border Radius

| Token | Value | Use |
|-------|-------|-----|
| `--radius-sm` | 4px | Small elements, inputs |
| `--radius-md` | 8px | Cards, buttons |
| `--radius-lg` | 12px | Panels, modals |
| `--radius-xl` | 16px | Large panels |
| `--radius-full` | 9999px | Pills, tags |

## Components

### Buttons

**Primary (CTA)**
```css
background: #9E39E5;
color: #FFFFFF;
padding: 10px 20px;
border-radius: 8px;
font-size: 14px;
font-weight: 600;
```

**Secondary**
```css
background: rgba(34, 10, 51, 0.05);
color: #220A33;
padding: 10px 20px;
border-radius: 8px;
font-size: 14px;
font-weight: 600;
```

**Ghost**
```css
background: transparent;
color: #9E39E5;
padding: 10px 20px;
border-radius: 8px;
font-size: 14px;
font-weight: 600;
```

### Cards

**Default Card**
```css
background: #FFFFFF;
border: 1px solid rgba(34, 10, 51, 0.08);
border-radius: 8px;
padding: 24px;
```

**Elevated Card**
```css
background: #FFFFFF;
border: 1px solid rgba(34, 10, 51, 0.08);
border-radius: 12px;
padding: 32px;
box-shadow: 0 4px 24px rgba(34, 10, 51, 0.06);
```

**Score Card**
```css
background: rgba(158, 57, 229, 0.04);
border: 1px solid rgba(158, 57, 229, 0.12);
border-radius: 12px;
padding: 32px;
text-align: center;
```

### Inputs

**Text Input**
```css
background: #FFFFFF;
color: #220A33;
border: 1px solid rgba(34, 10, 51, 0.12);
padding: 10px 14px;
border-radius: 8px;
font-size: 16px;
```

**Text Input (Focus)**
```css
border-color: #9E39E5;
box-shadow: 0 0 0 3px rgba(158, 57, 229, 0.1);
```

**Textarea (答题区)**
```css
background: #FFFFFF;
color: #220A33;
border: 1px solid rgba(34, 10, 51, 0.12);
padding: 16px;
border-radius: 12px;
font-size: 16px;
line-height: 1.8;
min-height: 280px;
```

### Navigation

**Navbar**
```css
background: rgba(255, 255, 255, 0.88);
backdrop-filter: blur(12px);
border-bottom: 1px solid rgba(34, 10, 51, 0.06);
```

### Badges & Pills

**Type Badge (题型)**
```css
background: rgba(158, 57, 229, 0.08);
color: #9E39E5;
padding: 4px 12px;
border-radius: 9999px;
font-size: 12px;
font-weight: 600;
```

**Score Badge**
```css
/* High */
background: rgba(34, 197, 94, 0.1);
color: #16A34A;

/* Medium */
background: rgba(245, 158, 11, 0.1);
color: #D97706;

/* Low */
background: rgba(239, 68, 68, 0.1);
color: #DC2626;
```

### Progress Bar

```css
background: rgba(34, 10, 51, 0.06);
border-radius: 9999px;
height: 8px;
```

**Fill**
```css
background: linear-gradient(90deg, #9E39E5, #C084FC);
border-radius: 9999px;
```

### Modal

```css
background: #FFFFFF;
border: 1px solid rgba(34, 10, 51, 0.08);
border-radius: 16px;
box-shadow: 0 24px 48px rgba(34, 10, 51, 0.12);
```

### Toast

```css
background: #220A33;
color: #FFFFFF;
border-radius: 8px;
font-size: 14px;
font-weight: 500;
```

## Depth System

| Level | Treatment | Use |
|-------|-----------|-----|
| 0 | Flat, `#FFFFFF` | Page background |
| 1 | `#FFFFFF` + border | Cards |
| 2 | `#FFFFFF` + border + shadow | Elevated cards |
| 3 | `#F7F7F8` | Secondary sections |
| 4 | Multi-layer shadow | Modals, dropdowns |

## GSAP Animation Specs

### Scroll Reveal
```javascript
gsap.set('.reveal', { y: 24, autoAlpha: 0 });
// onEnter: gsap.to(el, { y: 0, autoAlpha: 1, duration: 0.5, ease: 'power2.out' });
```

### Card Hover (Desktop)
```javascript
gsap.to(card, { y: -2, boxShadow: '0 8px 24px rgba(34,10,51,0.08)', duration: 0.25 });
```

### Score Counter
```javascript
gsap.to(obj, { val: target, duration: 1.5, ease: 'power2.out', onUpdate: ... });
```

### Button Click
```javascript
gsap.fromTo(btn, { scale: 0.97 }, { scale: 1, duration: 0.2, ease: 'back.out(2)' });
```

## Do's and Don'ts

### Do
- Use `#220A33` for primary text — warmer than pure black, easier on eyes
- Keep generous whitespace — 80px+ between major sections
- Use purple accent (`#9E39E5`) sparingly — one CTA per section
- Use rounded corners (8px minimum) for friendly feel
- Use Manrope weights: 700 (headlines), 600 (emphasis), 400 (body), 500 (UI)
- Use purple-tinted neutrals (`rgba(34, 10, 51, ...)`) instead of pure gray

### Don't
- Don't use pure black (`#000`) for text — use `#220A33`
- Don't use sharp corners (0px) — minimum 4px radius
- Don't use heavy shadows — keep them subtle and purple-tinted
- Don't overcrowd — whitespace is part of the design
- Don't use more than 2 accent colors per section

## Responsive

| Breakpoint | Width | Changes |
|------------|-------|---------|
| Mobile | <768px | Single column, hamburger nav, display 56→32px |
| Tablet | 768–1024px | 2-column grids |
| Desktop | >1024px | Full layout, 3-column grids |

## Font CDN

```html
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
```
