"use client";

import { useEffect, useState } from "react";

/** A label + animated horizontal bar that grows to `value` (0–1) on mount. */
export default function ScoreBar({
  label,
  value,
  accent = "saffron",
  sub,
}: {
  label: string;
  value: number;
  accent?: "saffron" | "burgundy";
  sub?: string;
}) {
  const [grown, setGrown] = useState(false);
  const pct = Math.max(0, Math.min(1, value)) * 100;

  useEffect(() => {
    const id = requestAnimationFrame(() => setGrown(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const fill = accent === "burgundy" ? "bg-burgundy" : "bg-saffron";

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-4">
        <span className="font-serif text-lg text-ink">{label}</span>
        <span className="font-sans text-sm tabular-nums text-ink/50">
          {pct.toFixed(1)}%
        </span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-gold/15">
        <div
          className={`bar-fill h-full rounded-full ${fill}`}
          style={{ width: grown ? `${pct}%` : "0%" }}
        />
      </div>
      {sub ? <p className="text-xs text-ink/40">{sub}</p> : null}
    </div>
  );
}
