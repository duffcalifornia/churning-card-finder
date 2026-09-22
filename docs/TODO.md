# Revisit later

## Amex (paused 2026-09-20)
**Why:** after heavy automated use (well over 100 requests in one session, many through a headless browser), Amex
started returning "Loading Error" pages and now refuses this IP address; the site owner cannot load americanexpress.com
in a normal browser either. Reported by the owner, not verified by us.

**Do not** request any Amex page until the owner confirms they can load americanexpress.com normally again.

**When revisiting:**
1. Confirm with the owner that the block has cleared.
2. Run in small batches, one at a time, with a long delay, and stop at the first error page:
   `python3 scripts/card_offers.py --issuer amex --include-paused --card platinum --delay 8`
3. Budget: about 25 pages in total, spread over days, not one sitting.
4. Do not use the browser pane or a headless browser more than necessary.

**What is stale until then:** every Amex offer in `docs/amex-offers-snapshot.md` and `cardfinder/last_known_offers.json`
(read 2026-09-20 before the block). Amex offers are personalized; "as high as" figures are ceilings; the Marriott Bevy and
Brilliant offers ended 9/30/26 and should be treated as expired until a live read confirms them.

**Ideas that do not work (tested 2026-09-20):**
- Terms and offer-details pages: the real ones sit under `/apply/`, which robots.txt disallows; the one non-`/apply/`
  terms page returns an error placeholder.
- The card pages' plain HTML: offer figures are filled in by scripts, and raw data holds stale marketing numbers.

## Other open items
- Confirm with the owner: which cards with no offer really have none (Bank of America Royal ONE, Royal ONE Plus, BankAmericard,
  secured and business secured cards; U.S. Bank Smartly, Shield, Business Shield, Amazon Business, secured cards).
- Cards the owner thinks are still missing ("there may be more").

## Offer parser: open items (2026-09-20)
- Struck-through "old new" pairs: the parser uses the second number and flags the row. Confirmed for the two Chase business cards;
  still an assumption for the three Delta business cards and Wells Fargo Choice Privileges.
- Wells Fargo Attune and Business Elite: pages never found. Their offers are recorded as *unknown*, not "none". Need a URL or "discontinued".
- Chase Freedom Flex/Unlimited and Ink Cash/Unlimited advertise cash but pay Ultimate Rewards; the parser reports the cash figure and the catalog
  step must convert it (`displayedAsCash`).
- Amex offers are from before the block and are ceilings ("as high as") in several cases.

## Valuation and currency items (2026-09-20)
- Cards that cannot be value-ranked until you give a value: Barclays Breeze, Carnival, Emirates Skywards (two cards); BoA Allways Rewards
  (Allegiant) and Norwegian Cruise Line. Frequent Miler has no value for those currencies.
- Assumed, not yet confirmed: Hilton "Free Night Reward" is valued at Frequent Miler's Hilton certificate ($521); the Marriott Business free night
  at the 50K Marriott certificate ($274).
- Assumed for Wells Fargo Rewards (not stated): cash-back redemption available, no household pooling. Bilt is kept for completeness only.
- BoA and U.S. Bank points are valued at Frequent Miler's "most other bank points" rate, 1.0 cent (`default-bank-points`).

## Resolved (2026-09-20, from the site owner)
- Amex Blue Cash Everyday, Delta SkyMiles Blue, Hilton Honors (personal): $0 annual fee.
- U.S. Bank Split Card: discontinued. FlexPerks Gold: never existed.
- U.S. Bank Business Altitude Connect: $0 the first year, then $95. Business Altitude Power: $195, not waived.
- U.S. Bank Business Leverage: the bonus is worth $600 as a deposit to a U.S. Bank account. Altitude Connect and Go share the same bonus.
- Chase World of Hyatt (2026-09-20): resolved. The 70,000 offer is the Hyatt *Business* card; /travel-credit-cards/world-of-hyatt is a brand landing page for both cards.

## Marriott matrix
- Done 2026-09-21: `data/marriott-matrix.json` (schema `data/schema/marriott-matrix.schema.json`), from https://frequentmiler.com/marriott-card-eligible/ (updated 2026-05-14). Matches Section H cell for cell; owner confirmed. Engine still needs the lookup (needs an optional "bonus received" month per Marriott card in the history input).

