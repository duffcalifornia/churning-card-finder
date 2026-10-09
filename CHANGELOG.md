What changed about how this site chooses and ranks cards, and the major site milestones. Newest first.

## 2026-10-09
- Corrected how second spending requirements are described. The Air Canada Aeroplan Card's extra 40,000 miles take $20,000 in total over 12 months (not $20,000 more on top of the first $4,000), and the Wyndham Rewards Earner cards' second bonus is spend at Hotels by Wyndham.
- Updated the rankings to reflect changes to the value of Leading Hotels Leaders Club, Preferred Hotels I Prefer, and Wyndham Rewards.

## 2026-10-08
- Updated the bonus offer for the following card(s): Blue Cash Preferred Card and Graphite Business Cash Unlimited Card.

## 2026-10-07
- Added the following card(s): JetBlue Business Card.
- The Signup Offer Cheat Sheet's four pages now load correctly when opened directly from a link or search result (they previously showed a blank page), include the date card offers were last reviewed, and are readable by search engines and link previews. Added a proper preview image for shared links and a sitemap that records when the data last changed.
- Updated the bonus offer for the following card(s): Blue Cash Preferred Card, Delta SkyMiles Gold American Express Card, Delta SkyMiles Platinum American Express Card, Emirates Skywards Premium World Elite Mastercard, Graphite Business Cash Unlimited Card, Marriott Bonvoy Bevy American Express Card, and Marriott Bonvoy Brilliant American Express Card.
- Added the following card(s): AT&T Points Plus Card.

## 2026-10-05
- The Signup Offer Cheat Sheet's cash back views now value Citi ThankYou Points at their 1 cent cash-out rate for the Citi Strata cards, instead of the 1.5 cent travel rate. The travel views are unchanged.

## 2026-10-02
- Updated the bonus offer for the following card(s): United Business Card, United Club Business Card, United Club Infinite Card, United Explorer Card, United Gateway Card, and United Quest Card.

## 2026-10-01
- Added the following card(s): IHG One Rewards Premier Select Credit Card.
- Renamed the IHG One Rewards Traveler Credit Card to the IHG One Rewards Credit Card, and the IHG One Rewards Premier Business Credit Card to the IHG One Rewards Business Credit Card, to match the new names Chase uses.
- Updated the bonus offer for the following card(s): IHG One Rewards Business Credit Card, IHG One Rewards Credit Card, and IHG One Rewards Premier Credit Card.
- Updated the net value rankings to reflect changes to the annual fee on the following card: IHG One Rewards Business Credit Card and IHG One Rewards Premier Credit Card.
- Card offers are now read from the IHG, Hilton and Chase Marriott credit card pages as well as the issuers' own, and the better offer of the two is the one the Card Finder and the Signup Offer Cheat Sheet use. An offer that says it has ended, or one last read more than a week ago, is never preferred over a current one.
- Updated the bonus offer for the following card(s): Breeze Airways Card.

## 2026-09-29
- Removed the following card(s) because they can no longer be applied for: Business Altitude Power Visa Signature Card and Business Leverage Visa Signature Card.
- Added the following card(s): Business Essentials Plus Visa Signature Card and Business Essentials Visa Card.
- Updated the bonus offer for the following card(s): AAdvantage MileUp Card and Citi AAdvantage Platinum Select World Elite Mastercard.

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
