/**
 * GemIcon — hexagon-cut SVG gem icon used on task cards and in the admin UI.
 *
 * Renders a top-view gem with four polygon facets. Hue controls colour;
 * size controls the rendered dimensions (default 40px).
 */
import type { GemHue } from '../api/tasks'

/** Four-shade colour set for one gem facet layer: crown, upper, lower, base. */
interface HueColors {
  crown: string
  upper: string
  lower: string
  base: string
}

/** Tailwind colour palette values for each supported hue. */
const HUE_COLORS: Record<GemHue, HueColors> = {
  red:     { crown: '#f87171', upper: '#ef4444', lower: '#dc2626', base: '#b91c1c' },
  orange:  { crown: '#fb923c', upper: '#f97316', lower: '#ea580c', base: '#c2410c' },
  amber:   { crown: '#fbbf24', upper: '#f59e0b', lower: '#d97706', base: '#b45309' },
  yellow:  { crown: '#fde047', upper: '#eab308', lower: '#ca8a04', base: '#a16207' },
  lime:    { crown: '#a3e635', upper: '#84cc16', lower: '#65a30d', base: '#4d7c0f' },
  green:   { crown: '#4ade80', upper: '#22c55e', lower: '#16a34a', base: '#15803d' },
  emerald: { crown: '#34d399', upper: '#10b981', lower: '#059669', base: '#047857' },
  teal:    { crown: '#2dd4bf', upper: '#14b8a6', lower: '#0d9488', base: '#0f766e' },
  cyan:    { crown: '#22d3ee', upper: '#06b6d4', lower: '#0891b2', base: '#0e7490' },
  sky:     { crown: '#38bdf8', upper: '#0ea5e9', lower: '#0284c7', base: '#0369a1' },
  blue:    { crown: '#60a5fa', upper: '#3b82f6', lower: '#2563eb', base: '#1d4ed8' },
  indigo:  { crown: '#818cf8', upper: '#6366f1', lower: '#4f46e5', base: '#4338ca' },
  violet:  { crown: '#a78bfa', upper: '#8b5cf6', lower: '#7c3aed', base: '#6d28d9' },
  purple:  { crown: '#c084fc', upper: '#a855f7', lower: '#9333ea', base: '#7e22ce' },
  fuchsia: { crown: '#e879f9', upper: '#d946ef', lower: '#c026d3', base: '#a21caf' },
  rose:    { crown: '#fb7185', upper: '#f43f5e', lower: '#e11d48', base: '#be123c' },
}

interface GemIconProps {
  /** Gem hue — maps to a set of four shaded polygon fill colors. */
  hue: GemHue
  /** Rendered width and height in pixels. Default: 40. */
  size?: number
}

/**
 * Hexagon-cut gem SVG icon.
 *
 * @example
 * <GemIcon hue="indigo" size={36} />
 */
export default function GemIcon({ hue, size = 40 }: GemIconProps) {
  const c = HUE_COLORS[hue]
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 52 52"
      aria-hidden="true"
    >
      {/* Outer hexagon outline */}
      <polygon points="26,4 46,16 46,36 26,48 6,36 6,16" fill={c.upper} opacity={0.9} />
      {/* Crown facet (top, lightest) */}
      <polygon points="26,4 46,16 26,22 6,16" fill={c.crown} opacity={0.95} />
      {/* Upper side facets */}
      <polygon points="26,22 46,16 46,36 26,48 6,36 6,16" fill={c.lower} opacity={0.85} />
      {/* Base facet (bottom, darkest) */}
      <polygon points="26,22 46,36 26,48 6,36" fill={c.base} opacity={0.8} />
    </svg>
  )
}
