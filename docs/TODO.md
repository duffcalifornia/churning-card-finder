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

## Hamburger menu re-anchored to the header (2026-09-22)
- Follow-up to the earlier top-right fix: the button itself was correctly top-right, but the *dropdown* was still opening below the whole header (title + tagline), because `<nav>` was a sibling of `<header>`, not a descendant, so it couldn't be positioned relative to it.
- `<nav aria-label="Site">` moved inside `<header>` (App.tsx), nested right after the hamburger button. `.steps` dropdown now positioned `absolute; top: 44px; right: 0` (44px = the button's own 36px height plus an 8px gap) instead of being anchored to nav's own top, so it drops straight down from the button regardless of tagline length.
- Verified live at 375px: dropdown now opens directly under the button, overlapping the title/tagline as expected for a proper dropdown rather than pushing content down; closes correctly on navigating to a page (confirmed via `window.location.hash` and `aria-expanded`). `npx tsc --noEmit` clean, 296 TS tests pass.

## Senior-FE site audit: perf, meta, Cheat Sheet overflow (2026-09-22)
Full pass across desktop (up to 1400px) and mobile (375px) widths, dark and light color schemes, every page, per the owner's request to evaluate the live site as a senior front-end developer would and optimize for performance. Console was clean (zero warnings/errors) on every page in both this and the earlier hamburger-menu pass; color contrast checked (muted text ~7.5:1, warn banner ~8.4:1, accent button ~5.9:1, all comfortably above WCAG AA); no horizontal overflow on any page at 375px, including the deepest state (an expanded issuer table in Card History). Bundle is a single 113 kB gzip JS + 2.3 kB gzip CSS with brotli compression already on and TTFB in single-digit ms on Vercel's edge — page-level code splitting was considered and skipped: at this size it would trade a real (if small) initial-load win for a worse page-to-page feel (a loading flicker switching to Cheat Sheet or Card Finder, which most visits actually use), a bad trade for this app's shape.

Fixed, all "glaring" per the owner's standing approval, verified against the full existing test suite (296 TS + 372 Python, unaffected as expected since these are all CSS/meta/config changes with no engine logic touched) plus live before/after browser checks in place of new component tests (this project's established pattern has always been engine-level unit tests plus manual browser verification, with no React component test infra; introducing one wasn't judged worth doing unprompted for this pass):
- **Cheat Sheet columns were unbounded**: the permissive buckets (e.g. "Under 5/24, travel") show every eligible card by design (owner, earlier instruction), which is up to 76 cards, producing a 23,700px-tall single column and a ~24,300px page at desktop widths. Fixed by giving `.cheatsheet-column .results` `max-height: 70vh; overflow-y: auto` — every card is still there and still shown, just scrollable in place under its own heading rather than stretching the whole page. Confirmed via `scrollHeight` that card counts (59/76/43/50) were unchanged before and after; page height dropped from ~24,300px to ~1,370px at 1400px width.
- **No cache headers on hashed build assets**: Vercel was serving `/assets/*.js`/`.css` (Vite's content-hashed, safe-to-cache-forever filenames) with `Cache-Control: public, max-age=0, must-revalidate`, meaning every repeat visit re-validated the whole bundle instead of using a fully cached copy. Added `vercel.json` with `Cache-Control: public, max-age=31536000, immutable` scoped to `/assets/*`; `index.html` itself is untouched by the rule and keeps revalidating, which is what lets it always point at the current hash after a deploy.
- **No favicon**: every page load 404'd on the browser's default favicon request. Added `public/favicon.svg`, a minimal card-shaped icon in the site's own accent blue (no new branding decision, just completing missing infrastructure).
- **No meta description or Open Graph/Twitter tags**: since this site's whole audience is Reddit, an unstyled link with no preview text is a real loss when it's shared there. Added `<meta name="description">` and `og:*`/`twitter:*` tags to `index.html`, reusing the site's own existing title and tagline copy verbatim rather than writing new marketing text.

Not changed, flagged rather than fixed unilaterally (nothing rose to "glaring," and none of it needs a decision before the next real pass): the Card History step's per-issuer card lists get similarly long for issuers with many cards (e.g. Chase's ~20), though it's mitigated already by the existing sticky-issuer-header pattern and is a one-time data-entry form rather than a repeatedly-scanned reference list, so it reads differently than the Cheat Sheet did.

## Visual refresh: implemented from an approved Design mockup (2026-09-22)
Owner approved a Design-canvas mockup (two artboards: Home desktop, refined result card) exploring a more polished look for the card-list-heavy pages, while explicitly asking to keep decisions like this one behind approval rather than making them unilaterally. Implemented for real, following the same pattern as every other change this session (existing test suite green throughout, plus live before/after browser verification in place of new component tests, since this project still has no React component test infra):
- New `issuerLabel()` helper (`src/state/profile.ts`, reusing `ISSUER_SECTIONS`) turns a card's raw issuer id ("capone") into its display name ("Capital One") for a badge; test added first (`profile.test.ts`) checking every real catalog issuer id resolves to a non-empty name and the schwab/morganstanley-fold-into-Amex case, both green before wiring it into any component.
- New `src/ui/icons.tsx`: small inline stroke-SVG icons (fee, min-spend clock, ceiling warning, cheat-sheet list, card-finder compass) — no icon font or image request added.
- `CardItem.tsx` rewritten: each result is now a `.resultcard` (bordered, elevated card with a numbered `.rankbadge`) instead of a plain numbered `<li>` with a bottom border. Card name gets an issuer badge; a backup entry gets a short "Backup for X" badge instead of a full sentence line, with the original explanatory clause moved to its `title` tooltip so the information isn't lost, just deprioritized visually (this was shown in the approved mockup). Net value is now bold and accent-colored, clearly senior to the muted bonus-value figure; the fee/min-spend facts row gets small icons; the "as high as" ceiling note is now a pill instead of a plain warning-colored paragraph. `CardItem` takes an optional `rank` (1-based) prop for the badge, threaded through from `ResultsStep.tsx` (both the main list and the Best Personal Cards sub-list) and `CheatSheetPage.tsx`.
- `HomePage.tsx`: each of the two cards gets a small icon in a tinted circle (list icon for Cheat Sheet, compass icon for Card Finder).
- `styles.css`: new `--accent-tint` and `--shadow` tokens (light and dark); bolder/tighter `h1`; `.homecard`/`.resultcard` get elevation (subtle box-shadow) and background distinct from the page; `.results` switched from a numbered `<ol>` with bottom-border items to a flex column of cards with real spacing.
- Deliberately not changed: still no webfont (kept the existing system-ui stack from the earlier perf pass — the whole improvement here is spacing/hierarchy/elevation/icons, not typography, so as not to undo that decision for a purely cosmetic reason); still no new colors beyond tints of the existing accent/warn palette.
- Verified live at desktop (1280px) and mobile (375px) widths, dark and light color schemes: Home, Card Finder results (top-ranked, tiered-offer, and backup-badge cases), and the Cheat Sheet's scrollable columns (confirming the new card style composes correctly with the max-height/overflow fix from the previous pass). `npx tsc --noEmit` clean, 298 TS tests (296 + 2 new `issuerLabel` tests) and 372 Python tests pass, production build succeeds (111.4 kB gzip JS, 2.66 kB gzip CSS — negligible size change from the icons and extra markup).

## Less "vibe coded" pass: Public Sans, underline nav, no home-card icons (2026-09-22)
Follow-up to the visual refresh pass: owner felt the site still read as generic/AI-generated and wanted a typeface with real character but no design-tool-cliche baggage (the first suggestion, Fraunces, was rejected for exactly that reason — it has become its own AI-generated-site tell). Went with Public Sans (USWDS's typeface, built for real federal digital services) for headings AND body, one family rather than a pairing. Owner approved via a Design-canvas mockup first, same process as the prior visual pass; explicitly asked to leave the existing blue accent/color scheme alone for now.
- `index.html`: added the Google Fonts `css2` link (preconnect + stylesheet) for Public Sans at weights 400/500/600/700/800, covering every weight actually used across the site's CSS.
- `styles.css`: `body`'s font stack now leads with `"Public Sans"` before the system-ui fallback chain (kept as the fallback for the brief unstyled-text window and as a safety net if the Google Fonts request ever fails). This reverses the earlier "no webfont" perf decision from the audit pass, but that was made with default-blue-and-system-font specifically in mind; the owner weighed the trade knowingly this time.
- Site-level nav (`nav[aria-label="Site"] .steps`/`.step`) restyled to underlined tabs on desktop (`@media (min-width: 701px)`): no fill, no border-radius, a 2px accent underline on the current tab. Deliberately scoped to desktop only — the mobile hamburger dropdown keeps the filled-pill treatment (an underline reads poorly in a vertical list), and the wizard's own step sub-nav (`nav[aria-label="Steps"]`, a different element) is untouched either way since the new rule only targets `nav[aria-label="Site"]`.
- Removed the icon circles next to the two Home page cards (`HomePage.tsx`); `ListIcon`/`CompassIcon` deleted from `src/ui/icons.tsx` since nothing else used them (the fee/clock/warning icons on result cards are untouched).
- Verified live at desktop (1280px) and mobile (375px), dark and light: font actually applies (`document.fonts.check`), home cards have no icons, desktop nav is underlined with the wizard sub-nav and mobile dropdown both confirmed still using pills. `npx tsc --noEmit` clean, 298 TS tests, 372 Python tests, production build succeeds (111.2 kB gzip JS, 2.72 kB gzip CSS — the font itself loads from Google's CDN, not our bundle).

## Automated, consistent changelog entries for offer and valuation changes (2026-09-22)
Site owner's rule: once the site is past its initial development phase, the daily offer refresh and RRV valuation
updates will be by far the most common changelog entries, so they need one fixed phrasing each, always, rather than
a one-off sentence per run:
- Offer changes: "Updated the bonus offer for the following card(s): [cards]."
- Valuation changes: "Updated the rankings to reflect changes to the value of [points programs]."

New `scripts/cardfinder/changelog.py` (test-first, 19 tests in `test_changelog.py`): pure functions —
`offer_change_entry`/`valuation_change_entry` (diff old vs new, `None` if nothing changed), `format_list` (Oxford
comma: "A", "A and B", "A, B, and C"), `currency_label` (a real display name for a valuations.json id, e.g.
`hilton-honors` -> "Hilton Honors"; ~35 known ones in `_KNOWN_CURRENCY_NAMES`, unmapped ids fall back to
title-casing rather than guessing or blocking — add a real name there if one shows up wrong), and
`prepend_changelog_entry` (adds a bullet under today's `## YYYY-MM-DD` heading in CHANGELOG.md, creating it at the
top if today doesn't have one yet, or appending to it if a second entry lands the same day).

Wired into the two places these changes actually happen:
- `scripts/refresh_offers.py`: after merging a run's results, diffs the old vs new `last_known_offers.json` text
  per card; any real change (including a card's first-ever successful read) gets logged with its real display
  name (`Card.names[0]` from the registry, not its id). 1 new integration test (`MainWritesTheChangelogTests` in
  `test_refresh.py`) runs `main()` end to end with the network call stubbed out, confirming the actual wiring, not
  just the pure diff function.
- `scripts/check_rrv.py --ack`: rrv_check.py itself only ever knew "the RRV *page* changed," never which
  currencies' values moved — it hashes the whole table, it doesn't parse individual numbers. So the changelog
  writing hooks into `--ack` instead, the existing moment where a human (owner or Claude) has already edited
  `data/valuations.json` by hand and is confirming the page's new state as the baseline: `--ack` now diffs the
  current `values` dict against a new snapshot file (`scripts/cardfinder/last_known_values.json`, seeded now with
  today's real values) and logs whichever currencies actually differ. 2 new integration tests
  (`AckWritesTheChangelogTests` in `test_rrv_check.py`), including one confirming a no-op ack (page looked
  different but the values didn't actually move) logs nothing.
- Both `.github/workflows/refresh-offers.yml` and `.github/workflows/check-rrv.yml` now include `CHANGELOG.md` (and
  `last_known_values.json` for the RRV workflow) in their "commit if changed" file lists, so an automated entry
  actually ships with the data change that produced it, in the same commit.

Deliberately out of scope, not invented beyond what the owner specified: a fee-only change (bonus text identical,
annual fee different) has no changelog rule of its own and is not currently logged automatically — flagged in case
a third consistent phrasing is wanted for that case too.

## A third changelog rule: fee-only changes (2026-09-22)
Follow-up to the offer/valuation changelog automation above. Owner added a third consistent phrasing for the case
those two didn't cover: a run where a card's bonus offer text is unchanged but its annual fee (the amount, or it
becoming waived the first year) changed, which still moves that card's net value ranking on its own.
- `scripts/cardfinder/changelog.py`: new `fee_change_entry(old_fees, new_fees, old_waived, new_waived, card_names)`
  (6 new tests, test-first). Phrasing: "Updated the net value rankings to reflect changes to the annual fee on the
  following card: X." — deliberately keeps "card" singular in the template regardless of how many cards are
  listed, per the owner's explicit call that this will be rare enough not to need "card(s)".
- `scripts/refresh_offers.py`: now checks both `offer_change_entry` and `fee_change_entry` every run and logs
  either, neither, or both — they're independent facts, so a card with both kinds of change in the same run gets
  both lines. 1 new integration test confirming a fee-only run does NOT produce a bonus-offer line.
- `scripts/README.md` and the `refresh-offers.yml` header comment updated to describe all three rules together.
- Full suite: 401 Python tests (298 TS unaffected, this is Python-only), all green.

## Card history: independent counts, dropped Synchrony/TD sections (2026-09-22)
Two real usability bugs the owner hit actually using the Card Finder:
- **Auto-linked counts.** `setCardCount` used to try to keep "current (held now) is at most the sum of the approval
  windows" as an invariant: raising "hold now" above the approved total silently wrote the difference into
  "approved under 12 months ago", and lowering an approval window below the current held count silently lowered
  "hold now" too. In practice this meant entering "I hold 1 of this card" auto-guessed "approved under 12 months
  ago", and correcting that guess afterward (e.g. entering the real, older approval window) left the wrong guess
  sitting in `lt12` instead of being replaced. Fixed by removing all cross-field logic: `current` and each of the
  four approval windows are now set completely independently, full stop — confirmed the engine (`computeDerived`)
  never assumed that invariant either, it already read both as separate facts, so this was a pure UI/data-entry
  bug with no engine-side fix needed. Rewrote the two tests in `profile.test.ts` that had pinned the old behavior
  (TDD: new tests written first, asserting no cross-field effect, then the implementation changed to match); added
  a third test for the reverse direction. `data/schema/profile.schema.json`'s `cardHistoryEntry` description no
  longer claims the old (now false) invariant.
- **Synchrony and TD Bank sections removed** from the Card History step (`ISSUER_SECTIONS` in `profile.ts`):
  neither has any specific tracked cards in the catalog, so their section only ever showed the free-entry "other
  cards" line anyway — no different from just using "Other issuers not listed" at the bottom of the step. Kept
  both issuer ids valid in the schema (`profile.schema.json`'s `issuerId` enum, `card.schema.json`'s issuer enum)
  for backward compatibility with anything already stored and in case either gets real cards later; only the
  History step's own UI section list changed.
- Verified live: entering "hold now" no longer auto-fills any approval window; entering an approval window (even
  after "hold now" was already set) never touches any other window or `current`. Full suite green: 299 TS tests
  (298 + 1 new), 401 Python tests (unaffected, Python-side wasn't touched), production build succeeds.

## Fixed a fieldset/legend rendering bug on long yes/no questions (2026-09-22)
The Ink LLC workaround question's box border rendered straight through its own wrapped text (visible on the About
You step) instead of enclosing it. Root cause: `YesNo` (in `QuestionsStep.tsx`) used a native `<fieldset><legend>`,
and a browser's native legend rendering only reserves border space for one line of it — fine for every other
yes/no question here (all short, single-line), but the Ink LLC question's label is six lines long, so the extra
wrapped lines rendered outside the space the fieldset border accounted for.
- Replaced with `<div role="group" aria-labelledby>` plus a normal `<p>` for the label (`React.useId()` for a
  stable id), styled in `styles.css` to look identical to the fieldset-based groups elsewhere on the site. A
  `role="group"` + `aria-labelledby` div is the standard accessible substitute for fieldset/legend and renders
  correctly at any label length, native box-model quirk avoided entirely.
- Scoped to just `YesNo`; the one other native `<fieldset><legend>` on this step (the "which issuers shut you
  down" checkbox group) has a short, single-line question and wasn't reported as broken, so it was left alone.
- Verified live: reproduced the original bug's exact question (gave the profile an Ink card via History, then
  viewed About You), confirmed the box now fully encloses all six lines. `npx tsc --noEmit` clean, 299 TS tests,
  401 Python tests (unaffected), production build succeeds.

## Reworded the Ink LLC question for clarity (2026-09-22)
Owner felt the question was oddly phrased for a yes/no (the yes/no ask was buried mid-paragraph, with the state
list folded into the same sentence). Reworded per the owner's exact text: the context sentence now ends at
"cheap.", followed on its own line by the actual yes/no question ("Do you live in one of the states in the below
list, and if so, would you be willing to form an LLC in order to allow you to apply for a new Ink card?"), then
the state list on a third line by itself (no "or" before the last one, matching the owner's exact list).
- `YesNo`'s `label` string now has two `\n`s to mark the three lines; `.yesno-label` in `styles.css` gained
  `white-space: pre-line` so those render as real line breaks (a `\n` in a plain HTML text node is otherwise
  collapsed to a space) — safe for every other yes/no question on this step too, since none of the others contain
  a `\n` and `pre-line` only changes how newlines and existing whitespace runs are handled, not normal wrapping.
- Verified live: the three lines render distinctly (confirmed via `get_page_text` and a screenshot), no change to
  any other yes/no question. `npx tsc --noEmit` clean, 299 TS tests, 401 Python tests, production build succeeds.

## Fixed the Spending step's number fields; six-month spend falls back to double (2026-09-22)
Two related owner reports: (1) the $3,000/$6,000/$0 starting figures were real pre-filled guesses, not
suggestions; (2) trying to change either one, the box "forced a zero in it that couldn't be deleted until
typing another digit" — a real controlled-input bug, not a misunderstanding.
- **Root cause of the stuck-zero bug**: `Money`'s `onChange` committed straight to the parent on every keystroke,
  including the transiently-empty state while clearing the box — for a non-`allowBlank` field that meant calling
  `onChange(0)` the instant it went blank, so the very next render snapped a literal "0" back into the box before
  the next keystroke could land. Fixed by giving `Money` its own local text state, only resynced from the parent
  `value` when that value changed for a reason other than this input's own last edit (an external reset, e.g.
  Start Over) — the standard fix for a controlled numeric input fighting the user's typing. Verified by dispatching
  real input events one keystroke at a time (clear, then type "7","5","0" separately) and confirming the field
  lands on exactly "750", not "0750" or stuck.
- **Suggestions, not pre-filled defaults**: `defaultProfile()` now starts `spend3Months`/`spend6Months` at 0 (was
  3000/6000); `Money` gained `hideZero` (displays a stored 0 as an empty box, reusing the same idea `Count.tsx`
  already uses for card counts) and `placeholder` (custom suggestion text, e.g. "3000", instead of the fixed
  "0"/"No limit"). The 6-month field's placeholder is now *dynamic* — double whatever is currently in the
  3-month field (or "6000" if that's still blank) — so the box itself shows the real number the fallback below
  would use. The last field (supplemental spend) deliberately keeps showing a literal starting "0", not blank
  (owner: "every question but the last"), since $0 extra spend is already a normal, real answer for most people,
  not a guess to be replaced — it only got the typing-bug fix, not the suggestion treatment.
- **The three-month answer is the one that must be real** (owner: "otherwise the tool won't work") — no new
  blocking validation was added (nothing currently gates the Next button on this step), but it now reads clearly
  as required (a hint under the question) and starts genuinely blank rather than silently pre-filled with a
  guessed 3000, so leaving it unanswered is obvious rather than quietly working with an arbitrary number.
- **Six-month spend, left blank, is assumed to be double the three-month answer** — implemented as a real
  computation in `spendCapacity()` (`householdFilters.ts`), not just a UI hint: a stored 0 for `spend6Months` is
  treated as "not entered" and computed as `spend3Months * 2`. Safe to reuse 0 as the "unset" sentinel here (rather
  than widening the type to `number | null` like `maxAnnualFee`) because a real 6-month total lower than the
  3-month total is never a sensible answer — spend only accumulates over time, so there's no legitimate case where
  a household's true answer is genuinely $0 once they've already spent something by month 3. 2 new tests
  (`householdFilters.test.ts`), TDD (written and confirmed red before the fallback was added).
- Verified live end to end: fresh profile shows blank suggestion-placeholder fields (except the last, which shows
  "0"); clearing and retyping any field works cleanly; the 6-month placeholder updates live as the 3-month value
  changes; "Start Over" correctly resets every field back to its blank/0 starting state. `npx tsc --noEmit` clean,
  301 TS tests (299 + 2 new), 401 Python tests (unaffected), production build succeeds.

## Spending fields now genuinely blank (null), matching the annual fee field (2026-09-22)
Follow-up correction to the previous pass: the "hideZero" trick (a real stored 0 displayed as an empty box) still
left the last field (supplemental spend) showing a literal, real "0" that had to be deleted, and the owner's own
returning browser still had its real pre-fix values (3000/6000) saved from earlier testing — `defaultProfile()`
only affects brand-new profiles, not an existing saved one. Owner's ask: all three spending fields should work
exactly like the annual fee field already does — genuinely blank until typed, placeholder only, and the moment
you type one digit, only that digit remains (standard placeholder behavior) — and if the 3000/6000 suggestions
stay, prefix them with "ex." so they read as examples, not values to delete.
- `Household.spend3Months`, `spend6Months`, and `supplementalSpend3Months` widened from `number` to `number | null`
  (matching `maxAnnualFee`'s existing type) in `engine/types.ts` and `data/schema/profile.schema.json`; only one
  real consumer needed updating (`spendCapacity` in `householdFilters.ts`, the sole place besides the UI that
  reads these fields — confirmed by grep), which now null-coalesces spend3Months/supplementalSpend3Months to 0 and
  still falls back spend6Months to double spend3Months when null (previously trigged by a stored 0; both now work
  the same way). `defaultProfile()` sets all three to `null`.
- `Money` (`HouseholdStep.tsx`) simplified back to a single blank/null behavior for every field (the `hideZero`
  prop is gone, no longer needed now that these fields are genuinely nullable) — kept the local-text-state fix
  from the previous pass (still necessary: without it, clearing the box to retype fights the user, this time via
  `onChange(null)` instead of `onChange(0)`). Placeholders: "ex. 3000" and a live-dynamic "ex. {2x the 3-month
  field}" (or "ex. 6000" while that's still blank) for the two spend fields, per the owner's exact wording; "0"
  for supplemental spend (no "ex." — the owner only asked for it on the two fields they said could keep numbers).
- Verified live on a fresh profile (`localStorage.clear()`): all four fields render genuinely blank with only
  their placeholder text showing; typing into the 3-month field replaces the placeholder with exactly what was
  typed and the 6-month field's placeholder updates live to double it. 3 new/updated tests in
  `householdFilters.test.ts` covering the null case for every field. `npx tsc --noEmit` clean, 303 TS tests
  (301 + 2 new), 401 Python tests (unaffected), production build succeeds.

## Fixed a severe bug: the NLL warning was invisible for single-player households (2026-09-22)
Owner report: holding an Amex Platinum and having previously had an Amex Gold, both cards showed up in the results
with no mention of needing a targeted "no lifetime language" (NLL) offer — including Gold, which should be
family-blocked by holding Platinum alone, even with no prior Gold history at all.

Root-caused by actually reproducing it rather than guessing: wrote a real-catalog test first (`recommend.test.ts`)
with a single-player profile holding `amex-platinum` and no `amex-gold` history at all, and confirmed the *engine*
already computed `viaNllOnly: true` correctly for both cards (`nllBlock.ts`'s lifetime and family logic, and the
underlying `data/cards.json` family/tier/`onceInLifetime` data, were all already right). The bug was entirely in
the UI: `CardItem.tsx`'s only NLL-related markup lived inside `{!single && ... && <div className="who">}` — so
for the overwhelmingly common single-player case, the entire block, NLL annotation included, was skipped, no
matter what the engine had already correctly flagged. A real, severe bug: churning has real financial/eligibility
consequences, and this was silently hiding exactly the information someone needs before applying.
- Decoupled the NLL warning from the player-name line entirely, and gave it real visual weight instead of a small
  parenthetical: a new `.nllnote` warning box (same treatment as the existing "as high as" ceiling warning),
  shown whenever any non-backup player on that entry needs NLL — single-player or multi-player, and (for
  multi-player) wording that adapts to whether it's everyone listed or only some of them by name.
- 1 new test (`recommend: real data`, `recommend.test.ts`) using the real catalog, confirming both the
  currently-held-card case (Platinum) and the family-rule-with-no-prior-history case (Gold) are flagged, run with
  `perPlayer: Infinity` since the default top-5 cutoff can otherwise hide a card from a synthetic test profile's
  view before this even gets checked.
- Verified live end to end, reproducing the owner's exact scenario (single player, Platinum held, Gold never
  held): the results page now shows a clear, prominent warning box on the Platinum entry the moment it renders.
  `npx tsc --noEmit` clean, 304 TS tests (303 + 1 new), 401 Python tests (unaffected), production build succeeds.

## NLL note: copy fix and a distinct, more urgent color (2026-09-22)
Two small owner follow-ups to the NLL warning just added:
- Copy: "...offer to earn it again" -> "...offer to earn this bonus." The family-rule case can trigger with no
  prior history on the card itself at all (e.g. Gold blocked purely by holding Platinum), so "again" was wrong
  there — "this bonus" is accurate either way.
- Color: previously shared the same amber as the "as high as" ceiling note. Owner's instinct (agreed): these are
  different severities — ceiling just means the real bonus might be a little lower than shown, still guaranteed;
  NLL means the player may not be able to earn the bonus at all without a specific targeted offer, a real risk of
  applying for nothing. Gave `.nllnote` its own `--danger-bg`/`--danger-fg` tokens (a red-orange, distinct from
  the ceiling note's amber in both themes) instead of reusing `--warn-*`; `.ceiling` unchanged. Contrast checked
  in both themes (6.3:1 light, 7.2:1 dark, both comfortably above WCAG AA).
- Verified live: copy and both colors confirmed via computed styles against the real catalog scenario from the
  previous fix. `npx tsc --noEmit` clean, 304 TS tests, 401 Python tests, production build succeeds.

## NLL note: distinct icon (2026-09-22)
Owner asked for the NLL note to use a different icon than the shared triangle warning — something like a
stylized exclamation point, to read as more "stop and read this" than a generic caution triangle. Added
`AlertIcon` (`icons.tsx`): a circled, filled exclamation mark, distinct in shape from `WarningIcon`'s triangle.
`.nllnote` now uses `AlertIcon`; `.ceiling` is untouched, still `WarningIcon`. Verified live (SVG markup checked
directly on the same real scenario from the earlier NLL fix) that the two notes now render visually distinct
icons. `npx tsc --noEmit` clean, 304 TS tests, 401 Python tests, production build succeeds.
