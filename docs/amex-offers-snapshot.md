# Amex public offers snapshot (2026-09-20)

Source: each card's public product page on americanexpress.com, read in a real browser (rendered text), not the raw HTML. Amex robots.txt allows product pages. This is what an anonymous visitor sees.

How to read it:
- "As high as X" is Amex's ceiling for a targeted range ("Welcome offers vary and you may not be eligible for an offer"). Many people will get less. Treat it as a maximum, not a typical bonus.
- Two adjacent numbers on a page ("Earn 60,000 90,000 Bonus Miles") are an old figure struck through and a new one. Working assumption: the second number is current, consistent with the Chase correction. Not confirmed.
- Raw HTML contains different (stale) marketing numbers, so a plain fetch gives wrong answers. Only the rendered page is reliable.
- Requirement and window are as displayed. Expiry dates are shown where Amex prints them.

## Personal
| Card | Displayed offer | Type | Spend | Window | Ends |
|---|---|---|---|---|---|
| Gold | as high as 100,000 MR points (only on the `/28810/` variant page; the default page shows no number) | ceiling | $8,000 | 6 months | |
| Platinum | as high as 175,000 MR points | ceiling | $12,000 | 6 months | |
| Blue Cash Everyday | as high as $200 cash back | ceiling | $2,000 | 6 months | |
| Blue Cash Preferred | as high as $300 cash back | ceiling | $3,000 | 6 months | |
| Cash Magnet | none found | | | | |
| Everyday Preferred | none found | | | | |
| Delta Blue | 10,000 bonus miles | fixed | $1,000 | 6 months | |
| Delta Gold | as high as 80,000 bonus miles | ceiling | $3,000 | 6 months | |
| Delta Platinum | as high as 90,000 bonus miles | ceiling | $4,000 | 6 months | |
| Delta Reserve | 50,000 bonus miles + 2 round-trip Delta Comfort certificates | fixed | $10,000 | 6 months | |
| Hilton Honors | 70,000 points + Free Night Reward | fixed | $2,000 | 6 months | 1/13/2027 |
| Hilton Surpass | 130,000 points + Free Night Reward | fixed | $3,000 | 6 months | 1/13/2027 |
| Hilton Aspire | 200,000 points | fixed | $6,000 | 6 months | 1/13/2027 |
| Marriott Bevy | 125,000 points + $150 statement credit | fixed | $5,000 | 6 months | 9/30/2026 |
| Marriott Brilliant | 150,000 points + $250 statement credit | fixed | $6,000 | 6 months | 9/30/2026 |

## Business
| Card | Displayed offer | Type | Spend | Window | Ends |
|---|---|---|---|---|---|
| Business Platinum | as high as 300,000 MR points | ceiling | $20,000 | 3 months | |
| Business Gold | as high as 200,000 MR points | ceiling | $15,000 | 3 months | |
| Business Green Rewards | 15,000 to 25,000 MR points ("Special Welcome Offer") | fixed (two figures) | $3,000 | 3 months | |
| Blue Business Plus | 15,000 MR points | fixed | $3,000 | 3 months | |
| Blue Business Cash | $250 statement credit | fixed | $3,000 | 3 months | |
| Graphite Business Cash Unlimited | $1,500 cash back (Reward Dollars) | fixed | $50,000 | 6 months | |
| Delta Gold Business | 60,000 to 90,000 miles | fixed (two figures) | $6,000 | 6 months | 11/4/2026 |
| Delta Platinum Business | 70,000 to 100,000 miles | fixed (two figures) | $8,000 | 6 months | 11/4/2026 |
| Delta Reserve Business | 80,000 to 200,000 miles | fixed (two figures) | $20,000 | 6 months | 11/4/2026 |
| Hilton Honors Business | 150,000 points + Free Night Reward | fixed | $8,000 | 6 months | 1/13/2027 |
| Marriott Bonvoy Business | 100,000 points + 1 Free Night Award (up to 50,000 points); annual fee $125 | fixed | $8,000 | 6 months | 11/4/2026 |

Not captured: Amazon Business cards (both URLs redirect to the business card index page).

Variant pages: the sitemap lists `/28810/` variants of some card pages (Gold, Platinum, Blue Cash Everyday, Hilton Aspire and others). For Platinum, Blue Cash Everyday and Aspire the variant shows the same offer as the default page. Gold is the exception: the default page shows no number, the variant shows "as high as 100,000". Marriott Bonvoy Business is at `/us/credit-cards/business/business-credit-cards/amex-marriott-bonvoy-business-credit-card/` (it was in the business sitemap page but not in `en-us-sitemap.xml`).

## Annual fees (rendered pages and FAQ text)
Gold $325, Platinum $895, Delta Gold $0 then $150 (first year waived, from an earlier page read), Delta Platinum $350, Delta Reserve $650, Hilton Aspire $550, Marriott Bevy $250, Marriott Brilliant $650, Blue Cash Preferred $0 first year then $95, Business Platinum $895, Blue Business Cash $0. Others not verified. See the conversation for confidence notes.
