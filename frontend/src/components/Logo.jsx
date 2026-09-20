/** Flat, single-color mark — matches public/favicon.svg. No gradients/blur. */
export default function Logo({ size = 26 }) {
  return (
    <svg
      className="brand-mark"
      width={size}
      height={size}
      viewBox="0 0 32 32"
      aria-hidden="true"
    >
      <rect width="32" height="32" rx="6" fill="#2563eb" />
      <path
        d="M12.5 11l-4.5 5 4.5 5M19.5 11l4.5 5-4.5 5"
        fill="none"
        stroke="#ffffff"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
