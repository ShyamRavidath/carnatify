/** Animated waveform placeholder shown while inference runs. */
export default function WaveSkeleton({ label }: { label: string }) {
  const bars = Array.from({ length: 40 });
  return (
    <div className="flex flex-col items-center gap-6 py-16">
      <div className="flex h-20 items-center gap-1.5" aria-hidden>
        {bars.map((_, i) => (
          <span
            key={i}
            className="w-1.5 rounded-full bg-saffron/40"
            style={{
              height: `${20 + 60 * Math.abs(Math.sin(i * 0.5))}%`,
              animation: "wave-pulse 1.2s ease-in-out infinite",
              animationDelay: `${i * 40}ms`,
            }}
          />
        ))}
      </div>
      <p className="text-sm uppercase tracking-eyebrow text-ink/50">{label}</p>
    </div>
  );
}
