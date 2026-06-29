"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CaretDown,
  Sparkle,
  WarningCircle,
  MusicNotes,
} from "@phosphor-icons/react";
import {
  getTracks,
  predict,
  getMeaning,
  type Track,
  type PredictResult,
  type MeaningResult,
} from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";
import WaveSkeleton from "@/components/WaveSkeleton";

type Status = "idle" | "loading" | "done" | "error";

export default function DemoPage() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [tracksError, setTracksError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string>("");

  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<PredictResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ── load track list once ────────────────────────────────────────────────
  useEffect(() => {
    getTracks()
      .then((t) => {
        setTracks(t);
        if (t.length) setSelected(t[0].track_id);
      })
      .catch((e) => setTracksError(e.message));
  }, []);

  // Group duplicate titles by appending the track_id, mirroring the original app.
  const options = useMemo(() => {
    const counts = new Map<string, number>();
    tracks.forEach((t) => counts.set(t.title, (counts.get(t.title) ?? 0) + 1));
    return tracks.map((t) => ({
      value: t.track_id,
      label:
        (counts.get(t.title) ?? 0) > 1 ? `${t.title}  ·  ${t.track_id}` : t.title,
    }));
  }, [tracks]);

  const selectedTrack = tracks.find((t) => t.track_id === selected);

  async function analyse() {
    if (!selected) return;
    setStatus("loading");
    setResult(null);
    setError(null);
    try {
      const r = await predict(selected);
      setResult(r);
      setStatus("done");
    } catch (e) {
      setError((e as Error).message);
      setStatus("error");
    }
  }

  const topMatch = result?.matches?.[0]?.title ?? null;

  return (
    <main className="relative mx-auto min-h-[100dvh] w-full max-w-5xl px-6 pb-32 pt-10">
      {/* Ambient glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[60vh]
                   bg-[radial-gradient(60%_50%_at_50%_0%,rgba(255,107,0,0.08),transparent_70%)]"
      />

      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm text-ink/60 transition-colors hover:text-saffron"
      >
        <ArrowLeft size={16} weight="bold" /> Back
      </Link>

      <header className="mt-8">
        <span className="eyebrow">The demo</span>
        <h1 className="mt-5 font-serif text-4xl font-semibold leading-tight text-burgundy md:text-5xl">
          Identify a composition
        </h1>
        <p className="mt-3 max-w-prose text-ink/70">
          Choose a recording from the Saraga archive and Carnatify will name its
          raga, match the composition, and read you its meaning.
        </p>
      </header>

      {/* ── Picker ─────────────────────────────────────────────────────────── */}
      <div className="mt-10 bezel">
        <div className="bezel-core flex flex-col gap-5 p-6 md:flex-row md:items-end">
          <label className="flex-1">
            <span className="mb-2 block text-xs uppercase tracking-eyebrow text-ink/50">
              Composition / rendition
            </span>
            {tracksError ? (
              <div className="flex items-center gap-2 rounded-xl border border-burgundy/30 bg-burgundy/5 px-4 py-3 text-sm text-burgundy">
                <WarningCircle size={18} /> Could not reach the API — {tracksError}
              </div>
            ) : tracks.length === 0 ? (
              <div className="h-12 w-full rounded-xl bg-gold/10 shimmer" />
            ) : (
              <div className="relative">
                <select
                  value={selected}
                  onChange={(e) => setSelected(e.target.value)}
                  className="w-full appearance-none rounded-xl border border-gold/30 bg-ivory
                             px-4 py-3 pr-10 font-sans text-ink outline-none
                             transition-colors focus:border-saffron"
                >
                  {options.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <CaretDown
                  size={16}
                  className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-ink/40"
                />
              </div>
            )}
            {selectedTrack ? (
              <p className="mt-2 text-xs text-ink/40">
                Metadata raga: {selectedTrack.raga || "—"} · tonic{" "}
                {selectedTrack.tonic.toFixed(1)} Hz
              </p>
            ) : null}
          </label>

          <button
            onClick={analyse}
            disabled={!selected || status === "loading"}
            className="group cta justify-center disabled:cursor-not-allowed disabled:opacity-50"
          >
            {status === "loading" ? "Analysing…" : "Analyse"}
            <span className="cta-icon">
              <MusicNotes size={16} weight="bold" />
            </span>
          </button>
        </div>
      </div>

      {/* ── Results ────────────────────────────────────────────────────────── */}
      <section className="mt-8">
        {status === "idle" && (
          <EmptyState />
        )}

        {status === "loading" && (
          <div className="bezel">
            <div className="bezel-core">
              <WaveSkeleton label="Tracing the contour · matching phrases" />
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="flex items-center gap-3 rounded-2xl border border-burgundy/30 bg-burgundy/5 px-6 py-5 text-burgundy">
            <WarningCircle size={22} />
            <div>
              <p className="font-medium">Analysis failed</p>
              <p className="text-sm text-burgundy/70">{error}</p>
            </div>
          </div>
        )}

        {status === "done" && result && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <ResultCard title="Raga">
              {result.raga.length ? (
                <div className="space-y-6">
                  {result.raga.map((r, i) => (
                    <ScoreBar
                      key={r.name + i}
                      label={r.name}
                      value={r.confidence}
                      accent={i === 0 ? "saffron" : "burgundy"}
                    />
                  ))}
                </div>
              ) : (
                <Muted>No confident raga prediction for this contour.</Muted>
              )}
            </ResultCard>

            <ResultCard title="Composition matches">
              {result.matches.length ? (
                <div className="space-y-6">
                  {result.matches.map((m, i) => (
                    <ScoreBar
                      key={m.track_id + i}
                      label={m.title}
                      value={m.score}
                      accent={i === 0 ? "saffron" : "burgundy"}
                    />
                  ))}
                </div>
              ) : (
                <Muted>No composition matched.</Muted>
              )}
            </ResultCard>

            <div className="md:col-span-2">
              <MeaningPanel topTitle={topMatch} />
            </div>
          </div>
        )}
      </section>
    </main>
  );
}

