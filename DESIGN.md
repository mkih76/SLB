---
version: v2
name: slb-linear-dark
description: Linear-inspired dark design system for 申论帮 (SLB) — a civil service exam preparation platform. Near-black canvas with purple-violet accent, Inter Variable typography with Chinese fallback, semi-transparent glass surfaces, and GSAP-driven micro-interactions. Optimized for long reading sessions and focused writing.
---

## Overview

申论帮 is a dark-mode-first education platform. The design inherits Linear's precision-engineered aesthetic — near-black backgrounds where content emerges from darkness like starlight — adapted for Chinese-language exam preparation. The near-black canvas reduces eye strain during extended study sessions; the single purple-violet accent provides clear hierarchy without visual fatigue.

**Key Characteristics:**
- Dark-mode-native: `#08090a` page background, `#0f1011` panels, `#191a1b` elevated surfaces
- Inter Variable + Noto Sans SC for Chinese text, weight 510 as signature emphasis
- Brand purple-violet: `#5e6ad2` (bg) / `#7170ff` (accent) / `#828fff` (hover)
- Semi-transparent glass surfaces: `rgba(255,255,255,0.02)` to `rgba(255,255,255,0.05)`
- Whisper-thin borders: `rgba(255,255,255,0.05)` to `rgba(255,255,255,0.08)`
- GSAP ScrollTrigger animations with prefers-reduced-motion support
- Optimized for long-form reading (申论材料) and writing (答题区)

## Color Palette

### Background Surfaces
| Token | Hex | Use |
|-------|-----|-----|
| `--bg-deep` | `#08090a` | Page background, hero sections |
| `--bg-panel` | `#0f1011` | Sidebar, navigation bar |
| `--bg-surface` | `#191a1b` | Cards, elevated containers |
| `--bg-hover` | `#28282c` | Hover states, active items |
| `--bg-glass` | `rgba(255,255,255,0.02)` | Glass card default |
| `--bg-glass-hover` | `rgba(255,255,255,0.05)` | Glass card hover |

### Text
| Token | Hex | Use |
|-------|-----|-----|
| `--text-primary` | `#f7f8f8` | Headings, primary content |
| `--text-secondary` | `#d0d6e0` | Body text, descriptions |
| `--text-tertiary` | `#8a8f98` | Placeholders, metadata |
| `--text-muted` | `#62666d` | Timestamps, disabled states |

### Brand & Accent
| Token | Hex | Use |
|-------|-----|-----|
| `--accent` | `#5e6ad2` | CTA buttons, brand marks |
| `--accent-bright` | `#7170ff` | Links, active states, selected items |
| `--accent-hover` | `#828fff` | Hover on accent elements |
| `--accent-soft` | `rgba(94,106,210,0.15)` | Accent background tints |

### Status
| Token | Hex | Use |
|-------|-----|-----|
| `--success` | `#10b981` | Correct answers, completion |
| `--warning` | `#f59e0b` | Needs attention, medium scores |
| `--error` | `#ef4444` | Errors, low scores |
| `--info` | `#3b82f6` | Information, tips |

### Borders
| Token | Value | Use |
|-------|-------|-----|
| `--border-subtle` | `rgba(255,255,255,0.05)` | Default borders |
| `--border-standard` | `rgba(255,255,255,0.08)` | Cards, inputs |
| `--border-accent` | `rgba(113,112,255,0.3)` | Active inputs, focus states |

## Typography

### Font Stack
```css
font-family: 'Inter', 'Noto Sans SC', system-ui, -apple-system, sans-serif;
font-feature-settings: "cv01", "ss03";
```

### Hierarchy
| Token | Size | Weight | Line Height | Letter Spacing | Use |
|-------|------|--------|-------------|----------------|-----|
| `display-xl` | 72px | 510 | 1.00 | -1.584px | Hero headline |
| `display-lg` | 48px | 510 | 1.00 | -1.056px | Section opener |
| `display-md` | 32px | 400 | 1.13 | -0.704px | Page title |
| `heading-1` | 24px | 400 | 1.33 | -0.288px | Section heading |
| `heading-2` | 20px | 590 | 1.33 | -0.24px | Card title |
| `heading-3` | 18px | 590 | 1.33 | -0.165px | Sub-section |
| `body-lg` | 18px | 400 | 1.60 | -0.165px | Lead text, 申论材料 |
| `body` | 16px | 400 | 1.50 | normal | Standard reading |
| `body-md` | 16px | 510 | 1.50 | normal | Navigation, labels |
| `body-sm` | 15px | 400 | 1.60 | -0.165px | Secondary body |
| `caption` | 13px | 400 | 1.50 | -0.13px | Metadata, timestamps |
| `label` | 12px | 590 | 1.40 | normal | Buttons, tags |
| `mono` | 14px | 400 | 1.50 | normal | Code, scores |

### Principles
- **510 is the signature weight** — between regular and medium, subtle emphasis without heaviness
- **Negative tracking at display sizes** — -1.584px at 72px, scaling proportionally
- **Three-tier weight**: 400 (reading), 510 (UI emphasis), 590 (strong emphasis)
- **No weight 700** — maximum is 590

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
| `--space-16` | 96px | Major section break |

## Border Radius

| Token | Value | Use |
|-------|-------|-----|
| `--radius-sm` | 4px | Small elements |
| `--radius-md` | 6px | Buttons, inputs |
| `--radius-lg` | 8px | Cards |
| `--radius-xl` | 12px | Panels, modals |
| `--radius-2xl` | 22px | Large panels |
| `--radius-full` | 9999px | Pills, tags |

## Components

### Buttons

