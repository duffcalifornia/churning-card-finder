# Questionnaire design

Status: draft v2 (2026-09-20). Decided items reflect user answers. Items marked OPEN are awaiting a decision.

## Principles
- The engine produces a **ranked list of cards per player**, not an optimal combination. The user decides which cards and how many to apply for.
- Bank-specific velocity rules the engine cannot see precisely are handled by a banner, not by code (see Results).
- No credit score question. A blurb replaces it (see Results).

## Flow
1. Number of players (numeric dropdown).
2. Card history, per player (moved up to second, per user proposal).
3. Per-player questions (one block per player).
4. "Applies globally" section (household level).
5. Results: one combined ranked list, with the players who can apply shown on each card.

Why card history goes second: it determines each player's X/24 and Amex-limit standing, so later questions can be worded for that player (for example the "under 5/24" question). Risk: the heaviest step comes early and could cause drop-off. Mitigations: issuer sections collapsed by default, live counters, and a "this player has no cards" shortcut.

## Card history (per player)
- Issuer sections, collapsible: Chase, Amex, Bank of America, Citi, US Bank, Wells Fargo, Bilt, Barclays, Capital One, Discover, FNBO, Synchrony, TD Bank, and "Other issuers not listed".
- "Other issuers not listed" (decided): personal cards only, and just two quantity fields: approved in the last 12 months, approved 12 to 24 months ago.
- Inside each listed issuer: every card a rule cares about, plus a generic "other [issuer] personal cards" line with just two free-form number boxes: approved in the last 12 months, approved 12 to 24 months ago (decided). Unlisted personal cards do not matter after 24 months; any that do matter for another reason must be named explicitly in the card list. No generic "other business card" lines (decided): the business cards that matter, including the Capital One and Discover ones that report to personal credit, are named explicitly in their issuer sections.
- Per card: "currently have" count. Any count above 0 auto-checks "ever had".
- Approval columns, each cell a count: <12 months ago, 12 to 24 months ago, 24 to 48 months ago, more than 48 months ago. The column heading reads "Approved (most cards) / received bonus (Southwest, Marriott)" (decided 2026-09-21): for Southwest and Marriott cards the count means the bonus date, for every other card the approval date. One set of columns serves both, and lifetime rules (Sapphire, Ink, Strata, Amex) read "ever approved" from any non-zero cell or a current card.
- **Over 5/24 rule (decided):** if the counts in the first two columns, summed over cards that report to personal credit (catalog flag `reportsToPersonal`, see A2 and A21), total 5 or more, the player is over 5/24. Live counters for X/24, Amex credit cards (of 5) and charge cards (of 10), Chase business cards open.
- **Marriott cards only:** two extra timeframe questions for the Section H matrix: held the card in the last 30 days, approved in the last 90 days. (The 24-month bonus test is now covered by the bonus-date columns above.) These windows are shorter than the buckets, so they need their own questions; without them the matrix's 30 and 90 day cells could only be shown as banners.
- Chase Ink cards: lifetime rule applies to sole proprietors (SSN or EIN); an LLC with its own EIN gets around it (K7). No per-card SSN/EIN question is needed. Built 2026-09-22 (owner supplied the state list and the desired behavior): one yes/no question per player, "You've had a Chase Ink business card before, which normally means you can't get that bonus again. You can get around this by applying through a newly formed LLC with its own EIN, but this only makes sense in a state where forming an LLC is free or cheap. If you live in one of these states, would you be willing to form an LLC to apply again: AZ, CO, HI, IA, ID, MI, MN, MO, MS, MT, NM, OH, PA, WI, or UT?" (`willingToFormLlcForInk`). Shown only if the player has ever had an Ink card (computeDerived's everHad set). A yes bypasses Chase's Ink lifetime block for every Ink card for that player (not just the one they held); it does not touch any other Chase lifetime card (Sapphire, Sapphire Business) or Citi Strata. Superseded the earlier plan of asking the player's exact state and showing a note only: the single yes/no does double duty (residency and willingness), since the engine only needs their conjunction and not which state.
- BoA: one yes/no per player, "Do you have an open Bank of America deposit account?" (K5). BoA cards are named individually so the 24-month held rule (K3) can read them. Dates on BoA cards are not asked (decided 2026-09-21): the 2/3/4 rule (K4) is not modelled, and the 24-month rule is approximated from the same buckets (a BoA card currently held or approved in the last 24 months blocks the same personal card; business cards do not warn).
- Consequence of coarse buckets: the engine cannot compute an exact "eligible again on" date. A card in the 12 to 24 month bucket will age off within 12 months, and results can say only that.

## Per-player questions
| Question | Type | Engine use |
|---|---|---|
| Has this player been shut down by any of: none, Chase, Amex, Citi, Wells Fargo, Barclays, Capital One, Discover, BoA, US Bank | multi-select | Removes all cards from those issuers for this player |
| Banned from earning AA miles | yes/no | Removes AA cards for this player. AA is the only program worth asking about for now (decided) |
| Comfortable applying for business cards | yes/no | Removes business cards and the business-spacer strategy |
| "Are you interested in trying to get under 5/24 (if over) or stay under 5/24 (if under)?" (wording decided: the two phrasings may be answered differently) | yes/no | If yes and the player is at 4/24 or above, show only business cards that do not report to personal credit (see edge cases) |

Dropped: credit score bracket, credit history length (decided; blurb instead).

### Edge cases for "stay under 5/24"
- "Business cards only" must exclude business cards that report to personal credit: Cap1 business cards other than Spark Cash Plus and Venture X Business (A21) and Discover business cards (A26).
- If the player also answered "not comfortable with business cards", the list is empty. Show a message explaining why and suggesting they change one answer.
- At 4/24 the next personal card takes the player to 5/24, so a Chase personal card is still technically approvable at 4/24. The rule hides it anyway (confirmed intent).

## Global questions
| Question | Type | Engine use |
|---|---|---|
| Highest annual fee you would pay on one card in its first year (blank = no limit) | number | Hard filter on the first-year fee: a waived first year counts as $0 |
| Spend all day-to-day non-housing expenses on one card for 3 months: how much | number | Capacity for minimum spend |
| Same, for 6 months | number | Capacity for 6-month windows |
| Realistic supplemental spend over 3 months | number | Adds to capacity |
| Bonus types wanted | multi-select: cashback, hotel points, airline miles | Chooses which card lists apply |
| Points or miles programs that should NOT be considered | multi-select from the transfer matrix programs | Hides cards that are only useful through excluded programs |

**Household question wording and behavior (owner, 2026-09-21):**
- Annual fee: "The highest annual fee you would pay on a single card". It is what the player would pay in the card's first year, so a card whose fee is waived that year counts as $0. Blank means no limit (stored as null). Ranking uses the same first-year fee.
- "If you were to put all of your day-to-day, non-housing spending on one card for the next three months, how much would that be?", then "The same, for the next 6 months", then "How much extra could you realistically spend over the next three months via supplemental spending?"
- "(Optional) Points or miles programs you do NOT want to consider" (includes Cash back), and a new "(Optional) Points or Miles programs to target" with the subheading "If you are planning for a very specific redemption, select all points programs you'd like to target if possible". A program cannot be in both.
- Targets: a card leads to a targeted program if it is co-branded with it, or its currency transfers to it and the currency is unlocked for the player (an unlocker card counts). Cards that lead to a targeted program are ranked ahead of the rest (then by value), both when picking each player's top 5 and in the combined list.
- Card history table: the column headings are "Hold now" and "Approved under 12 months ago" and so on. An open issuer section pins its name and the column headings to the top of the page while its cards scroll past.
Decision (user): replace the two "prioritize hotel/airline programs" questions with one "exclude these programs" question.
Exclusion logic: hide a co-branded card if its program is excluded. Hide a transferable-points card only if every redemption it offers is excluded (so a card remains if at least one usable partner or cash back is left).
"Cash back" is one of the excludable options (decided).

**Unlocking cards are a hard filter (decided; interpretation to confirm):** a card whose points are only worth something through transfers is shown only if the player or household holds an unlocking card, unless cash back is an acceptable redemption. Unlocking cards themselves are always shown. Unlockers per currency: Chase UR (Sapphire Preferred, Sapphire Reserve, Business Sapphire Reserve, Ink Preferred), Citi TYP (Strata Elite, Strata Premier), Capital One (a miles-earning card). Household pooling per currency: Chase UR and Capital One points can be pooled across players (an unlocker held by any player counts); Amex MR and Citi TYP cannot (the unlocker must be held by the same player). See docs/transfer-matrix.md.
**Unlock and bonus types, as built (owner, 2026-09-21):**
- No bonus types selected means all types.
- Transferable points count as airline or hotel only once the currency is unlocked for the player (the unlocker cards themselves count as unlocked) and a partner of that kind is not excluded. They count as cash back when the cash-out is good and cash back is not excluded. A card left with no wanted type is hidden ("noUnlocker" if it would match once unlocked). So a travel player without an unlocker sees only that currency's unlocker cards, and none of the currency's cards if those are blocked.
- A player who wants both travel and cash back, with no unlocker, still sees the lesser cards as cash back cards (working assumption: cash back is an acceptable redemption; confirm).
- Amex points: cash-out is good only for a player who currently holds a Schwab Platinum, or a Business Platinum plus an Amex Business Checking account, all in their own name (no pooling). A Schwab Platinum counts for its own bonus; a Business Platinum only if the checking account is already held. New per-player question, asked only when the player holds a Business Platinum: "Do you have an Amex Business Checking account?" (`hasAmexBusinessChecking`).
- Cards with no valuation (six) and the Discover cash back match cards are hidden until they have a value.

Dropped (decided): points held, home airport, destinations, planned-cards-over-2-years (replaced by the stay-under-5/24 question).

## Results
- **One combined ranked list for all players** (decided), ordered by the ranking matrix, with each card showing which players can apply for it. No card assignment between players, no combination advice.
- Result format (decided), one numbered list, each card followed by the players who can apply:
  1. Card A, P2
  2. Card B, P1 and P2
  3. Card C, P1
  4. Card D, P2
- "Ranking matrix" means the flowchart's priority lists (Section C of the rule audit) (confirmed). Cards not in the flowchart need a rank supplied by the user.
- **Mixed players (decided 2026-09-21, replaces the best-rank tie-break):** get each player's top 5 eligible cards, combine them into a single list, then rank the whole list by value. A card several players can apply for is ranked at the highest value any of them gets from it (values differ with each player's unlocked currencies), and is labeled with all of them.
- **Top-of-list banner:** links to https://frequentmiler.com/complete-guide-to-credit-card-application-rules-by-bank/ and tells the user to confirm they will not be denied by a bank-specific rule (Chase 2/30, Amex 1/5 and 2/90, Citi 8/65, BoA 2/3/4, and so on). These short-window velocity rules are not computed by the engine.
- **Credit blurb:** "This list assumes you have an established credit history and an above-average credit score. A thinner credit history or a lower score will limit which cards you can be approved for." Also point newbies to the flowchart's newbie notes and the r/churning wiki.
- **Spend note:** minimum spend is shared across cards with overlapping windows, so avoid stacking bonuses you cannot all meet.
- **NLL cards are inline, not a separate section (decided, replaces the earlier design):** if a card would be shown had the player never held a card that blocks it (Amex family rule, Section J, or once-per-lifetime, A10), it is listed at the rank it would have had, marked "(via NLL only)" for that player. Example: Delta Gold would be third of five, and the player once had Delta Gold, so it still appears third with "(via NLL only)". The mark is per player: "Card, P1 (via NLL only) and P2". Working assumption: only Amex family and lifetime blocks get this treatment; cooldown blocks (24 and 48 month rules, Marriott windows) hide the card.
- **No "why was this card hidden" section (decided).**
- **Card information (decided; updated 2026-09-21 by the owner):** each card shows the welcome bonus you earn (points or miles with the program named, cash, free nights, an "Up to" marker on "as high as" offers; a card with a second spend tier is phrased the way the offer itself reads: "Get A after spending B in C months, then get an additional X after spending Y more in Z months", owner 2026-09-21), the value of that bonus and the net value (bonus value minus the first-year annual fee; a waived first year is $0), the annual fee and the minimum spend, plus the Bilt blurb below. No other notes on cards. The `burnWorthy` flag is dropped (B2, B3, B5 superseded).
- **Rank by toggle (decided 2026-09-21):** the results page lets the user rank by best net value (default) or best raw value (bonus value only, ignoring fees). It changes each player's top 5, the backups and the combined order; the choice is remembered in the browser.
- **Bilt blurb (decided):** "The complexities of the Bilt 2.0 program make it hard to determine whether this card makes sense for you. You will need to research this program and see if it makes sense for your spending habits and your redemption goals." Decided: this is a generic page-level blurb shown to every user. Bilt cards are never included in any list. Users decide for themselves whether to research the program at all.
- **Best Personal Cards section (decided):** for a player who said they want to get or stay under 5/24 and is at 4/24 or above (so personal cards are hidden from the main list), show a separate section, "Best Personal Cards", with the subheading: "We realize that you said you are trying to get/stay under 5/24, but here are the three highest ranked personal cards you're eligible for. Only you know how close you are to being under 5/24, or when you'd be back to 4/24 if this card would make you 5/24, so only you can say whether or not any of these offers are worth applying for a personal card for." Shown per player, three cards each, in rank order.
- **List length (decided; 5 confirmed 2026-09-21):** each player's top 5 eligible cards (NLL cards count) are combined into one list, ranked by value, with each card labeled with the players for whom it is in their top 5. "As high as" backups are added per player (below) and ranked by value like everything else.
- **"As high as" backups (decided 2026-09-21, from the owner):** Amex shows "as high as" ceilings and many applicants get less. So for every card in a player's top 5 whose welcome bonus is a ceiling (`welcomeBonus.ceiling`), the results add one extra card for that player, so an applicant who does not get the maximum still has a shortlist. Refinements to confirm: (a) the extra card is the best-ranked eligible card below the top 5 that is not itself a ceiling offer and is not already listed, because a second ceiling card would not help; (b) backups are labeled "Backup" for that player; (c) ceiling cards are shown as "up to X" with a one-line note that the offer varies; (d) a player with no eligible non-ceiling card left simply gets fewer backups. Ceiling offers are still ranked at their ceiling value.
- **Ranking rules (decided):** players under 5/24 get cards in rank order. Players at 5/24 or over get the travel list, the cashback list, or both merged by rank, according to the selected bonus types. Ranks come from the user's card data (to be provided).
- **Spend hard filter (decided):** a card is hidden for a household if its typical minimum spend exceeds the capacity for its window. 3-month capacity = spend3Months + supplementalSpend3Months. 6-month capacity = spend6Months + 2 x supplementalSpend3Months. Working assumption for other windows (for example 4 months): interpolate linearly between the 3 and 6 month capacities.
- **Bonus types (decided):** show a card if it matches at least one selected type. A transferable-points card counts as airline or hotel if it has at least one non-excluded partner of that kind.
- **NLL:** confirmed that only Amex family and lifetime blocks get "(via NLL only)".
- Machine-checked rules (computed from the buckets): Chase 5/24 and Ink 3/24, Barclays 6/24, BoA credit-card count (more than 6 in 12 months with a BoA deposit account, more than 2 without) and 24-month held rule, Amex 5 credit and 10 charge card limits, Amex family rules, Capital One Venture family, lifetime rules (Sapphire, Ink, Strata families, Amex), Southwest personal family rule, Citi 8/65 and 48-month rule, Marriott matrix. Not modelled: Wells Fargo velocity rules (G11 dropped) and BoA 2/3/4. Banner-only rules: everything that needs windows shorter than the buckets.