// ── sub-components ──────────────────────────────────────────────────────────

function ResultCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bezel h-full animate-rise-in">
      <div className="bezel-core h-full p-7">
        <h2 className="mb-6 font-serif text-2xl font-semibold text-burgundy">
          {title}
        </h2>
        {children}
      </div>
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-ink/50">{children}</p>;
}

function EmptyState() {
  return (
    <div className="bezel">
      <div className="bezel-core flex flex-col items-center gap-3 px-6 py-20 text-center">
        <MusicNotes size={32} weight="light" className="text-gold" />
        <p className="font-serif text-xl text-ink/70">
          Pick a recording and press Analyse.
        </p>
        <p className="max-w-sm text-sm text-ink/45">
          Carnatify will identify the raga and the composition, then offer to
          read you the meaning of its lyrics.
        </p>
      </div>
    </div>
  );
}

function MeaningPanel({ topTitle }: { topTitle: string | null }) {
  const [state, setState] = useState<Status>("idle");
  const [data, setData] = useState<MeaningResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Reset whenever the top match changes.
  useEffect(() => {
    setState("idle");
    setData(null);
    setErr(null);
  }, [topTitle]);

  async function reveal() {
    if (!topTitle) return;
    setState("loading");
    setErr(null);
    try {
      const r = await getMeaning(topTitle);
      setData(r);
      setState("done");
    } catch (e) {
      setErr((e as Error).message);
      setState("error");
    }
  }

  return (
    <div className="bezel animate-rise-in">
      <div className="bezel-core p-7">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-serif text-2xl font-semibold text-burgundy">
            Lyrics &amp; meaning
          </h2>
          {topTitle && state === "idle" && (
            <button onClick={reveal} className="group cta py-2 text-xs">
              Reveal meaning
              <span className="cta-icon">
                <Sparkle size={14} weight="bold" />
              </span>
            </button>
          )}
        </div>

        {!topTitle && (
          <Muted>No composition match available to look up.</Muted>
        )}

        {topTitle && state === "idle" && (
          <p className="mt-4 text-sm text-ink/55">
            Top match: <span className="font-serif text-ink">{topTitle}</span>.
            Reveal an English meaning &amp; cultural context, generated by Claude.
          </p>
        )}

        {state === "loading" && (
          <div className="mt-6 space-y-3">
            <div className="h-4 w-1/3 rounded bg-gold/15 shimmer" />
            <div className="h-3 w-full rounded bg-gold/15 shimmer" />
            <div className="h-3 w-11/12 rounded bg-gold/15 shimmer" />
            <div className="h-3 w-4/5 rounded bg-gold/15 shimmer" />
            <p className="pt-1 text-xs uppercase tracking-eyebrow text-ink/40">
              Asking Claude…
            </p>
          </div>
        )}

        {state === "error" && (
          <div className="mt-5 flex items-start gap-2 rounded-xl border border-burgundy/30 bg-burgundy/5 px-4 py-3 text-sm text-burgundy">
            <WarningCircle size={18} className="mt-0.5 shrink-0" />
            <span>{err}</span>
          </div>
        )}

        {state === "done" && data && (
          <div className="mt-5">
            <div className="flex flex-wrap gap-x-8 gap-y-2 border-b border-gold/20 pb-4">
              <Meta label="Title" value={data.title} />
              <Meta label="Composer" value={data.composer || "Unknown"} />
            </div>
            <p className="mt-5 whitespace-pre-line text-[15px] leading-relaxed text-ink/80">
              {data.meaning}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-eyebrow text-ink/40">
        {label}
      </p>
      <p className="font-serif text-lg text-ink">{value}</p>
    </div>
  );
}
