interface WaveLogoProps {
  size?: number;
  className?: string;
}

export default function WaveLogo({ size = 32, className = "" }: WaveLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Wave path — extracted from icons.py _draw_wave_logo() */}
      <path
        d="M20,45 C22,45 26,60 32,60 C38,60 38,40 42,40 C46,40 46,58 50,58 C54,58 54,40 58,40 C62,40 62,58 66,58 C70,58 74,42 80,42"
        stroke="url(#vw-gradient)"
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <defs>
        <linearGradient id="vw-gradient" x1="20" y1="40" x2="80" y2="60" gradientUnits="userSpaceOnUse">
          <stop stopColor="#6366F1" />
          <stop offset="1" stopColor="#8B5CF6" />
        </linearGradient>
      </defs>
    </svg>
  );
}
