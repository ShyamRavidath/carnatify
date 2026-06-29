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

export async function getMeaning(title: string): Promise<MeaningResult> {
  return asJson<MeaningResult>(
    await fetch(`${BASE}/meaning/${encodeURIComponent(title)}`, {
      cache: "no-store",
    })
  );
}
