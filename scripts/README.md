# Card offer checker (maintainer tool)

> **AMEX IS PAUSED (2026-09-20).** Automated reads of americanexpress.com are currently being blocked. The tool
> skips Amex unless run with `--include-paused`. **Do not do that until the owner confirms access is working
> again.** See `docs/TODO.md` for what to do when revisiting.

Reads each tracked card's welcome offer and annual fee from the issuer's own public pages. Not part of the
website, and it never edits the catalog: you review the report and update the catalog by hand.

```
python3 scripts/card_offers.py --issuer chase
python3 scripts/card_offers.py --issuer amex --card platinum --json out.json --delay 3
python3 -m unittest discover -s scripts/tests -t scripts      # 194 tests, no network
```

Exit code 0 if every expected card was found, 2 if any could not be. (`refresh_offers.py`, the daily job, is gentler:
a card that is plainly gone does not fail it. See "When a card cannot be found" below.)

## Turning offers into numbers
`python3 scripts/parse_offers.py` (no network) reads `cardfinder/last_known_offers.json` and writes `data/parsed-offers.json`
(validated by `data/schema/parsed-offer.schema.json`) and `docs/parsed-offers-review.md`. The rules for what counts as a bonus are in
`cardfinder/parse.py`. Rows the parser is unsure about are marked `needsReview`.

## How it stays defensive
- **Finding a card:** known URL, then URL variants (trailing slash, `/28810/`), then the issuer's sitemap (including
  sitemap indexes), then links on listing pages. A page is accepted only if its title or heading really is that card
  (siblings like Disney Premier or Hilton Surpass are rejected). A card that cannot be found is reported with every
  attempt.
- **Reading a card:** offers come from several patterns tried in order; the one that worked is recorded. Issuers whose
  offers appear only after scripts run (Amex) use a headless browser (Playwright, optional). Raw HTML for those pages
  is never trusted for the offer. If the default page hides its offer, variant pages are tried.
- **Fees:** the earliest fee that belongs to this card. Employee, additional and authorized-user fees are skipped, and
  where pages list other cards' fees (Amex) a fee must follow this card's own name. A fee that differs from the last
  known one (`cardfinder/last_known_fees.json`) is flagged.
- **Completing a headline:** if only a headline offer is readable (BoA: "25,000 online bonus points offer"), the
  card's Terms & Conditions link is followed to find the spend requirement.
- **Last resort:** when a card's live page cannot be read (block, error), its last successfully read offer
  (`cardfinder/last_known_offers.json`) is shown, flagged `offer_from_last_known` and dated. A live offer always wins.
- **Sanity checks:** two cards resolving to the same page are both flagged `same_page_as_another_card`; a fee that
  differs from the last known one is flagged `fee_changed`.
- **Being polite:** a pause between requests, retries with backoff only for transient errors, and a circuit breaker:
  after 3 error or block pages in a row from one issuer it stops and reports the rest as not checked.

## When a card cannot be found
The daily refresh (`.github/workflows/refresh-offers.yml`) does not fail because a card has vanished from its issuer's
site. If every page it tried for a card was a 404 or the wrong page, the card keeps its last known data, and
`report_missing_cards.py` opens a GitHub issue ("Card not found: ...", label `card-missing`) with what was tried. Reply
to that issue, from the GitHub mobile app if you like:

- `/discontinued`: the card can no longer be applied for. `card-status.yml` adds it to
  `cardfinder/discontinued_cards.json`, drops its cached offer and fee, rebuilds `data/`, adds the changelog line
  "Removed the following card(s) because they can no longer be applied for: ...", runs the tests, commits, and closes the issue.
- `/still-active`: it can still be applied for. The issue is labelled `still-active` and closed, and the same card is not
  raised again for 30 days.

Only replies from someone with write access count, and the reply must start with the command. An open issue is closed
automatically if the card is found again. The job **still fails** (and comments on issue 1) when a card could not be
*read* (a page errored or refused us, which is what a block looks like) or 4 or more cards from one issuer go missing in
one run, since that looks like a redesign or a block rather than retirements. To retire a card by hand, add it to
`discontinued_cards.json` (or `NOT_TRACKED` in `registry.py`) and run `parse_offers.py` and `build_cards.py`.
The logic is in `cardfinder/missing.py` and `cardfinder/status.py`; both workflows share a `data-writes` concurrency
group so they never push at the same time.

