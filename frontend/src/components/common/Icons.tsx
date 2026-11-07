type P = { className?: string };
const base = (className = 'h-5 w-5') => ({
  className,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
});

export const MicIcon = ({ className }: P) => (
  <svg {...base(className)}>
    <rect x="9" y="3" width="6" height="11" rx="3" />
    <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
  </svg>
);

export const StopIcon = ({ className }: P) => (
  <svg {...base(className)}>
    <rect x="7" y="7" width="10" height="10" rx="1.5" fill="currentColor" />
  </svg>
);

export const SpeakerIcon = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M4 9v6h4l5 4V5L8 9H4z" />
    <path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12" />
  </svg>
);

export const SpeakerOffIcon = ({ className }: P) => (
  <svg {...base(className)}>
    <path d="M4 9v6h4l5 4V5L8 9H4z" />
    <path d="M17 9l5 6M22 9l-5 6" />
  </svg>
);
