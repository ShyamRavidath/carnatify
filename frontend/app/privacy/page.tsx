import type { Metadata } from "next";
import LegalPage from "@/components/LegalPage";
import { SUPPORT_EMAIL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Privacy Policy — Carnatify",
  description: "How the Carnatify app handles the audio you record.",
};

export default function Privacy() {
  return (
    <LegalPage eyebrow="Carnatify for iPhone" title="Privacy Policy" updated="11 October 2026">
      <p>
        Carnatify suggests which raga a Carnatic performance may be in. This page explains
        exactly what happens to the audio you record. The short version: your recording is
        used once, to make the suggestion, and is then deleted. We do not keep it.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li>
          <strong>Audio you choose to record.</strong> Recording only starts when you tap
          Listen, and stops when you tap Stop or after three minutes. The app asks for
          microphone permission the first time and never records in the background.
        </li>
        <li>
          <strong>Nothing else.</strong> There are no accounts, no sign-in, no advertising,
          no analytics or tracking SDKs, and no contact, location, or device identifiers
          collected by the app.
        </li>
      </ul>

      <h2>How the audio is used</h2>
      <p>
        The clip is sent over an encrypted (HTTPS) connection to the Carnatify server, which
        extracts the melody, compares it with the ragas the model knows, and returns a ranked
        list of possible ragas. The audio file is deleted from the server as soon as that
        analysis finishes, whether it succeeds or fails. The raga suggestion is not stored
        on the server, and the recording is not used to train models.
      </p>
      <p>
        On your iPhone, the recording is kept in temporary storage only while it is being
        sent and is removed afterwards.
      </p>

      <h2>Who processes it</h2>
      <p>
        The Carnatify server runs on <a href="https://huggingface.co/privacy">Hugging Face</a>{" "}
        Spaces. Like any web host, Hugging Face may keep standard request logs (such as IP
        address and time of request) for security and operations, under its own privacy
        policy. We do not sell or share your data with anyone else.
      </p>

      <h2>Children</h2>
      <p>
        Carnatify does not knowingly collect personal information from anyone, including
        children. The only input is audio of music, and it is not retained.
      </p>

      <h2>Your choices</h2>
      <p>
        You can turn off microphone access at any time in Settings → Privacy &amp; Security →
        Microphone. Because we do not keep recordings or create accounts, there is nothing
        stored about you to view or delete.
      </p>

      <h2>Changes and contact</h2>
      <p>
        If this policy changes, the date at the top of the page will change too. Questions:{" "}
        <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>.
      </p>
    </LegalPage>
  );
}