**Primary (CTA)**
```css
background: #5e6ad2;
color: #f7f8f8;
padding: 8px 16px;
border-radius: 6px;
font-size: 16px;
font-weight: 510;
```

**Ghost (Secondary)**
```css
background: rgba(255,255,255,0.02);
color: #e2e4e7;
border: 1px solid rgba(255,255,255,0.08);
padding: 8px 16px;
border-radius: 6px;
```

**Accent (Links)**
```css
background: transparent;
color: #7170ff;
padding: 0;
border: none;
```

### Cards

**Glass Card**
```css
background: rgba(255,255,255,0.02);
border: 1px solid rgba(255,255,255,0.08);
border-radius: 8px;
padding: 24px;
```

**Elevated Card**
```css
background: #191a1b;
border: 1px solid rgba(255,255,255,0.08);
border-radius: 8px;
padding: 24px;
box-shadow: rgba(0,0,0,0.2) 0px 0px 0px 1px;
```

**Score Card (考试结果)**
```css
background: rgba(94,106,210,0.1);
border: 1px solid rgba(113,112,255,0.2);
border-radius: 12px;
padding: 32px;
text-align: center;
```

### Inputs

**Text Input**
```css
background: rgba(255,255,255,0.02);
color: #d0d6e0;
border: 1px solid rgba(255,255,255,0.08);
padding: 12px 14px;
border-radius: 6px;
font-size: 16px;
```

**Text Input (Focus)**
```css
border-color: rgba(113,112,255,0.3);
box-shadow: 0 0 0 2px rgba(94,106,210,0.15);
```

**Textarea (答题区)**
```css
background: rgba(255,255,255,0.02);
color: #f7f8f8;
border: 1px solid rgba(255,255,255,0.08);
padding: 16px;
border-radius: 8px;
font-size: 16px;
line-height: 1.8;
min-height: 280px;
```

### Navigation

**Navbar**
```css
background: rgba(15,16,17,0.85);
backdrop-filter: blur(12px);
border-bottom: 1px solid rgba(255,255,255,0.05);
```

### Badges & Pills

**Type Badge (题型)**
```css
background: rgba(94,106,210,0.15);
color: #7170ff;
padding: 2px 10px;
border-radius: 9999px;
font-size: 12px;
font-weight: 590;
```

**Score Badge**
```css
/* High */
background: rgba(16,185,129,0.15);
color: #10b981;

/* Medium */
background: rgba(245,158,11,0.15);
color: #f59e0b;

/* Low */
background: rgba(239,68,68,0.15);
color: #ef4444;
```

### Progress Bar

```css
background: rgba(255,255,255,0.05);
border-radius: 9999px;
height: 8px;
```

**Fill**
```css
background: linear-gradient(90deg, #5e6ad2, #7170ff);
border-radius: 9999px;
```

### Modal

```css
background: #191a1b;
border: 1px solid rgba(255,255,255,0.08);
border-radius: 12px;
box-shadow: rgba(0,0,0,0.85) 0px 0px 0px 1px,
            rgba(0,0,0,0.4) 0px 2px 4px;
```

### Toast

```css
background: #191a1b;
border: 1px solid rgba(255,255,255,0.08);
border-radius: 8px;
color: #f7f8f8;
font-size: 14px;
font-weight: 510;
```

## Depth System

| Level | Treatment | Use |
|-------|-----------|-----|
| 0 | Flat, `#08090a` | Page background |
| 1 | `rgba(255,255,255,0.02)` bg | Glass cards |
| 2 | `#191a1b` bg + border | Elevated cards |
| 3 | `#28282c` bg | Hover states |
| 4 | Multi-layer shadow | Modals, dropdowns |

## GSAP Animation Specs

### Scroll Reveal
```javascript
gsap.set('.reveal', { y: 30, autoAlpha: 0 });
// onEnter: gsap.to(el, { y: 0, autoAlpha: 1, duration: 0.6, ease: 'power2.out' });
```

### Card Hover (Desktop)
```javascript
gsap.to(card, { y: -4, boxShadow: '0 8px 25px rgba(0,0,0,0.3)', duration: 0.3 });
```

### Score Counter
```javascript
gsap.to(obj, { val: target, duration: 2, ease: 'power2.out', onUpdate: ... });
// onComplete: gsap.fromTo(el, { scale: 1 }, { scale: 1.08, yoyo: true, repeat: 1 });
```

### Button Click
```javascript
gsap.fromTo(btn, { scale: 0.97 }, { scale: 1, duration: 0.3, ease: 'back.out(2)' });
```

## Do's and Don'ts

### Do
- Use `#f7f8f8` for primary text — never pure `#ffffff`
- Keep button backgrounds near-transparent on dark surfaces
- Reserve brand purple (`#5e6ad2`) for CTAs and interactive accents only
- Use semi-transparent white borders, never solid dark borders
- Apply `font-feature-settings: "cv01", "ss03"` on all Inter text
- Use weight 510 as default emphasis weight
- Apply negative letter-spacing at display sizes

### Don't
- Don't use pure white (`#ffffff`) as primary text
- Don't use weight 700 — maximum is 590
- Don't introduce warm colors into UI chrome
- Don't use drop shadows for elevation on dark surfaces — use luminance stepping
- Don't use solid colored backgrounds for buttons
- Don't skip OpenType features (`cv01`, `ss03`)

## Responsive

| Breakpoint | Width | Changes |
|------------|-------|---------|
| Mobile | <768px | Single column, hamburger nav, display 72→36px |
| Tablet | 768–1024px | 2-column grids |
| Desktop | >1024px | Full layout, 3-column grids |

## Font CDN

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
```
