/** Flat stroke icons (currentColor, 18px) for sidebar nav items. */

const common = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

export function IndexIcon() {
  return (
    <svg {...common}>
      <path d="M12 3v10m0 0l-3.5-3.5M12 13l3.5-3.5" />
      <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
    </svg>
  );
}

export function OverviewIcon() {
  return (
    <svg {...common}>
      <rect x="3" y="3" width="8" height="8" rx="1.5" />
      <rect x="13" y="3" width="8" height="5" rx="1.5" />
      <rect x="13" y="10" width="8" height="11" rx="1.5" />
      <rect x="3" y="13" width="8" height="8" rx="1.5" />
    </svg>
  );
}

export function ChatIcon() {
  return (
    <svg {...common}>
      <path d="M4 5h16v11H8l-4 4V5z" />
    </svg>
  );
}

export function HistoryIcon() {
  return (
    <svg {...common}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

export function OnboardingIcon() {
  return (
    <svg {...common}>
      <path d="M6 3h9l5 5v13H6z" />
      <path d="M15 3v5h5" />
      <path d="M9 13h6M9 17h6" />
    </svg>
  );
}

export function EvaluationIcon() {
  return (
    <svg {...common}>
      <path d="M9 11l2 2 4-4" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}
