/** Small inline stroke icons used in the refined card/result styling. No icon font or image requests: each is a
 * few bytes of inline SVG, so they cost nothing extra over the plain-text list this replaced. */
const common = { width: 15, height: 15, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };

export function FeeIcon() {
  return (
    <svg {...common}>
      <rect x="3" y="6" width="18" height="13" rx="2" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

export function ClockIcon() {
  return (
    <svg {...common}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5 V12 L15 14" />
    </svg>
  );
}

export function WarningIcon() {
  return (
    <svg {...common} width="14" height="14">
      <path d="M12 3 L21 19 H3 Z" />
      <line x1="12" y1="9" x2="12" y2="13.5" />
      <circle cx="12" cy="16.2" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** A circled, filled exclamation mark: visually distinct from WarningIcon's triangle, for the NLL note — a more
 * "stop and read this" mark than a generic caution triangle, matching how much more it matters. */
export function AlertIcon() {
  return (
    <svg {...common} width="14" height="14">
      <circle cx="12" cy="12" r="9.5" />
      <line x1="12" y1="7" x2="12" y2="13.2" />
      <circle cx="12" cy="16.6" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}