## Amex refresh (2026-09-21)
- Re-read 24 Amex cards from their public product pages in three batches of 5 to 7 (15 second delay, 5 minute gap between batches, one card per run, stopping at the first error page). No error pages in the batches. An earlier all-at-once run got error pages after 8 cards, so keep this pace.
- Skipped by design: Cash Magnet and Everyday Preferred (discontinued), both Amazon Business cards (no live page).
- `parse_offers.py` marks a paused issuer's offers stale only if they were read before 2026-09-21 (`stale_since`). Amex stays paused for crawling: use `--include-paused`, and go slowly.
- Still open: the three Delta Business struck-through pairs (90k / 100k / 200k, second number assumed current; flagged for review in `data/parsed-offers.json`). Delta Gold and Delta Platinum also show a limited-time general statement credit ($250, $300; offer ends 11/4/2026), counted as cash.

## Card catalog (data/cards.json, built 2026-09-21)
- Built by `python3 scripts/build_cards.py` from the registry, parsed offers, currencies, Section J and K rules and the Marriott matrix. Tests in `scripts/tests/test_catalog.py` (the file on disk must match a fresh build).
- 170 cards: 121 value-ranked, 9 unranked (the six without a valuation, plus the three Discover cashback-match cards), 40 history-only (no welcome offer, or named only by a rule).
- Amex charge card list confirmed by the owner 2026-09-21. `firstYearFeeWaived` is set on 10 cards (Amex, Citi AA, US Bank, United Explorer); the owner confirmed on 2026-09-21 that these are the only cards with a waived first year, so the rest are correctly false.
- Amex "as high as" ceilings rank at their ceiling value (owner accepted, 2026-09-21); the results add one non-ceiling backup card per ceiling card shown (see questionnaire-design.md and engine-contract.md). The Ranking Methodology page must say ceilings are maximums.
- `rank` (flowchart list positions) is not filled: Section C is waiting on the owner's current-card research.

## Engine status (2026-09-21)
- Built and tested (TypeScript, `npm test`): computeDerived, unlockStatus, hardExclusion (four rule groups), nllBlock, netValue, recommend. 201 tests.
- recommend uses value ranking alone. Top 5 per player, NLL cards inline, one backup per "as high as" card (best-ranked card below the cutoff that is not a ceiling and not NLL-only), combined across players and ranked by value (a shared card at the highest value any player gets from it), Best Personal Cards (top 3) for players who want to stay under 5/24 at 4/24 or more.
- Not modelled, banner only: rules with windows shorter than the buckets (Amex 2/90 and 1/5, Chase 2/30, Citi 8/65, BoA 2/3/4). Authorized users are ignored entirely.
- Open: flowchart-list ranking (Section C research), the questionnaire UI, results page, Ranking Methodology page, changelog, suggest-a-change function.
- To confirm with the owner: a player who wants both travel and cash back with no unlocker still sees the lesser UR cards as cash back cards (built that way, confirmed 2026-09-21). Aeroplan's extra tier is counted for every shown card, as designed.

## Site (Vite + React + TypeScript, started 2026-09-21)
- Run with `npm run dev` (port 5173); `npm run build` makes a static site in `dist/` (about 89 kB gzipped JS). Tests: `npm test` (230) and the Python suite.
- Built: player count, card history (issuer sections, counts per window, Marriott extras, live X/24 and Amex counters, "no cards" shortcut, "other cards" lines), about-you questions (shutdowns, AA ban, business, under 5/24, BoA deposit account, Amex business checking only if a Business Platinum is held), household questions, results (banner, credit blurb, combined list, backups, "up to" note, Best Personal Cards, Bilt blurb). Answers persist in localStorage only.
- Not yet built: Ranking Methodology page, changelog page, suggest-a-change form and its serverless function, "more info" per card, print/share of results, a shareable link, accessibility audit, mobile visual pass, hosting choice.
- Preview: added a "churning-card-finder" entry to ~/.claude/launch.json (the preview tool reads that file).