## When the scraper finds a card we do not track
The same daily run also looks for cards an issuer sells that are not in the registry (`cardfinder/newcards.py`). It needs
no list of card URLs and no per-issuer patterns: a link on the issuer's listing pages or sitemap is a *candidate* if it
looks like the URLs of cards already tracked (same host, same top folder, same depth, same `.html`-or-not style) and is not
a known, discontinued, ignored or recently rejected page. Each candidate page is fetched and must read like one card's own
page: a singular "Card" in its heading (category pages say "Cards" or "Offers"), a card we do not already have, and a
readable annual fee. At most 8 pages per issuer per run are fetched, and a page judged "not a card" is not re-checked for
30 days (`cardfinder/candidate_rejects.json`). An issuer that served error pages, or was cut off by the circuit breaker, is
not scanned that day. Amex stays untouched while paused.

Nothing is added to the site automatically. `report_new_cards.py` opens one issue per candidate ("New card found: X", label
`card-new`, at most 5 per run) showing the offer and fee it read and what the site would count. Reply, from the GitHub mobile
app if you like:

- `/track`: start tracking it. Optional: `kind=business`, `name="Exact Name"`, `currency=<id>`. It is added to
  `cardfinder/tracked_cards.json`, its offer and fee are seeded from what was read (so it shows on the site complete
  right away), the changelog line "Added the following card(s): ..." is added, the tests run, the change is committed, and
  the issue closes. A card whose offer is paid in points must be given a currency (the ids are listed in the issue);
  a card paying free night awards cannot be tracked from a reply yet. Family, lifetime and cooldown rules still have to be
  added by hand.
- `/ignore`: never raise this page again (`cardfinder/ignored_cards.json`), for retail store cards and the like.

What it cannot do: judge rules, and it only sees cards linked from the pages and sitemaps it reads (a card that is not
linked anywhere public, like the Barclays Hawaiian Airlines card, still has to be added by hand).
To try it without the network, use `python3 scripts/refresh_offers.py --issuer usbank --new-cards-file /tmp/new.json` on a
copy of the repo (a real run writes the cache files), then `python3 scripts/report_new_cards.py /tmp/new.json --dry-run`
(needs the `gh` CLI signed in).

## Hotel card pages
IHG, Hilton and Marriott each publish a page listing their co-branded cards, with offers that can differ from the
issuer's own page (one side gets a new offer first). `cardfinder/hotels.py` reads those three pages
(`HOTEL_SITES`: ihg.com/onerewards/content/us/en/creditcard, hilton.com/en/hilton-honors/credit-cards,
marriott.com/credit-cards.mi) in the same daily run and keeps each card's reading in
`cardfinder/last_known_hotel_offers.json`. A card's offer is read from the stretch of page between its heading and the
next card's heading; only the offer sentence and its "Offer ends" date are kept, because these pages do not mark where an
offer stops and what follows is ongoing benefits.

`cardfinder/choose.py` then picks, per card, the offer that is worth more by the site's own measure (points x
cents-per-point, plus cash, plus free night certificates; the annual fee is the same on both pages so it cancels). Before
comparing values, an offer whose own text says it has ended ("Offer ends 9/30/26") is dropped, and so is one last read more
than 7 days ago when the other is fresh (Amex is paused, so its cached offers age while the hotel pages stay current). A tie,
or an offer that cannot be valued, goes to the issuer. The annual fee always comes from the issuer's page. A hotel-sourced
offer is marked `offerSource: "hotel"` with its `offerSourceUrl` in `data/parsed-offers.json`; `parse_offers.py` and the
daily refresh both apply the choice, so the changelog logs a change however it came about.

These sites sit behind bot protection: plain HTTP gets a 403, and so does Playwright's default headless build. They are
fetched with an ordinary Chrome user agent in Chromium's "new" headless mode (`channel="chromium"`), which needs nothing
beyond the `playwright install chromium` the workflow already does. A hotel page that cannot be read (blocked, redesigned,
a card heading changed) never fails the run: its cards keep the issuer's offer and the log carries a `::warning::` line.
GitHub's runner IPs are a different profile from a home connection, so watch the first few scheduled runs for those warnings.

## Flags in the report
`url_changed` `needs_render` `render_failed` `page_error` `no_offer_found` `no_fee_found` `fee_changed`
`offer_is_ceiling` ("as high as", a maximum) `check_struck_through` (old and new figures both on the page)
`offer_may_be_partial` `offer_from_variant` `offer_from_rendered` `offer_from_terms_page` `offer_from_last_known`
`same_page_as_another_card`

