import { useState } from "react";

const MAX_SUMMARY = 200;
const MAX_DETAILS = 3000;
const ISSUES_URL = "https://github.com/duffcalifornia/churning-card-finder/issues";

type Status = "idle" | "sending" | "sent" | "error";

export function SuggestionsPage() {
  const [summary, setSummary] = useState("");
  const [details, setDetails] = useState("");
  const [website, setWebsite] = useState(""); // honeypot: real visitors never see or fill this field
  const [status, setStatus] = useState<Status>("idle");
  const [errorText, setErrorText] = useState("");
  const [issueUrl, setIssueUrl] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!summary.trim()) return;
    setStatus("sending");
    setErrorText("");
    try {
      const res = await fetch("/api/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ summary: summary.trim(), details: details.trim(), website }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.error || `Request failed (${res.status})`);
      const data = await res.json().catch(() => null);
      setIssueUrl(data?.issueUrl ?? null);
      setStatus("sent");
      setSummary("");
      setDetails("");
    } catch (err) {
      setStatus("error");
      setErrorText(err instanceof Error ? err.message : String(err));
    }
  };

  if (status === "sent") {
    return (
      <section>
        <h2>Suggest a change</h2>
        <p>
          Thanks — that's been posted as an issue on the project's GitHub. You can check{" "}
          <a href={issueUrl ?? ISSUES_URL} target="_blank" rel="noreferrer">
            {issueUrl ? "your suggestion" : "the issues page"}
          </a>{" "}
          any time to see its status.
        </p>
        <button type="button" className="secondary" onClick={() => setStatus("idle")}>Suggest another</button>
      </section>
    );
  }

  return (
    <section>
      <h2>Suggest a change</h2>
      <p>
        Found a rule that's wrong, a card that's missing, or something you think should work differently? This
        creates an issue on the project's public GitHub repository with whatever you type below — nothing else is
        sent, and no account is needed. Please don't include your name, email, or any other personal information.
      </p>

      <form onSubmit={submit}>
        <label className="field">
          What's the suggestion, in a sentence?
          <input
            type="text"
            value={summary}
            maxLength={MAX_SUMMARY}
            required
            onChange={(e) => setSummary(e.target.value)}
          />
        </label>
        <label className="field">
          More detail (optional)
          <textarea
            value={details}
            maxLength={MAX_DETAILS}
            rows={6}
            onChange={(e) => setDetails(e.target.value)}
          />
        </label>

        {/* Honeypot: hidden from real visitors (off-screen, unreachable by tab, never announced to a screen
            reader), but a plain scripted bot filling every field on the page will fill this one too. */}
        <div aria-hidden="true" className="honeypot">
          <label>
            Website
            <input type="text" name="website" tabIndex={-1} autoComplete="off" value={website} onChange={(e) => setWebsite(e.target.value)} />
          </label>
        </div>

        {status === "error" && <p className="note" style={{ color: "var(--warn-fg)" }}>Something went wrong: {errorText}. Try again in a moment.</p>}

        <div className="buttons">
          <button type="submit" className="primary" disabled={status === "sending" || !summary.trim()}>
            {status === "sending" ? "Sending…" : "Send suggestion"}
          </button>
        </div>
      </form>
    </section>
  );
}
