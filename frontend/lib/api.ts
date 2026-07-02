/**
 * Thin client for the Carnatify FastAPI backend (HuggingFace Space).
 * Base URL comes from NEXT_PUBLIC_API_BASE; no secrets ever live here.
 */

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8077";

export interface Track {
  track_id: string;
  title: string;
  raga: string;
  tonic: number;
}

export interface RagaPrediction {
  name: string;
  confidence: number;
}

export interface CompositionMatch {
  title: string;
  score: number;
  track_id: string;
}

export interface PredictResult {
  raga: RagaPrediction[];
  matches: CompositionMatch[];
  tonic?: number;    // only present from /predict-audio
  duration?: number; // only present from /predict-audio
}

export interface MeaningResult {
  title: string;
  composer: string;
  meaning: string;
}

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function getTracks(): Promise<Track[]> {
  return asJson<Track[]>(await fetch(`${BASE}/tracks`, { cache: "no-store" }));
}

export async function predict(trackId: string): Promise<PredictResult> {
  return asJson<PredictResult>(
    await fetch(`${BASE}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track_id: trackId }),
    })
  );
}

/** MediaRecorder output differs by browser: Chrome webm, Safari mp4, Firefox ogg. */
function audioExtension(mimeType: string): string {
  const t = mimeType.toLowerCase();
  if (t.includes("mp4") || t.includes("aac")) return "m4a";
  if (t.includes("ogg") || t.includes("opus")) return "ogg";
  if (t.includes("mpeg") || t.includes("mp3")) return "mp3";
  if (t.includes("wav")) return "wav";
  return "webm";
}

export async function predictAudio(blob: Blob): Promise<PredictResult> {
  const form = new FormData();
  form.append("file", blob, `recording.${audioExtension(blob.type)}`);

  // First request after the Space cold-starts can take 2–4 minutes (model
  // download + container init); cap the wait so the UI never hangs silently.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5 * 60 * 1000);
  try {
    return await asJson<PredictResult>(
      await fetch(`${BASE}/predict-audio`, {
        method: "POST",
        body: form,
        signal: controller.signal,
      })
    );
  } catch (e) {
    if ((e as Error).name === "AbortError") {
      throw new Error(
        "Analysis timed out after 5 minutes — the server may be busy. Please try again in a moment."
      );
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export async function getMeaning(title: string): Promise<MeaningResult> {
  return asJson<MeaningResult>(
    await fetch(`${BASE}/meaning/${encodeURIComponent(title)}`, {
      cache: "no-store",
    })
  );
}