## Known limits
- Public pages show public offers, not elevated or targeted ones.
- Amex began returning "Loading Error" pages to automated visits after heavy use on 2026-09-20. Use a larger
  `--delay`, run it rarely, and check the report for `page_error`.
- All ten issuers are configured in `cardfinder/registry.py`. Cards the site owner said not to track are kept with
  `expected=False` and a reason (`NOT_TRACKED`).

## Watching Frequent Miler's valuations for changes
`python3 scripts/check_rrv.py` (one polite request) checks whether
[Frequent Miler's Reasonable Redemption Values page](https://frequentmiler.com/reasonable-redemption-values-rrvs/)
— the source for `data/valuations.json` — has moved since it was last saved, using the article's `dateModified` and a
hash of its tables' text; either one differing counts as changed. State lives in `cardfinder/rrv_check_state.json`.

Exit codes, meant for a daily cron job: `0` nothing needs attention, `1` the page changed (compare it to
`data/valuations.json` by hand, then rerun with `--ack` to accept the new baseline), `2` the page could not be read
(never reported as "unchanged"). See the script's own `--help` for a sample crontab line.

`--ack` also diffs `data/valuations.json`'s current values against `cardfinder/last_known_values.json` (a snapshot
of them as of the last ack) and, for whichever points programs actually changed cents-per-point, adds one line to
`CHANGELOG.md`: "Updated the rankings to reflect changes to the value of X." (site owner's rule, 2026-09-22). This
only fires from a real edit you already made to `valuations.json` before running `--ack` — the check itself never
parses or guesses values off the RRV page, only whether the page looks different at all.

## Refreshing offers automatically
`scripts/refresh_offers.py` is what actually keeps the site's data current: it runs the same checker as
`card_offers.py`, folds successful reads into `cardfinder/last_known_offers.json`, `last_known_fees.json` and
`last_known_fee_waived.json`, and then rebuilds `data/parsed-offers.json` and `data/cards.json` from them (as
separate processes — see the comment in the script for why an in-process rebuild silently used stale data the
first time this was built). A card that could not be read this run keeps its last known value; nothing is
guessed. Amex is skipped by default, same as `card_offers.py`.

Any card whose offer text actually changed this run gets one line in `CHANGELOG.md`: "Updated the bonus offer for
the following card(s): X." A card whose offer text was unchanged but whose annual fee (amount, or newly waived the
first year) changed gets its own line instead: "Updated the net value rankings to reflect changes to the annual fee
on the following card: X." (deliberately singular "card" even for more than one, per the owner). Both are the
owner's rule, 2026-09-22, for consistent changelog entries once the site is past its initial development phase, and
both can fire for the same card in the same run if it genuinely had both kinds of change. A run where nothing
changed adds nothing.

```
python3 scripts/refresh_offers.py                       # full run, all non-paused issuers, writes and rebuilds
python3 scripts/refresh_offers.py --dry-run --delay 3     # check and report only, writes nothing
```

`.github/workflows/refresh-offers.yml` runs it once a day on GitHub Actions: it commits the refreshed files when
something changed, and fails the job (so GitHub notifies whoever watches the repo, same as the RRV check below)
when a genuinely tracked card could not be read — which is also what an issuer's circuit breaker tripping (a
likely block) looks like. One bad card does not hold back the rest: everything that did read successfully is
still committed. It can also be triggered manually from the Actions tab at any time — worth knowing if you
suspect an issuer is giving you trouble and want to check without waiting for the schedule, or with a longer
`delay` — and its `include_paused` input can re-check Amex by hand, but only once you've actually confirmed the
earlier block has cleared; the schedule itself never touches Amex.

**A real risk worth knowing about:** this runs from GitHub's shared runner IPs, which carries a different
detection profile than your own connection would. Watch the first several scheduled runs, and if an issuer starts
erroring or circuit-breaking repeatedly, pause it in `cardfinder/registry.py` (`IssuerConfig.paused`) the same way
Amex is paused now, rather than letting the daily job keep hammering it.

`.github/workflows/check-rrv.yml` runs the RRV checker above once a day too: it commits the updated baseline when
there's nothing to flag, and fails the job when the page changed or couldn't be read. Re-run it by hand with the
`ack` input set to `true` once you've compared a change to `data/valuations.json`.
