import Link from "next/link";
import { ArrowUpRight } from "@phosphor-icons/react/dist/ssr";
import Nav from "@/components/Nav";
import WaveformHero from "@/components/WaveformHero";
import HowItWorks from "@/components/HowItWorks";
import Reveal from "@/components/Reveal";

export default function Home() {
  return (
    <main className="relative overflow-x-clip">
      <Nav />

      {/* Ambient warm glow behind the hero. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[120vh]
                   bg-[radial-gradient(60%_50%_at_50%_0%,rgba(255,107,0,0.10),transparent_70%)]"
      />

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="mx-auto flex min-h-[100dvh] w-full max-w-6xl flex-col items-center justify-center px-6 pt-28 text-center">
        <span className="eyebrow">कर्नाटक संगीत · Carnatic music, decoded</span>

        <h1 className="mt-8 font-serif text-6xl font-semibold leading-[0.95] tracking-tight text-burgundy md:text-8xl">
          Carnatify
        </h1>
        <p className="mt-5 font-serif text-xl italic text-ink/60 md:text-2xl">
          nāda-rūpa — giving form to sound.
        </p>

        <p className="mt-7 max-w-prose text-base leading-relaxed text-ink/70 md:text-lg">
          Hear a Carnatic performance and Carnatify names its raga, finds the
          composition, and unfolds the meaning of its lyrics — centuries of
          tradition, read by the ear of a machine.
        </p>

        <div className="mt-10">
          <Link href="/demo" className="group cta">
            Identify a composition
            <span className="cta-icon">
              <ArrowUpRight size={16} weight="bold" />
            </span>
          </Link>
        </div>

        <div className="mt-20 w-full">
          <WaveformHero />
          <p className="mt-3 text-xs uppercase tracking-eyebrow text-ink/40">
            Scroll — watch the waveform become language
          </p>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────────── */}
      <HowItWorks />

      {/* ── Demo CTA ─────────────────────────────────────────────────────── */}
      <section className="mx-auto w-full max-w-6xl px-6 pb-32">
        <Reveal>
          <div className="bezel">
            <div className="bezel-core flex flex-col items-center gap-8 px-8 py-20 text-center md:py-28">
              <span className="eyebrow">The demo</span>
              <h2 className="max-w-2xl font-serif text-4xl font-semibold leading-tight text-burgundy md:text-6xl">
                Choose a recording. Hear what it knows.
              </h2>
              <p className="max-w-prose text-base leading-relaxed text-ink/70">
                Pick from 197 concert recordings in the Saraga archive and let
                Carnatify identify the raga, match the composition, and read you
                its meaning.
              </p>
              <Link href="/demo" className="group cta">
                Open the demo
                <span className="cta-icon">
                  <ArrowUpRight size={16} weight="bold" />
                </span>
              </Link>
            </div>
          </div>
        </Reveal>
      </section>

      <footer className="border-t border-gold/20 py-10 text-center text-xs text-ink/40">
        Carnatify · built on the Saraga Carnatic dataset · meanings by Claude
      </footer>
    </main>
  );
}
