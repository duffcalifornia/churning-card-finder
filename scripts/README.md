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

Exit code 0 if every expected card was found, 2 if any could not be.

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
