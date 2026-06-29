import Link from "next/link";

export default function Nav() {
  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-40 flex justify-center">
      <nav
        className="pointer-events-auto mt-6 flex w-max items-center gap-6 rounded-full
                   border border-gold/30 bg-ivory/70 px-5 py-2.5 backdrop-blur-xl
                   shadow-[0_12px_40px_-24px_rgba(139,0,0,0.4)]"
      >
        <Link
          href="/"
          className="font-serif text-lg font-semibold tracking-tight text-burgundy"
        >
          Carnatify
        </Link>
        <span aria-hidden className="h-4 w-px bg-gold/40" />
        <Link
          href="/demo"
          className="text-sm font-medium text-ink/70 transition-colors duration-300 hover:text-saffron"
        >
          Try the demo
        </Link>
      </nav>
    </header>
  );
}
