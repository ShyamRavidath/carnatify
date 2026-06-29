import { Ear, MagnifyingGlass, BookOpen } from "@phosphor-icons/react/dist/ssr";
import Reveal from "./Reveal";

const STEPS = [
  {
    icon: Ear,
    step: "01",
    title: "Listen",
    body: "Point Carnatify at a performance. It traces the melodic contour — the tonic-normalised pitch line that carries a raga's soul.",
  },
  {
    icon: MagnifyingGlass,
    step: "02",
    title: "Identify",
    body: "A classifier weighs the phrase patterns to name the raga, while contour matching finds which known composition is being sung.",
  },
  {
    icon: BookOpen,
    step: "03",
    title: "Understand",
    body: "Carnatify surfaces the composer, the language, and an English meaning — so the lyrics resolve from sound into significance.",
  },
];

export default function HowItWorks() {
  return (
    <section className="mx-auto w-full max-w-6xl px-6 py-28 md:py-40">
      <Reveal>
        <span className="eyebrow">How it works</span>
        <h2 className="mt-6 max-w-2xl font-serif text-4xl font-semibold leading-tight text-burgundy md:text-5xl">
          From a single phrase to its full meaning.
        </h2>
      </Reveal>

      <div className="mt-16 grid grid-cols-1 gap-6 md:grid-cols-3">
        {STEPS.map(({ icon: Icon, step, title, body }, i) => (
          <Reveal key={title} delay={i * 120}>
            <div className="bezel h-full">
              <div className="bezel-core flex h-full flex-col gap-5 p-8">
                <div className="flex items-center justify-between">
                  <span className="flex h-12 w-12 items-center justify-center rounded-full border border-gold/40 bg-saffron/5">
                    <Icon size={24} weight="light" className="text-saffron" />
                  </span>
                  <span className="font-serif text-3xl font-semibold text-gold/50">
                    {step}
                  </span>
                </div>
                <h3 className="font-serif text-2xl font-semibold text-ink">
                  {title}
                </h3>
                <p className="max-w-prose text-[15px] leading-relaxed text-ink/70">
                  {body}
                </p>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
