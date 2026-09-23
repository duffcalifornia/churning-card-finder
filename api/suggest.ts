// Vercel Edge Function: the only non-static piece of the site. Turns a "Suggest a change" form submission into a
// GitHub issue, using a token that only ever lives server-side (set as the GITHUB_TOKEN environment variable in
// the Vercel project's settings — never commit it, never put it in client-side code). See docs/deployment.md for
// how to create a token scoped to just this repo's Issues.
//
// Uses only the standard Request/Response Web APIs, not a Vercel-specific SDK, so it is not locked to Vercel.
//
// Honest limitation: this function is stateless per invocation, so there is no persistent request-rate limiting
// here beyond the honeypot field and GitHub's own API rate limit on the token (a real backstop, but not built for
// this specifically). A dedicated store (e.g. Upstash) would be needed for real abuse-rate limiting.
//
// GitHub never emails the token's own owner about issues that token created (it suppresses notifications for
// your own activity), so a suggestion landing as a GitHub issue is not enough to actually notify anyone. The
// RESEND_API_KEY + SUGGESTION_NOTIFY_EMAIL env vars below are optional: when both are set, a submission also
// sends a direct email via Resend (https://resend.com). See docs/deployment.md for setup. Best-effort only — an
// email failure never blocks the GitHub issue from being created, since that's the primary record of the suggestion.
export const config = { runtime: "edge" };

const REPO = "duffcalifornia/churning-card-finder";
const MAX_SUMMARY = 200;
const MAX_DETAILS = 3000;

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

async function notifyByEmail(summary: string, details: string, issueUrl: string): Promise<void> {
  const apiKey = process.env.RESEND_API_KEY;
  const to = process.env.SUGGESTION_NOTIFY_EMAIL;
  if (!apiKey || !to) return; // not configured; silently skip
  try {
    await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: process.env.RESEND_FROM_EMAIL || "onboarding@resend.dev",
        to,
        subject: `New site suggestion: ${summary}`,
        text: `${details ? details : "(no further detail given)"}\n\nGitHub issue: ${issueUrl}`,
      }),
    });
  } catch {
    // Best-effort notification only; the GitHub issue is the real record.
  }
}

export default async function handler(request: Request): Promise<Response> {
  if (request.method !== "POST") return json(405, { error: "POST only" });

  let body: { summary?: string; details?: string; website?: string };
  try {
    body = await request.json();
  } catch {
    return json(400, { error: "Invalid request body" });
  }

  // Honeypot: a real visitor never sees or fills this field (see SuggestionsPage.tsx). Report success to a bot
  // that filled it, rather than an error, so it does not learn to leave the field empty next time.
  if (body.website) return json(200, { ok: true });

  const summary = (body.summary ?? "").trim().slice(0, MAX_SUMMARY);
  const details = (body.details ?? "").trim().slice(0, MAX_DETAILS);
  if (!summary) return json(400, { error: "A one-sentence summary is required." });

  const token = process.env.GITHUB_TOKEN;
  if (!token) return json(500, { error: "The site is not configured to accept suggestions right now." });

  const issueBody = [
    "Submitted through the site's Suggest a Change form. Nothing else was collected — no name, email, or IP is stored by this app.",
    "",
    details ? details : "(no further detail given)",
  ].join("\n");

  const ghResponse = await fetch(`https://api.github.com/repos/${REPO}/issues`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "churning-card-finder-suggestions-form",
    },
    body: JSON.stringify({ title: summary, body: issueBody }),
  });

  if (!ghResponse.ok) return json(502, { error: "Could not create the issue. Try again in a moment." });

  const issue = await ghResponse.json().catch(() => null);
  await notifyByEmail(summary, details, issue?.html_url ?? `https://github.com/${REPO}/issues`);

  return json(200, { ok: true });
}
