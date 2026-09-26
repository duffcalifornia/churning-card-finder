# Deployment

The site itself is fully static (Vite build output in `dist/`). The one exception is `api/suggest.ts`, a Vercel
Edge Function that turns the Suggest a Change form into a GitHub issue — everything else needs no server.

## Hosting: Vercel (assumed, not yet chosen for real)
Vercel was picked because it's the simplest pairing with a Vite static site plus one small function, on a free
tier. Not yet actually deployed anywhere. If you'd rather use Netlify or something else, the function needs to
move (Netlify's convention is `netlify/functions/*.ts` with a different request/response shape) — everything
else (the static build) is host-agnostic already.

To deploy on Vercel:
1. Connect the GitHub repo in the Vercel dashboard. It auto-detects the Vite build (`npm run build`, output
   `dist/`) and picks up `api/suggest.ts` as a function automatically.
2. Create a **fine-grained personal access token** at <https://github.com/settings/personal-access-tokens>,
   scoped to **only this repository**, with **Issues: read and write** permission and nothing else. Do this
   yourself in GitHub's UI — an assistant should never generate or handle this token for you.
3. In the Vercel project's Settings → Environment Variables, add `GITHUB_TOKEN` with that token's value. Never
   commit it, never put it in any file in this repo (see `.env.example`, which documents the variable name only).
4. Redeploy. The Suggest a Change form should now work; test it once before linking the site anywhere public.

### Optional: email notification for new suggestions

GitHub does not email a token's own owner about issues that token created — it suppresses notifications for your
own account's activity, even if you're watching the repo. So without this, the only way to notice a new
suggestion is to check the repo's Issues tab yourself. To also get a direct email:

1. Create a free account at <https://resend.com> and generate an API key.
2. In the Vercel project's Settings → Environment Variables, add:
   - `RESEND_API_KEY` — the key from step 1.
   - `SUGGESTION_NOTIFY_EMAIL` — the address you want notified.
   - `RESEND_FROM_EMAIL` (optional) — defaults to `onboarding@resend.dev`, Resend's shared test sender, which can
     only send to the email address you signed up to Resend with. To notify a different address, or once you're
     past testing, verify your own sending domain in Resend and set this to an address at that domain instead.
3. Redeploy. Both env vars must be set for email to fire; leaving either unset skips it silently and the GitHub
   issue is still created as before — the email is a best-effort extra, never a requirement for suggestions to work.

### Optional: referral links on the "Support this project" page

`src/ui/ReferralsPage.tsx` reads its referral URLs from Vite env vars rather than hardcoding them, so that
swapping a link out later never touches git history — see the comment in `.env.example` for why. To set or change
one:

1. In the Vercel project's Settings → Environment Variables, add or edit whichever of these you have a live link
   for: `VITE_REFERRAL_CHASE_SAPPHIRE`, `VITE_REFERRAL_CHASE_MARRIOTT`, `VITE_REFERRAL_CHASE_INK`,
   `VITE_REFERRAL_AMEX`. Leave any of them unset (or blank) to just not show that entry.
2. **Redeploy — this one matters more than usual.** Unlike `GITHUB_TOKEN` or the Resend vars (read by
   `api/suggest.ts` at request time), these are Vite env vars: baked into the built JS bundle at build time. A
   change here does nothing until the next build actually runs. They're also not secret from anyone visiting the
   live site — that's the whole point of a referral link — this is purely about keeping an old, swapped-out link
   from lingering in this repo's history.

## SEO: the cheat sheet's real URLs, and the sitemap

Every page except the Signup Offer Cheat Sheet is a hash on `/` (`/#finder`, `/#methodology`, ...) rather than a
real path — a hash fragment never reaches the server, so Google treats every one of those as the same URL as the
homepage. That's fine for pages nobody searches for by name, but the cheat sheet's four presets ("best cash back
card under 5/24", etc.) directly match how people actually phrase these searches, so those four get real,
independent paths instead: `/cheatsheet/under-cashback`, `/cheatsheet/under-travel`, `/cheatsheet/over-cashback`,
`/cheatsheet/over-travel` (bare `/cheatsheet` also works, defaulting to the first one). `vercel.json`'s `rewrites`
are what make a direct load or refresh of one of these work — without them, Vercel would 404 on a path with no
matching static file, since only `index.html` itself exists on disk; the client-side router in `src/App.tsx` reads
`window.location.pathname` and takes it from there. `public/sitemap.xml` lists these real URLs (plus the
homepage); it's a plain static file, hand-maintained, since this list of pages is small and doesn't change often -
if a genuinely new indexable page is ever added, update it by hand rather than trying to automate something this
small. `/referrals` is deliberately left out of both the sitemap and this real-URL treatment: it already sets its
own `noindex` meta tag, and no one should be searching for it anyway.

## Data refresh automation (already running, needs no hosting change)
`.github/workflows/check-rrv.yml` and `.github/workflows/refresh-offers.yml` run on GitHub Actions regardless of
where the site itself is hosted — they commit straight to this repo, and a redeploy on Vercel (or wherever) picks
up the new `data/*.json` on the next build. See `scripts/README.md` for what each one does.
