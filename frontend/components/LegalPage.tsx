import Nav from "@/components/Nav";

// Shared shell for the plain-text pages App Store Connect links to
// (/privacy, /support). Keep them static: Apple's reviewer must be able to
// load them without the backend being awake.
export default function LegalPage({
  eyebrow,
  title,
  updated,
  children,
}: {
  eyebrow: string;
  title: string;
  updated: string;
  children: React.ReactNode;
}) {
  return (
    <main className="relative overflow-x-clip">
      <Nav />
      <article className="mx-auto w-full max-w-prose px-6 pb-32 pt-36">
        <span className="eyebrow">{eyebrow}</span>
        <h1 className="mt-6 font-serif text-5xl font-semibold tracking-tight text-burgundy">
          {title}
        </h1>
        <p className="mt-3 text-sm text-ink/50">Last updated {updated}</p>
        <div
          className="mt-10 space-y-5 text-base leading-relaxed text-ink/75
                     [&_a]:text-saffron [&_a]:underline [&_h2]:mt-10 [&_h2]:font-serif
                     [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:text-burgundy
                     [&_li]:ml-5 [&_li]:list-disc [&_ul]:space-y-2"
        >
          {children}
        </div>
      </article>
    </main>
  );
}