## Spending step and history layout changes (2026-09-21)
- Blank annual fee = no limit (null). The fee limit counts a waived first-year fee as $0 (owner correction, 2026-09-21); ranking uses the first-year fee too (owner, 2026-09-21).
- New "programs to target" list; engine ranks targeted cards first (src/engine/targets.ts). Excluding and targeting are mutually exclusive.
- History table: "Hold now", "Approved ..." headings, open issuer pinned with sticky headings.
- A browser that already has a saved profile keeps its old values; "Start over" resets. New visitors start with a blank fee limit, $3,000 / $6,000 spend and $0 extra.
- Phone pass (375px) done 2026-09-21: the history table becomes a labelled row per card; no page scrolls sideways. Not yet checked: tablet width, keyboard-only use, screen reader.
- Results page (2026-09-21): each card shows its welcome bonus (`src/ui/bonusText.ts`), bonus value and net value; a rank-by toggle (net default, raw) drives `recommend(..., { rankBy })`. Catalog now stores `welcomeBonus.freeNights`.
- Second-tier bonus offers phrased like the issuer's own wording ("Get A after spending B in C months, then get an additional X after spending Y more in Z months"), owner correction 2026-09-21. Parser also now recognizes the "if you spend a total of $X within Y, earn Z" phrasing (`_SECOND_TIER_TOTAL` in scripts/cardfinder/parse.py), and marks that tier's spend as cumulative from account opening (not additional) via a note on the Tier, though nothing reads that note yet.

## Ink LLC workaround question (2026-09-22)
- New per-player yes/no, shown only if the player has ever held an Ink card: "You've had a Chase Ink business card before... would you be willing to form an LLC to apply again: AZ, CO, HI, IA, ID, MI, MN, MO, MS, MT, NM, OH, PA, WI, or UT?" (`Player.willingToFormLlcForInk`, `src/ui/QuestionsStep.tsx`).
- A yes lifts Chase's Ink lifetime block (hardExclusion.ts) for every Ink card for that player, not just the one they held. It does not affect Sapphire/Sapphire Business or Citi Strata lifetime rules, or any other rule. Engine only stores the single boolean (residency and willingness folded into one answer); it does not ask which state.
- Verified with engine unit tests (bonusEligibility.test.ts) in both directions, and in the browser that the question appears/disappears correctly and the answer persists. The specific card didn't rank high enough to appear in the demo's visible list in this manual check, which is expected (not a defect) given synthetic test-run parameters.

## RRV watcher (2026-09-22)
- `scripts/check_rrv.py` + `scripts/cardfinder/rrv_check.py` (test-first, 14 tests): checks Frequent Miler's RRV page once per run via `dateModified` (JSON-LD) and a hash of the page's table text; either differing is "changed". State in `scripts/cardfinder/rrv_check_state.json` (gitignored-worthy, but currently just a plain file like the other `last_known_*.json` state files). Baseline saved 2026-09-21 from the live page (dateModified 2026-09-02).
- Exit codes for cron: 0 fine, 1 changed (needs a manual compare against data/valuations.json, then `--ack`), 2 page unreadable (never silently treated as unchanged).
- Not yet done: actually scheduling it daily. Options: a real crontab entry on the owner's machine (sample line in the script's docstring), or Claude Code's own Scheduled Tasks feature if the owner wants Claude to run and report it instead.

