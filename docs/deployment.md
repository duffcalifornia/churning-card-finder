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

## Data refresh automation (already running, needs no hosting change)
`.github/workflows/check-rrv.yml` and `.github/workflows/refresh-offers.yml` run on GitHub Actions regardless of
where the site itself is hosted — they commit straight to this repo, and a redeploy on Vercel (or wherever) picks
up the new `data/*.json` on the next build. See `scripts/README.md` for what each one does.
