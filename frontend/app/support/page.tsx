import type { Metadata } from "next";
import LegalPage from "@/components/LegalPage";
import { SUPPORT_EMAIL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Support — Carnatify",
  description: "Help with the Carnatify iPhone app.",
};

export default function Support() {
  return (
    <LegalPage eyebrow="Carnatify for iPhone" title="Support" updated="11 October 2026">
      <p>
        Need help, found a wrong answer, or have an idea? Email{" "}
        <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a> and we will get back to you.
      </p>

      <h2>Getting a good result</h2>
      <ul>
        <li>Record as close to the full three minutes as you can. Short clips are much less reliable.</li>
        <li>Hold the phone toward the performers and away from chatter, fans, or applause.</li>
        <li>Alapana and kriti sections both work; long percussion solos (tani avartanam) do not.</li>
      </ul>

      <h2>Common questions</h2>
      <p>
        <strong>Why does it say “possible ragas” instead of one answer?</strong> Raga
        identification from a phone recording is genuinely hard, and closely related ragas
        share most of their notes. Carnatify shows its ranked suggestions honestly rather than
        claiming certainty it does not have.
      </p>
      <p>
        <strong>The first result took a long time.</strong> The server sleeps when nobody has
        used it for a while. The first request after that can take up to a minute while it
        wakes up; later ones are faster.
      </p>
      <p>
        <strong>It says the microphone is off.</strong> Open Settings → Carnatify and turn on
        Microphone.
      </p>
      <p>
        <strong>Is my recording saved?</strong> No. See the{" "}
        <a href="/privacy">privacy policy</a>.
      </p>
    </LegalPage>
  );
}