## Methodology page and RRV automation (2026-09-22)
- `src/ui/MethodologyPage.tsx`, reachable at `#methodology` (plain hash routing in App.tsx, no router dependency added; linked from the footer of every wizard step). Structure: plain-language summary, how a bonus is valued, what's checked/not checked, a collapsed `<details>` "eligibility rules this site does check" (owner: keep it collapsed so newcomers can skip it), known simplifications, a "data freshness" line, credits.
- "Data freshness" shows two dates: the oldest `verifiedOn` among cards actually shown in the ranking (`oldestVerifiedOn` in `src/ui/staleness.ts`, honest-worst-case rather than newest), and `valuations.json`'s own `verifiedOn` for point values. `Card.verifiedOn` and `Valuations.verifiedOn` added to `src/engine/types.ts`.
- `.github/workflows/check-rrv.yml`: runs `scripts/check_rrv.py` daily via GitHub Actions once the repo is on GitHub; commits the baseline on success, fails the job (GitHub's own notification) when the page changed or was unreadable. `workflow_dispatch` with an `ack` input re-runs it with `--ack`.
- Deliberately did NOT set up automation for the issuer offer checker (`card_offers.py`): Amex is still paused after the earlier IP block, and this project's whole practice has been manual, slow, owner-approved runs. Automating that into an unattended daily job would risk repeating the block. Flagged to the owner; not done without an explicit yes.
- Not yet done: this repo is not a git repository yet, so the workflow file is scaffolding only — it needs `git init`, a GitHub remote, and a push before it actually runs. 8 tests added for staleness.ts (formatDate, oldestVerifiedOn); MethodologyPage itself has no component test yet (content-only, checked by hand in the browser).

## Daily offer refresh automation (2026-09-22)
- `scripts/refresh_offers.py` + `scripts/cardfinder/refresh.py` (test-first, 14 tests in test_refresh.py): runs the checker, merges successful reads into the three `last_known_*.json` cache files, then rebuilds `data/parsed-offers.json` and `data/cards.json` as separate subprocesses.
- `.github/workflows/refresh-offers.yml`: daily schedule + `workflow_dispatch` (delay, include_paused, dry_run inputs) so it stays manually triggerable, per the owner's explicit request — important if an issuer starts giving trouble and they want to check by hand rather than wait for the schedule. Fails the job (GitHub notification) when a tracked card can't be read, which doubles as the circuit-breaker/likely-block signal; successful reads still commit regardless.
- Two real bugs caught and fixed before this went anywhere near a daily schedule, both found by actually running the pipeline against one real card rather than trusting it from reading the code:
  1. `json.dump(..., sort_keys=True)` on the cache files alphabetized every entry's own fields (seen/text/full_text) on every write, turning a one-card update into a 100+ line diff across the whole file. Fixed by dropping sort_keys and relying on `merge_last_known` preserving each dict's existing order; regression-tested (`WriteCacheFilesPreservesOrder`).
  2. `import parse_offers; import build_cards` in the same process silently rebuilt from **stale** data: `cardfinder.registry` loads the cache files into module-level constants at import time, and refresh_offers.py had already imported it before writing the fresh files, so the in-process rebuild used the pre-write values (`cards.json`'s `verifiedOn` never actually moved). Fixed by running both as real subprocesses instead.
- Reused `card_offers.py`'s existing exit-code contract (0 = every expected card found, 2 = something wasn't) as the "does this need a look" signal, rather than inventing a new one.
- Flagged explicitly in scripts/README.md: automating this trades the caution that's kept this project un-blocked so far for daily freshness, on the owner's explicit call given the site's value depends on current offers. GitHub's shared runner IPs are plausibly a bigger bot-detection target than a residential IP, not a smaller one. Watch the first several scheduled runs; pause an issuer in registry.py the same way Amex already is if it starts erroring repeatedly.
- Not yet done: has not been run against issuers other than a single Chase card (politely, by hand, to verify the pipeline). The first real scheduled/full run will be the first time this touches all issuers at once.

## Failure notifications for the offer refresh (2026-09-22)
- Tracking issue https://github.com/duffcalifornia/churning-card-finder/issues/1 (owner is watching it automatically as its creator). refresh-offers.yml posts a comment there only when a run does not pass (exit code nonzero): the affected cards' NOT FOUND lines, any page_error flags, any circuit-breaker trip notes, and the summary line, plus a link to the full run log. Nothing is posted on a clean run, per the owner's explicit request ("if it doesn't pass, that is"). GitHub's own issue-comment notification email is what actually reaches the owner; no SMTP secret or third-party service needed.
- Verified the log-line extraction locally against synthetic mixed-outcome results (found/not_found/page_error/circuit-breaker) before committing, not just by reading the code.
- Open question raised by the owner, not yet resolved: whether a mature, paced daily job is actually safe against Amex specifically, given the block already happened once from a residential IP and a GitHub Actions job would come from a shared data-center IP instead, which bot-defense systems often weight independently of request rate. Proposed: one manual workflow_dispatch run with include_paused against Amex only, watched closely, before ever considering adding it to the schedule.

## Site restructure: Home, Cheat Sheet, Card Finder, Methodology (2026-09-22)
- Four top-level pages via plain hash routing (`""`, `#cheatsheet`, `#finder`, `#methodology`), generalized from the earlier methodology-only hack. The wizard (People/History/About/Spending/Results) now lives under `#finder`, with its own 5-step sub-nav unchanged.
- "Signup Offer Cheat Sheet" (`src/ui/CheatSheetPage.tsx` + `src/state/cheatSheetPresets.ts`): the classic 4-box flowchart (5/24 status x cashback/travel), but built by feeding four synthetic Profile presets into the *same* `recommend()` engine rather than the never-populated flowchart-list (`rank`) data — no new ranking logic needed. Each preset assumes no card history at all and effectively unlimited spend (a large finite number, not Infinity — spendCapacity's interpolation does real arithmetic and Infinity - Infinity is NaN), so the only things that vary are 5/24 status (simulated via 5 generic cards in the 12-24-month bucket specifically, so it trips Chase's 24-month rules without also tripping BoA's/US Bank's unrelated 12-month ones) and bonusTypes. Shows *every* eligible card (`perPlayer: Infinity`), not a top 5 — per the owner, this page is for people who already know their own real situation and want the full reference list to self-filter, not a curated recommendation.
- Real, expected consequence worth remembering: the "travel" columns show only true co-branded cards and the currency-*unlocking* cards themselves (Sapphire Preferred/Reserve, Ink Preferred, Strata Premier/Elite, Venture/Venture X) — never their lesser same-family siblings (Freedom Flex, Ink Cash), because the hypothetical persona holds no unlocker. Correct given "never had any of these cards," not a bug.
- Extracted `CardItem` and `RankBySelector` out of `ResultsStep.tsx` into their own files so the cheat sheet can reuse them.
- Home page (`src/ui/HomePage.tsx`): two cards, one per tool, explaining the difference (generic reference vs. personalized).
- 13 new tests for the presets module (`src/state/cheatSheetPresets.test.ts`), all engine-level (no UI test yet for CheatSheetPage/HomePage/App routing itself, consistent with how the wizard steps aren't directly unit tested either).
- Verified live: home page, cheat sheet at both the 4-column desktop layout and the 1-column-plus-dropdown mobile layout (860px breakpoint, wider than the 600px one used for the history table since four columns of full card detail need more room), dropdown switching, nav between all four pages including the inline "use the Card Finder" link. One false alarm during verification: clicking felt broken at a custom 1400px *emulated* viewport, traced to a coordinate-scaling artifact of that emulation, not a real bug — confirmed via a direct `window.location.hash` test and a clean click at normal viewport size.

## Changelog, Suggestions, and the unlisted referrals page (2026-09-22)
- `CHANGELOG.md` at the repo root, rendered on `#changelog` via `marked` (new dependency) from a build-time `?raw` import — no runtime fetch, safe to render with `dangerouslySetInnerHTML` since the source is maintainer-authored, never user input.
- `#suggestions`: a form that POSTs to `/api/suggest`, a Vercel Edge Function (`api/suggest.ts`, standard Web Request/Response APIs, not a Vercel-specific SDK) that creates a GitHub issue using a `GITHUB_TOKEN` environment variable — never in client code. Honeypot field (off-screen, `aria-hidden`, unreachable by tab) for basic spam resistance; honest limitation noted in the code: no persistent rate-limit store, so abuse protection beyond the honeypot relies on GitHub's own per-token API rate limit. `docs/deployment.md` covers hosting setup (Vercel assumed but not yet chosen for real; not yet deployed anywhere) and how to create a properly-scoped token; `.env.example` documents the variable name only. Typechecked standalone (Node types, no DOM) since it's outside the main app's tsconfig/runtime.
- `#referrals` ("Support this project"): not in the main nav, reachable only via the footer or a direct link; sets `<meta name="robots" content="noindex">` while active. Placeholder content only (no real referral URLs or BMAC link yet — owner to fill in `src/ui/ReferralsPage.tsx`). Deliberately has zero connection to the ranking engine, preserving the "no affiliate links" principle for the actual tool; this page is a separate, disclosed exception, not an influence on any ranking.
- Footer now links to both from every page.

## Mobile hamburger menu for site nav (2026-09-22)
- The site-level nav (`nav[aria-label="Site"]` in App.tsx) now collapses into a hamburger button below 700px, since it grew to six items with some long labels ("Signup Offer Cheat Sheet"). CSS scoped via the `nav[aria-label="Site"]` selector so the wizard's own step sub-nav (`nav[aria-label="Steps"]`, a different `<nav>`) is unaffected.
- New `navOpen` state in App.tsx; the dropdown opens/closes on the hamburger button and closes automatically on navigation (`goToPage` now also calls `setNavOpen(false)`).
- Fixed in the same pass: `ChangelogPage`/`CHANGELOG.md` had a duplicate top-level heading (`# Changelog` rendered as a second real `<h1>`, colliding with the site's own page `<h1>` and breaking the "every page has one `<h2>` title" pattern used elsewhere). Removed the line from `CHANGELOG.md`, added an explicit `<h2>Changelog</h2>` in the component. Caught live while verifying the hamburger menu, not a hamburger bug itself.
- Verified live at 375px mobile emulation: icon renders, dropdown opens showing all six items with the current page highlighted, closes correctly on navigating (tested via the open dropdown). Two false alarms during this verification, both coordinate-scaling artifacts of the emulated viewport (confirmed via direct JS clicks/hash checks, not real bugs): a ref-click on Card Finder appeared to do nothing at 1400px, and a ref-click on the hamburger button appeared not to toggle `aria-expanded` at 375px.
- `npx tsc --noEmit` clean, 296 TS tests / 14 files, 372 Python tests, `npm run build` succeeded.

## Bilt Palladium added, disclaimer removed (2026-09-21)
- `bilt-palladium` is now a tracked, ranked card (site owner, 2026-09-21): 50,000 points after $4,000 spend in 90 days, $495 annual fee (waiver not confirmed, assumed not waived). New `bilt` issuer in `registry.py` (no sitemap/listing page needed for one card); its URL for the scraper is `https://www.bilt.com/card/palladium`. Bilt Blue and Obsidian remain untracked.
- Offer text and fee were seeded by hand into `last_known_offers.json`/`last_known_fees.json` (owner-supplied, not yet independently read from the live page) so the card shows up immediately; the next scheduled `refresh-offers.yml` run will read the real page and correct these if they've drifted, the same as any other card.
- Currency valuation reused as-is: `data/valuations.json`'s existing `bilt: 1.55` (Frequent Miler cents-per-point, already present and matching the RRV snapshot) rather than the 1.5 figure mentioned verbally, since the site's own sourced data was already more precise and consistent with its own snapshot.
- Removed the unconditional "Bilt 2.0 is complex" note from the bottom of every Card Finder results page (`src/ui/ResultsStep.tsx`) and the unused `showBiltBlurb` schema field it was scaffolded for (`data/schema/results.schema.json`), per the owner's explicit instruction, rather than narrowing it to a per-card note. `docs/rule-audit.md` Section I updated to record the partial reversal (Palladium ranked normally now; Blue/Obsidian still note-only, though the note itself no longer exists anywhere until they're added).
- Verified: `data/cards.json` has the correct entry (currency `bilt`, $495 fee, 50k/$4k/3mo, value-ranked not unranked); full Python (372) and TS (296, after updating one hardcoded ranked-card-count assertion in `netValue.test.ts` from 121 to 122) suites pass; confirmed live in the Card Finder that the disclaimer paragraph is gone and Palladium is a normal ranked entry (net value ~$280, below the demo persona's visible top 8, which is expected given no card history and its comparatively high fee, not a bug).

## Real BMAC link, footer copy, hamburger position (2026-09-22)
- `BMAC_URL` set to the owner's real Buy Me a Coffee link (`buymeacoffee.com/duffcalifornia`), replacing the placeholder. `REFERRAL_LINKS` is still empty; the owner hasn't supplied any yet.
- Footer copy changed to the owner's exact wording: "If you want to support this project, you could use one of my referral links or buy me a coffee" (`src/App.tsx`), replacing the earlier "My referral links · Buy me a coffee" label pair.
- Hamburger button moved to the top-right corner of the site nav (was left-aligned, stacked above the dropdown) via `position: absolute; top: 0; right: 0` on `.hamburger` inside the existing 700px media query; the dropdown itself (`position: absolute; top: 100%`) is unaffected since it's relative to the nav container, not the button.
- Verified live at 375px: button renders top-right, dropdown still opens correctly beneath it with all six items. `npx tsc --noEmit` clean, 296 TS tests pass.
