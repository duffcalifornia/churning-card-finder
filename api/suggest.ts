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
export const config = { runtime: "edge" };

const REPO = "duffcalifornia/churning-card-finder";
const MAX_SUMMARY = 200;
const MAX_DETAILS = 3000;

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
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
  return json(200, { ok: true });
}
