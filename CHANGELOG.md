# Changelog

What changed about how this site chooses and ranks cards, and the major site milestones. Newest first.

## 2026-09-22
- Fixed a bug where a fresh offer read could crash the whole daily data refresh instead of just flagging one card;
  added a test-suite gate so a bad build is never committed.
- Confirmed Amex can be checked safely from the automated daily refresh (previously paused after an unrelated IP
  block during development).
- Added the Signup Offer Cheat Sheet, Home page, Changelog, and Suggestions pages, and restructured site navigation.

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
