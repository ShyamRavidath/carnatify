/**
 * Hero waveform. A single SVG <path> "draws" itself left-to-right as the user
 * scrolls (stroke-dashoffset animated on a scroll() timeline — see globals.css),
 * while stylized script glyphs fade in beneath it, suggesting the waveform
 * resolving into language. Entirely CSS/SVG, reversible, no canvas or video.
 */
export default function WaveformHero() {
  // A gently undulating waveform path across a 1200×200 viewbox.
  const wavePath =
    "M0,100 C 60,40 120,40 180,100 S 300,160 360,100 S 480,40 540,100 " +
    "S 660,160 720,100 S 840,40 900,100 S 1020,160 1080,100 S 1180,70 1200,100";

  return (
    <div className="relative mx-auto w-full max-w-5xl" aria-hidden>
      <svg
        viewBox="0 0 1200 200"
        className="w-full"
        fill="none"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="wave-grad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#C9A227" />
            <stop offset="50%" stopColor="#FF6B00" />
            <stop offset="100%" stopColor="#8B0000" />
          </linearGradient>
        </defs>

        {/* Faint full path so the line has a "track" before it draws. */}
        <path d={wavePath} stroke="#C9A227" strokeOpacity="0.12" strokeWidth="2" />

        {/* The animated, self-drawing waveform. */}
        <path
          d={wavePath}
          stroke="url(#wave-grad)"
          strokeWidth="3"
          strokeLinecap="round"
          className="wave-draw"
        />

        {/* Script glyphs that fade in as the wave resolves into language. */}
        <text
          className="glyph-fade"
          x="270"
          y="180"
          textAnchor="middle"
          fontSize="56"
          fill="#8B0000"
          fillOpacity="0.85"
          style={{ fontFamily: "var(--font-crimson), serif" }}
        >
          स
        </text>
        <text
          className="glyph-fade"
          x="600"
          y="186"
          textAnchor="middle"
          fontSize="64"
          fill="#FF6B00"
          style={{ fontFamily: "var(--font-crimson), serif" }}
        >
          सं
        </text>
        <text
          className="glyph-fade"
          x="930"
          y="180"
          textAnchor="middle"
          fontSize="56"
          fill="#8B0000"
          fillOpacity="0.85"
          style={{ fontFamily: "var(--font-crimson), serif" }}
        >
          गी
        </text>
      </svg>
    </div>
  );
}