## Ranking methods (decided 2026-09-20)
- **Value ranking (user proposal, to be built alongside the flowchart lists, decision deferred):** bonus value = points x cents-per-point (per-currency values supplied by the user, data/schema/valuations.schema.json) + cash back or statement credits + other value (for example free night certificates, valued in dollars by the user). Ranking value = bonus value minus the first-year annual fee (a waived first year costs $0). Gross bonus is not used. Effective annual fee (fee minus credits) is deliberately not used because credit values differ per person.
- **Flowchart lists:** kept in the data (`rank`) so both methods can be computed and compared. Once value ranking exists, compare it to the flowchart order; if they track closely, the flowchart lists can be dropped.
- **What counts as bonus value (decided 2026-09-20):**
  1. Authorized-user and employee-card bonuses do not count.
  2. Offers of the form "spend X for Y points, then earn 2 points per dollar on the next $Z for a total of A" (World of Hyatt): count only the first part.
  3. Offers of the form "spend A in B for C points, then spend X in Y for an additional Z points" (Aeroplan): include the additional bonus, provided the household's stated spending capacity meets at least the first threshold.
  4. Gift card and statement credit bonuses count at face value (Disney, Amazon), even though they are unlikely to be recommended.
  5. Free night awards are valued in the program's points (Marriott Boundless: 50,000 points each).
  6. Elite qualifying points (PQP) and other non-cash extras are not valued.
  7. Ranking uses the first-year annual fee (owner, 2026-09-21): a card whose first-year fee is waived is ranked with a fee of $0, and displayed as "Annual fee of $X, waived the first year" (the `firstYearFeeWaived` flag).
