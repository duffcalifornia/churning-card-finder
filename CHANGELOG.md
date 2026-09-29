What changed about how this site chooses and ranks cards, and the major site milestones. Newest first.

## 2026-09-29
- Removed the following card(s) because they can no longer be applied for: Business Altitude Power Visa Signature Card and Business Leverage Visa Signature Card.
- Added the following card(s): Business Essentials Plus Visa Signature Card and Business Essentials Visa Card.

## 2026-09-28
- Updated the bonus offer for the following card(s): Wells Fargo Autograph Visa Card.

## 2026-09-26
- The Signup Offer Cheat Sheet's four views now each have their own real, shareable URL (for example /cheatsheet/under-cashback) with their own page title, instead of all four sharing one generic link. Added a sitemap for search engines.
- After sending a suggestion, the confirmation now links straight to that suggestion's GitHub issue so you can check its status, instead of just mentioning that one exists.
- Updated the bonus offer for the following card(s): Wells Fargo Autograph Visa Card.

## 2026-09-25
- Added "Download my data" and "Restore from a file" to the Card Finder's card history step, so your answers survive clearing site data or switching devices. Nothing is sent to a server - the file only ever moves between your own device and your own browser. Restoring shows how long ago the backup was made and doesn't guess at anything: you're asked to look over the approval windows and how many of each card you hold, since either may have changed since the backup.
- Fixed "Download my data" opening desktop Safari's share sheet (AirDrop, Mail, Messages...) instead of saving the file, since that sheet has no direct way to just save it. Only phones and tablets get the share sheet now; every other device gets a plain download.

## 2026-09-24
- Fixed the Signup Offer Cheat Sheet's cash-back columns valuing Chase Sapphire Preferred, Chase Sapphire Reserve, and Ink Business Preferred at Ultimate Rewards' travel-transfer rate instead of its cash-out rate, since getting one of those cards is what unlocks the currency in the first place.
- Fixed the daily data refresh logging a "bonus offer updated" entry whenever an issuer's page reformatted its wording (a swapped punctuation mark, retitled section) with the actual points, minimum spend and fee never moving - it now compares the parsed offer instead of the raw scraped text.
- Updated the bonus offer for the following card(s): Wells Fargo Autograph Journey Visa Card.

## 2026-09-23
- Made the Changelog page collapse older entries as the site ages: this month stays fully visible, older months in the current year each get their own collapsible section, and past years collapse into one section per year holding that year's own months - so the page stays short no matter how long the changelog gets.
- Added a "Cards to show" filter to the Signup Offer Cheat Sheet, so you can view all cards, personal cards only, or business cards only.
- Fixed a bug where, on iPad and iPhone in Safari and Chrome, focusing a card-count field in the card history table could scroll the sticky issuer and column headers up behind the browser's own toolbar.
- Added a button to download the Card Finder's recommended cards as a CSV file.
- Added the Barclays Hawaiian Airlines World Elite Mastercard, which is not listed on Barclays' own card pages.
- Updated the bonus offer for the following card(s): Spark Cash Select, Wells Fargo Autograph Journey Visa Card, and Wells Fargo Signify Business Cash Card.
- Updated the net value rankings to reflect changes to the annual fee on the following card: Spark Cash Select.

## 2026-09-22
- Fixed a bug where a fresh offer read could crash the whole daily data refresh instead of just flagging one card;
  added a test-suite gate so a bad build is never committed.
- Confirmed Amex can be checked safely from the automated daily refresh (previously paused after an unrelated IP
  block during development).
- Added the Signup Offer Cheat Sheet, Home page, Changelog, and Suggestions pages, and restructured site navigation.
- Updated the bonus offer for the following card(s): Bilt Palladium Card, Spark Cash Select, and Wells Fargo Autograph Visa Card.
- Updated the net value rankings to reflect changes to the annual fee on the following card: Spark Cash Select.
- Updated the bonus offer for the following card(s): Wells Fargo Autograph Journey Visa Card.

## 2026-09-21
- Assembled the full card catalog and built the rules engine: 5/24 and issuer velocity limits, lifetime and family
  rules (Amex, Chase Sapphire and Ink, Citi Strata, Capital One Venture), the Marriott eligibility matrix, transfer
  "unlock" requirements, and value-based ranking (a welcome bonus's dollar value minus its first-year annual fee).
- Added the Chase Ink lifetime workaround question (forming an LLC in a low-fee state).
- Published the Ranking Methodology page.
- Refreshed all Amex offers and fees.
- Set up automatic daily watching of Frequent Miler's point valuations and, later, of every tracked card's offer.

## 2026-09-20
- Audited the r/churning credit card flowchart's rules section by section against current issuer terms and
  community sources, confirming or correcting each one before it shipped in the engine.
- Designed the questionnaire flow and results format.
- Built a maintainer tool that reads each tracked card's welcome offer and annual fee from the issuer's own public
  page, defensively (URL changes, redirects, rendered pages, error pages) and never guesses a value it can't read.
