# Transferable points matrix

Source: user-provided, 2026-09-20. Status: unverified against issuer pages. Transfer ratios were not provided; v1 needs only which partners exist. Verify against each issuer's own transfer partner page before launch.

Legend: "Avios" means Aer Lingus, British Airways, Iberia and Qatar programs together.

## Programs by currency

**Chase Ultimate Rewards:** Avios, Air Canada Aeroplan, Air France/KLM Flying Blue, Finnair Plus, Hyatt, IHG, JetBlue, Marriott Bonvoy, Singapore Airlines KrisFlyer, Southwest Rapid Rewards, United MileagePlus, Virgin Atlantic Flying Club, Wyndham, cash back.

**Amex Membership Rewards:** Avios, Aeromexico Club Premier, Air Canada Aeroplan, Air France/KLM Flying Blue, ANA Mileage Club, Avianca LifeMiles, Cathay Pacific Asia Miles, Choice, Delta SkyMiles, Emirates Skywards, Finnair Plus, Hilton, JetBlue, Leading Hotels of the World, Marriott Bonvoy, Qantas Frequent Flyer, Singapore Airlines KrisFlyer, Virgin Atlantic Flying Club, cash back.

**Capital One rewards:** Avios, Aeromexico Club Premier, Air Canada Aeroplan, Air France/KLM Flying Blue, ALL Accor, Avianca LifeMiles, Cathay Pacific Asia Miles, Choice, Emirates Skywards, Etihad Guest, EVA Air Infinity MileageLands, Finnair Plus, JAL Mileage Bank, JetBlue, Preferred Hotels and Resorts, Qantas Frequent Flyer, Singapore Airlines KrisFlyer, TAP Air Portugal, Turkish Airlines Miles and Smiles, Virgin Atlantic Flying Club, Wyndham.

**Citi ThankYou Rewards:** Avios, Air France/KLM Flying Blue, American AAdvantage, Avianca LifeMiles, Cathay Pacific Asia Miles, Emirates Skywards, Etihad Guest, EVA Air Infinity MileageLands, Finnair Plus, JAL Mileage Bank, Jet Airways InterMiles, JetBlue, Malaysia Enrich, Qantas Frequent Flyer, Singapore Airlines KrisFlyer, Thai Airways Royal Orchid Plus, Turkish Airlines Miles and Smiles, Virgin Atlantic Flying Club, ALL Accor, Choice, Leading Hotels of the World, Preferred Hotels and Resorts, Wyndham, cash back. (Jet Airways InterMiles removed: defunct, confirmed by user.)

**Wells Fargo Rewards (user, 2026-09-20):** Avios, Air France/KLM Flying Blue, Cathay Pacific, JetBlue, "Virgin America", Choice, Wyndham. Confirmed by user: this is Virgin Atlantic (Flying Club), not Virgin America.

**Bilt Rewards:** ALL Accor, Hilton, Hyatt, IHG, Marriott Bonvoy, Preferred Hotels and Resorts, Wyndham, Avios, Air Canada Aeroplan, Air France/KLM Flying Blue, Alaska Atmos, Avianca LifeMiles, Cathay Pacific Asia Miles, Etihad Guest, Finnair Plus, JAL Mileage Bank, Southwest Rapid Rewards, TAP Air Portugal, Turkish Airlines Miles and Smiles, United MileagePlus, Virgin Atlantic Flying Club.

## Per-program quirks
**Chase:** UR can be transferred between household members. At least one household member must hold a Sapphire Preferred, Sapphire Reserve, Business Sapphire Reserve or Ink Preferred to transfer points to any partner program.

**Amex:** MR cannot be transferred between household members. Redeeming MR for cash back is only worthwhile with (a) a Morgan Stanley Platinum, (b) a Schwab Platinum, or (c) a Business Platinum plus a business checking account.

**Citi:** You need a Strata Elite or Strata Premier to transfer points to transfer partners. Points cannot be transferred between household members. Double Cash rewards can be transferred to rewards cards.

**Capital One:** Rewards can be moved from cash back cards to miles. Points can be transferred to any cardholder. You need a card that earns miles to transfer to partners.

## Confirmed by user (2026-09-20)
- Jet Airways is defunct (removed). Hilton under Amex, and Wyndham under Chase and Capital One, are correct.
- Spelling fixes to apply when the data is encoded: Etihad Guest, EVA Air Infinity MileageLands, Cathay Pacific Asia Miles.

## Also confirmed
- Wells Fargo's "Virgin" partner is Virgin Atlantic.
- Co-branded currencies (United, Delta, Southwest, etc.) are treated as their own program.

## Items still open
- Transfer ratios are not recorded (not needed for v1).
- Verify the whole matrix against each issuer's own partner page before launch.

## Engine implications
- **Unlocking card is a hard filter (user decision).** A card that earns transferable points and is not itself an unlocker is shown only if the player, or the household where pooling is allowed, holds an unlocking card, unless cash back is an acceptable redemption. Unlockers: Chase (Sapphire Preferred, Sapphire Reserve, Business Sapphire Reserve, Ink Preferred), Citi (Strata Elite, Strata Premier), Capital One (any miles-earning card). Amex and Wells Fargo have no unlocker in the notes provided (Amex cash back is only optimal with the special cards above).
- Household pooling: Chase UR and Capital One points can be pooled across players; Amex MR and Citi TYP cannot.
