"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CaretDown,
  Microphone,
  MusicNotes,
  Sparkle,
  StopCircle,
  WarningCircle,
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
type Tab = "archive" | "record";
type RecordState = "idle" | "recording" | "recorded" | "error";

// MOCK — replace body of analyseAudio with `await predictAudio(blob)` once backend is deployed
const MOCK_RESULT: PredictResult = {
  raga: [
    { name: "Bhairavi", confidence: 0.31 },
    { name: "Tōḍi", confidence: 0.22 },
    { name: "Śankarābharaṇaṁ", confidence: 0.15 },
  ],
  matches: [
    { title: "Ninnuvina", score: 0.91, track_id: "mock_1" },
    { title: "Koluvaiyunnade", score: 0.87, track_id: "mock_2" },
    { title: "Brova Bharama", score: 0.82, track_id: "mock_3" },
  ],
  tonic: 147.0,
  duration: 30.0,
};

export default function DemoPage() {
  const [tab, setTab] = useState<Tab>("archive");

  // ── archive tab state ────────────────────────────────────────────────────
  const [tracks, setTracks] = useState<Track[]>([]);
  const [tracksError, setTracksError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string>("");

  // ── shared results state ─────────────────────────────────────────────────
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<PredictResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ── record tab state ─────────────────────────────────────────────────────
  const [recordState, setRecordState] = useState<RecordState>("idle");
  const [recordError, setRecordError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [waveData, setWaveData] = useState<number[]>(Array(24).fill(0));
  const [recordedDuration, setRecordedDuration] = useState(0);

  // ── refs ─────────────────────────────────────────────────────────────────
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const rafIdRef = useRef<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const blobRef = useRef<Blob | null>(null);
  const startTimeRef = useRef<number>(0);

  function stopWaveform() {
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
  }

  // ── load track list once ─────────────────────────────────────────────────
  useEffect(() => {
    getTracks()
      .then((t) => {
        setTracks(t);
        if (t.length) setSelected(t[0].track_id);
      })
      .catch((e: Error) => setTracksError(e.message));
  }, []);

  // ── cleanup on unmount ───────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      const mr = mediaRecorderRef.current;
      if (mr && mr.state !== "inactive") {
        mediaRecorderRef.current = null;
        mr.stop();
      }
      if (rafIdRef.current !== null) cancelAnimationFrame(rafIdRef.current);
      if (timerRef.current !== null) clearInterval(timerRef.current);
      if (audioCtxRef.current) audioCtxRef.current.close();
    };
  }, []);

  // ── track options ────────────────────────────────────────────────────────
  const options = useMemo(() => {
    const counts = new Map<string, number>();
    tracks.forEach((t) => counts.set(t.title, (counts.get(t.title) ?? 0) + 1));
    return tracks.map((t) => ({
      value: t.track_id,
      label:
        (counts.get(t.title) ?? 0) > 1
          ? `${t.title}  ·  ${t.track_id}`
          : t.title,
    }));
  }, [tracks]);

  const selectedTrack = tracks.find((t) => t.track_id === selected);

  // ── tab switching ────────────────────────────────────────────────────────
  function switchTab(newTab: Tab) {
    // Detach recorder so its onstop won't update state after we reset
    const mr = mediaRecorderRef.current;
    mediaRecorderRef.current = null;
    if (mr && mr.state !== "inactive") mr.stop();

    stopWaveform();
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
    chunksRef.current = [];
    blobRef.current = null;

    setTab(newTab);
    setRecordState("idle");
    setRecordError(null);
    setElapsed(0);
    setWaveData(Array(24).fill(0));
    setRecordedDuration(0);
    setStatus("idle");
    setResult(null);
    setError(null);
  }

  // ── recording ────────────────────────────────────────────────────────────
  async function startRecording() {
    setRecordError(null);
    chunksRef.current = [];
    blobRef.current = null;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setRecordState("error");
      setRecordError(
        "Microphone access denied. Please allow mic access in your browser settings."
      );
      return;
    }

    const audioCtx = new AudioContext();
    audioCtxRef.current = audioCtx;
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    const source = audioCtx.createMediaStreamSource(stream);
    source.connect(analyser);

    const mr = new MediaRecorder(stream);

    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    mr.onstop = () => {
      // Always clean up the mic stream
      stream.getTracks().forEach((t) => t.stop());

      // If switchTab detached us, skip all state updates
      if (mediaRecorderRef.current !== mr) return;

      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      blobRef.current = blob;
      const dur = Math.round((Date.now() - startTimeRef.current) / 1000);
      setRecordedDuration(dur);
      setRecordState("recorded");
      stopWaveform();
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (audioCtxRef.current) {
        audioCtxRef.current.close();
        audioCtxRef.current = null;
      }
      setWaveData(Array(24).fill(0));
    };

    mediaRecorderRef.current = mr;
    mr.start();
    startTimeRef.current = Date.now();
    setElapsed(0);
    setRecordState("recording");

    // Counting timer (polls at 200ms for responsiveness, auto-stops at 60s)
    timerRef.current = setInterval(() => {
      const secs = Math.floor((Date.now() - startTimeRef.current) / 1000);
      setElapsed(secs);
      if (secs >= 60) {
        if (mediaRecorderRef.current?.state !== "inactive") {
          mediaRecorderRef.current?.stop();
        }
        if (timerRef.current !== null) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
      }
    }, 200);

    // Waveform rAF loop
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      analyser.getByteFrequencyData(dataArray);
      const binCount = dataArray.length;
      const bars: number[] = [];
      for (let i = 0; i < 24; i++) {
        const start = Math.floor((i / 24) * binCount);
        const end = Math.floor(((i + 1) / 24) * binCount);
        let sum = 0;
        for (let j = start; j < end; j++) sum += dataArray[j];
        bars.push(end > start ? sum / (end - start) : 0);
      }
      setWaveData(bars);
      rafIdRef.current = requestAnimationFrame(tick);
    };
    rafIdRef.current = requestAnimationFrame(tick);
  }

  function stopRecording() {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      mediaRecorderRef.current.stop();
    }
  }

  async function analyseAudio() {
    if (!blobRef.current) return;
    const blob = blobRef.current;

    if (recordedDuration < 15) {
      setStatus("error");
      setError("Record at least 15 seconds for a reliable analysis.");
      return;
    }
    if (blob.size > 50 * 1024 * 1024) {
      setStatus("error");
      setError("Recording too large — please try a shorter clip.");
      return;
    }

    setStatus("loading");
    setResult(null);
    setError(null);

    try {
      // MOCK — swap for `await predictAudio(blob)` once backend is deployed
      await new Promise<void>((resolve) => setTimeout(resolve, 2000));
      setResult(MOCK_RESULT);
      setStatus("done");
    } catch (e) {
      setError((e as Error).message);
      setStatus("error");
    }
  }

  // ── archive analysis ──────────────────────────────────────────────────────
  async function analyseArchive() {
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

  function formatTime(secs: number) {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  }

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
          Choose a recording from the Saraga archive or record yourself, and
          Carnatify will name the raga, match the composition, and read you its
          meaning.
        </p>
      </header>

      {/* ── Tab pills ──────────────────────────────────────────────────────── */}
      <div className="mt-8 flex gap-2">
        <button
          onClick={() => switchTab("archive")}
          className={`rounded-full px-5 py-2 text-sm font-medium transition-colors ${
            tab === "archive"
              ? "bg-saffron text-white"
              : "text-ink/60 hover:text-saffron"
          }`}
        >
          Saraga Archive
        </button>
        <button
          onClick={() => switchTab("record")}
          className={`rounded-full px-5 py-2 text-sm font-medium transition-colors ${
            tab === "record"
              ? "bg-saffron text-white"
              : "text-ink/60 hover:text-saffron"
          }`}
        >
          Record Audio
        </button>
      </div>

      {/* ── Picker / Recorder card ──────────────────────────────────────────── */}
      <div className="mt-4 bezel">
        <div className="bezel-core p-6">
          {tab === "archive" ? (
            <div className="flex flex-col gap-5 md:flex-row md:items-end">
              <label className="flex-1">
                <span className="mb-2 block text-xs uppercase tracking-eyebrow text-ink/50">
                  Composition / rendition
                </span>
                {tracksError ? (
                  <div className="flex items-center gap-2 rounded-xl border border-burgundy/30 bg-burgundy/5 px-4 py-3 text-sm text-burgundy">
                    <WarningCircle size={18} /> Could not reach the API —{" "}
                    {tracksError}
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
                onClick={analyseArchive}
                disabled={!selected || status === "loading"}
                className="group cta justify-center disabled:cursor-not-allowed disabled:opacity-50"
              >
                {status === "loading" ? "Analysing…" : "Analyse"}
                <span className="cta-icon">
                  <MusicNotes size={16} weight="bold" />
                </span>
              </button>
            </div>
          ) : (
            /* ── Record Audio tab ──────────────────────────────────────────── */
            <div>
              {recordError ? (
                <div className="flex items-center gap-3 rounded-xl border border-burgundy/30 bg-burgundy/5 px-5 py-4 text-burgundy">
                  <WarningCircle size={20} className="shrink-0" />
                  <p className="text-sm">{recordError}</p>
                </div>
              ) : recordState === "idle" ? (
                <div className="flex flex-col items-center gap-4 py-8">
                  <button
                    aria-label="Start recording"
                    onClick={startRecording}
                    className="flex h-20 w-20 items-center justify-center rounded-full
                               bg-red-500 transition-colors hover:bg-red-600"
                  >
                    <Microphone size={40} weight="fill" className="text-white" />
                  </button>
                  <p className="text-sm text-ink/55">
                    Tap to record — up to 60 seconds
                  </p>
                </div>
              ) : recordState === "recording" ? (
                <div className="flex flex-col items-center gap-5 py-8">
                  <button
                    aria-label="Stop recording"
                    onClick={stopRecording}
                    className="flex h-20 w-20 items-center justify-center rounded-full
                               bg-red-500 transition-colors hover:bg-red-600"
                  >
                    <StopCircle size={40} weight="fill" className="text-white" />
                  </button>
                  <p className="font-mono text-3xl tabular-nums text-ink">
                    {formatTime(elapsed)}
                  </p>
                  {/* 24-bar waveform visualizer */}
                  <div className="flex h-16 items-end gap-[3px]">
                    {waveData.map((v, i) => {
                      const height = Math.max(4, Math.round(4 + (v / 255) * 56));
                      return (
                        <div
                          key={i}
                          className="w-2 rounded-t bg-[#FF6B00] transition-all duration-75"
                          style={{ height: `${height}px` }}
                        />
                      );
                    })}
                  </div>
                </div>
              ) : recordState === "recorded" ? (
                <div className="flex flex-col items-center gap-5 py-8">
                  <p className="text-sm text-ink/70">
                    Recorded:{" "}
                    <span className="font-medium text-ink">
                      {recordedDuration} seconds
                    </span>
                  </p>
                  <button
                    onClick={analyseAudio}
                    disabled={status === "loading"}
                    className="group cta justify-center disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {status === "loading" ? "Analysing…" : "Analyse"}
                    <span className="cta-icon">
                      <MusicNotes size={16} weight="bold" />
                    </span>
                  </button>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {/* ── Results ────────────────────────────────────────────────────────── */}
      <section className="mt-8">
        {status === "idle" && <EmptyState />}

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