- **Two-rate valuations for unlock currencies (decided 2026-09-20):** Chase UR, Citi TYP and Capital One points have a `withUnlocker` and a `withoutUnlocker` cents-per-point value (data/schema/valuations.schema.json). A household's rate depends on its unlock status per currency (respecting household pooling). Working assumption to confirm: the bonus of an unlocking card itself (Sapphire Preferred or Reserve, Business Sapphire Reserve, Ink Preferred) is valued at the `withUnlocker` rate, since getting the card unlocks the currency.
- **Bonuses advertised as cash but awarded as points (decided):** stored as points in the card's currency plus a `displayedAsCash` figure (Ink Business Cash and Unlimited, Freedom cards). Ink Business Premier is real cash and is stored as `cashBack`.
- Known simplifications to state on the methodology page: first-year annual fee (a waived first year counts as $0); typical (not elevated) bonuses; one cents-per-point value per currency regardless of how the points are used.
- Stale data: one page-level line, "Bonus data last reviewed on <date>". Each card keeps its own `verifiedOn` internally.

## Site pages
- Results page (the wizard's output).
- **Ranking Methodology page (decided):** explains the value assigned to each point type, the "bonus value minus annual fee" logic, the filters (annual fee cap, spend capacity, shutdowns, excluded programs, unlock cards), and how cards get ranked against each other.
- Changelog page.
- Suggest-a-change form.

## Site behavior
- **Changelog:** a visible page listing every change to how the site chooses cards (rule changes, catalog changes), generated from a `CHANGELOG.md` in the repo.
- **Suggest a change:** a form anyone can submit without a GitHub account, which creates an issue on the repo. Needs a small serverless function that holds a narrowly scoped GitHub token and creates the issue, with spam protection (honeypot plus rate limit or a CAPTCHA service). The form sends only what the user types and warns them not to include personal information. This is the one place the site is not fully static. Approved by user.

## Profile shape and derived values
Schema: data/schema/profile.schema.json. Example (placeholder card ids, not real data): data/example-profile.json.

Stored: per player, a map of card id to `{ current, approved: { lt12, m12to24, m24to48, gt48 }, marriott? }`, generic "other personal" counts per issuer and for unlisted issuers, shutdown issuers, AA ban, business comfort, under-5/24 interest. Household: max annual fee, 3 and 6 month spend, supplemental spend, bonus types, excluded programs.

Never stored, always derived by the engine per player:
- Ever had a card: `current > 0` or any approval count above 0. (The "ever had" checkbox is UI only and auto-checks from the counts.)
- X/24: sum of `lt12 + m12to24` over cards where `reportsToPersonal`, plus the generic other-personal counts.
- Over 5/24: X/24 is 5 or more.
- Amex credit and charge card counts: sum of `current` over Amex cards, split by `chargeCard`.
- Chase business cards open, and open Ink cards split by annual fee (one no-fee and one annual-fee Ink allowed; sole proprietors are caught by the lifetime rule under either SSN or EIN, so no per-card SSN/EIN split).
- Family blocks, lifetime blocks, 24 and 48 month cooldowns, Marriott matrix lookups.
- Household unlocker status per currency, respecting each currency's `householdPooling`.

Invariants the UI must enforce: `current` is at most the sum of the four approval counts (raising `current` bumps the newest window if needed); Marriott extras appear only for Marriott cards.

Known limits of this shape:
- Cards approved in the 12 to 24 month bucket cannot be dated more precisely, so "when do I drop under 5/24" is answered only as "within 12 months".
- Product changes and upgrades are not modeled.
- The Ink SSN/EIN split is counts only; it cannot tell which specific Ink card is under which identity.

## Data still to build
- Transfer matrix (see docs/transfer-matrix.md).
- Annual fee and typical minimum spend and window per card, hand-maintained, each with a `verifiedOn` date. A maintainer-only checker exists at scripts/card_offers.py (see scripts/README.md, built test-first with 130 tests): it finds each card even if its URL moves, reads the offer and fee, flags anything doubtful, and never edits the catalog. Chase (40 cards) and Amex (24 cards, needs a headless browser) are configured; Citi and Capital One are not yet. Fee changes against the last known fee are flagged; a full diff against the catalog is not built.
