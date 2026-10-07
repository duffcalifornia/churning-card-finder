"""The cards we track and how to reach each issuer.

`urls` are only starting points: discovery falls back to sitemaps and listing pages
when they stop working. Cards marked expected=False are skipped (with the reason kept).
"""
import dataclasses
import json
import os

from .models import Card, IssuerConfig

CHASE = "https://creditcards.chase.com/"
AMEX = "https://www.americanexpress.com/"

ISSUERS = {
    "chase": IssuerConfig(
        name="chase",
        sitemaps=[CHASE + "sitemap.xml"],
        listing_pages=[CHASE, CHASE + "credit-cards"],
    ),
    "amex": IssuerConfig(
        name="amex",
        sitemaps=[AMEX + "en-us-sitemap.xml"],
        listing_pages=[AMEX + "us/credit-cards/", AMEX + "us/credit-cards/business/business-credit-cards/"],
        variant_suffixes=["28810/"],
        # Was paused 2026-09-20 to 2026-10-07 (americanexpress.com returned "Loading Error" pages after heavy use);
        # lifted by the site owner on 2026-10-07 after a test read of four cards worked. If it starts blocking again,
        # set `paused="..."` here, as it was, rather than letting the daily job keep hammering it.
        render=True,  # offers are filled in by scripts; raw HTML carries stale numbers
        fee_near_name=True,  # pages also list other cards' fees; accept only a fee stated next to this card's name
    ),
    "citi": IssuerConfig(
        name="citi",
        listing_pages=["https://www.citi.com/credit-cards/sitemap", "https://www.citi.com/credit-cards/compare/view-all-credit-cards"],
        render=True,          # bonus figures are filled in by scripts (the raw page has "$ in the first months")
    ),
    "capone": IssuerConfig(
        name="capone",
        sitemaps=["https://www.capitalone.com/sitemap.xml"],
        listing_pages=["https://www.capitalone.com/credit-cards/", "https://www.capitalone.com/small-business/credit-cards/"],
        render=True,
    ),
    "wellsfargo": IssuerConfig(
        name="wellsfargo",
        sitemaps=["https://www.wellsfargo.com/seo-sitemap/wellsfargositemap_index.xml"],   # lists almost no card pages
        listing_pages=["https://www.wellsfargo.com/credit-cards/", "https://creditcards.wellsfargo.com/"],   # the first redirects to the second
    ),
    "boa": IssuerConfig(
        name="boa",
        sitemaps=["https://www.bankofamerica.com/content/sitemap_index.xml"],
        listing_pages=["https://www.bankofamerica.com/credit-cards/", "https://www.bankofamerica.com/smallbusiness/credit-cards/"],
        render=True,
    ),
    "schwab": IssuerConfig(     # Amex-issued card hosted on schwab.com; nothing here is requested from americanexpress.com
        name="schwab",
        listing_pages=["https://www.schwab.com/credit-cards"],
    ),
    "morganstanley": IssuerConfig(     # Amex-issued cards hosted on us.etrade.com; nothing here is requested from americanexpress.com
        name="morganstanley",
    ),
    "usbank": IssuerConfig(
        name="usbank",
        sitemaps=["https://www.usbank.com/site-map.xml"],
        listing_pages=["https://www.usbank.com/credit-cards.html", "https://www.usbank.com/business-banking/business-credit-cards.html"],
    ),
    "fnbo": IssuerConfig(
        name="fnbo",
        sitemaps=["https://www.fnbo.com/sitemap.xml"],
        listing_pages=["https://www.fnbo.com/personal-banking/credit-cards"],
    ),
    "barclays": IssuerConfig(
        name="barclays",
        sitemaps=["https://cards.barclaycardus.com/sitemap.xml"],
        listing_pages=["https://cards.barclaycardus.com/banking/cards/"],
    ),
    "discover": IssuerConfig(
        name="discover",
        sitemaps=["https://www.discover.com/site-map.xml"],
        listing_pages=["https://www.discover.com/credit-cards/", "https://www.discover.com/credit-cards/travel/"],
    ),
    "bilt": IssuerConfig(
        name="bilt",
        # Only the Palladium card is tracked so far (site owner, 2026-09-21); no sitemap or listing page needed for one card.
    ),
}


def _chase(cid, names, path, kind="personal", note=""):
    return Card(id=f"chase-{cid}", issuer="chase", names=names, kind=kind, urls=[CHASE + path], note=note)


def _amex(cid, names, path, kind="personal", expected=True, note=""):
    return Card(id=f"amex-{cid}", issuer="amex", names=names, kind=kind, urls=[AMEX + path] if path else [],
                expected=expected, note=note)


_AC = "us/credit-cards/card/"
_AB = "us/credit-cards/business/business-credit-cards/"

CARDS = [
    # Chase personal
    _chase("freedom-flex", ["Chase Freedom Flex", "Freedom Flex"], "cash-back-credit-cards/freedom/flex"),
    _chase("freedom-rise", ["Chase Freedom Rise", "Freedom Rise"], "cash-back-credit-cards/freedom/rise"),
    _chase("freedom-unlimited", ["Chase Freedom Unlimited", "Freedom Unlimited"], "cash-back-credit-cards/freedom/unlimited"),
    _chase("sapphire-preferred", ["Chase Sapphire Preferred", "Sapphire Preferred"], "rewards-credit-cards/sapphire/preferred"),
    _chase("sapphire-reserve", ["Chase Sapphire Reserve", "Sapphire Reserve"], "rewards-credit-cards/sapphire/reserve"),
    _chase("united-explorer", ["United Explorer Card", "United Explorer"], "travel-credit-cards/united/united-explorer"),
    _chase("united-gateway", ["United Gateway Card", "United Gateway"], "travel-credit-cards/united/united-gateway"),
    _chase("united-quest", ["United Quest Card", "United Quest"], "travel-credit-cards/united/united-quest"),
    _chase("united-club-infinite", ["United Club Infinite Card", "United Club Infinite", "United Club Card"], "travel-credit-cards/united/club-infinite"),
    _chase("marriott-bold", ["Marriott Bonvoy Bold Credit Card", "Marriott Bonvoy Bold"], "travel-credit-cards/marriott-bonvoy/bold"),
    _chase("marriott-bountiful", ["Marriott Bonvoy Bountiful Credit Card", "Marriott Bonvoy Bountiful"], "travel-credit-cards/marriott-bonvoy/bountiful"),
    _chase("marriott-boundless", ["Marriott Bonvoy Boundless Credit Card", "Marriott Bonvoy Boundless"], "travel-credit-cards/marriott-bonvoy/boundless"),
    _chase("ihg-premier", ["IHG One Rewards Premier Credit Card", "IHG Rewards Club Premier", "IHG Premier"], "travel-credit-cards/ihg-rewards-club/premier"),
    _chase("ihg-premier-select", ["IHG One Rewards Premier Select Credit Card", "IHG Premier Select"], "travel-credit-cards/ihg-rewards-club/premier-select"),
    # Chase renamed the Traveler card in September 2026; the old URL redirects here. The id stays so saved card histories still match.
    _chase("ihg-traveler", ["IHG One Rewards Credit Card", "IHG One Rewards Traveler Credit Card", "IHG Rewards Club Traveler", "IHG Traveler"], "travel-credit-cards/ihg-rewards-club/one-rewards"),
    _chase("world-of-hyatt", ["World of Hyatt Credit Card", "World of Hyatt"], "travel-credit-cards/world-of-hyatt-credit-card"),
    _chase("southwest-plus", ["Southwest Rapid Rewards Plus Credit Card", "Southwest Plus"], "travel-credit-cards/southwest/plus"),
    _chase("southwest-premier", ["Southwest Rapid Rewards Premier Credit Card", "Southwest Premier"], "travel-credit-cards/southwest/premier"),
    _chase("southwest-priority", ["Southwest Rapid Rewards Priority Credit Card", "Southwest Priority"], "travel-credit-cards/southwest/priority"),
    _chase("aeroplan", ["Air Canada Aeroplan Card", "Aeroplan Credit Card", "Air Canada Aeroplan"], "travel-credit-cards/aircanada/aeroplan"),
    _chase("british-airways", ["British Airways Visa Signature Card", "British Airways Avios"], "travel-credit-cards/avios/british-airways"),
    _chase("aer-lingus", ["Aer Lingus Visa Signature Card", "Aer Lingus Avios"], "travel-credit-cards/avios/aer-lingus"),
    _chase("iberia", ["Iberia Visa Signature Card", "Iberia Avios"], "travel-credit-cards/avios/iberia"),
    _chase("disney-visa", ["Disney Visa Card", "Disney Rewards Visa Card"], "rewards-credit-cards/disney/rewards"),
    _chase("disney-premier", ["Disney Premier Visa Card"], "rewards-credit-cards/disney/premier"),
    _chase("disney-inspire", ["Disney Inspire Visa Card"], "rewards-credit-cards/disney/inspire"),
    _chase("amazon-prime", ["Prime Visa Credit Card", "Amazon Prime Rewards Visa Signature Card", "Prime Visa"], "cash-back-credit-cards/amazon-prime-rewards"),
    _chase("amazon-visa", ["Amazon Visa Credit Card", "Amazon Rewards Visa Signature Card", "Amazon Visa"], "cash-back-credit-cards/amazon-rewards"),
    _chase("slate", ["Chase Slate Credit Card", "Slate Credit Card"], "balance-transfer-credit-cards/slate"),
    _chase("slate-edge", ["Chase Slate Edge Credit Card", "Slate Edge"], "credit-building-credit-cards/edge"),
    _chase("doordash", ["DoorDash Rewards Mastercard", "DoorDash Card"], "cash-back-credit-cards/doordash"),
    _chase("instacart", ["Instacart Mastercard", "Instacart Card"], "cash-back-credit-cards/instacart"),
    # Chase business
    _chase("sapphire-reserve-business", ["Sapphire Reserve for Business", "Chase Sapphire Reserve for Business"], "business-credit-cards/sapphire/reserve", "business"),
    _chase("ink-unlimited", ["Ink Business Unlimited Credit Card", "Ink Business Unlimited"], "business-credit-cards/ink/unlimited", "business"),
    _chase("ink-premier", ["Ink Business Premier Credit Card", "Ink Business Premier"], "business-credit-cards/ink/premier", "business"),
    _chase("ink-cash", ["Ink Business Cash Credit Card", "Ink Business Cash"], "business-credit-cards/ink/cash", "business"),
    _chase("ink-preferred", ["Ink Business Preferred Credit Card", "Ink Business Preferred"], "business-credit-cards/ink/business-preferred", "business"),
    _chase("united-business", ["United Business Card", "United Business"], "business-credit-cards/united/united-business-card", "business"),
    _chase("united-club-business", ["United Club Business Card", "United Club Business"], "business-credit-cards/united/united-club-business", "business"),
    # Renamed from "Premier Business" in September 2026; the old URL redirects here. The id stays for the same reason.
    _chase("ihg-premier-business", ["IHG One Rewards Business Credit Card", "IHG One Rewards Premier Business Credit Card", "IHG Business Premier", "IHG Premier Business"], "business-credit-cards/IHG/business", "business"),
    _chase("southwest-premier-business", ["Southwest Rapid Rewards Premier Business Credit Card", "Southwest Premier Business"], "business-credit-cards/southwest/premier-business", "business"),
    # Amex personal
    _amex("gold", ["American Express Gold Card", "Gold Card"], _AC + "gold-card/"),
    _amex("platinum", ["Platinum Card", "American Express Platinum Card"], _AC + "platinum/"),
    _amex("blue-cash-everyday", ["Blue Cash Everyday Card"], _AC + "blue-cash-everyday/"),
    _amex("blue-cash-preferred", ["Blue Cash Preferred Card"], _AC + "blue-cash-preferred/"),
    _amex("delta-blue", ["Delta SkyMiles Blue American Express Card", "Delta SkyMiles Blue"], _AC + "delta-skymiles-blue-american-express-card/"),
    _amex("delta-gold", ["Delta SkyMiles Gold American Express Card", "Delta SkyMiles Gold"], _AC + "delta-skymiles-gold-american-express-card/"),
    _amex("delta-platinum", ["Delta SkyMiles Platinum American Express Card", "Delta SkyMiles Platinum"], _AC + "delta-skymiles-platinum-american-express-card/"),
    _amex("delta-reserve", ["Delta SkyMiles Reserve American Express Card", "Delta SkyMiles Reserve"], _AC + "delta-skymiles-reserve-american-express-card/"),
    _amex("hilton-honors", ["Hilton Honors American Express Card", "Hilton Honors Card"], _AC + "hilton-honors/"),
    _amex("hilton-surpass", ["Hilton Honors American Express Surpass Card", "Hilton Honors Surpass"], _AC + "hilton-honors-surpass/"),
    _amex("hilton-aspire", ["Hilton Honors American Express Aspire Card", "Hilton Honors Aspire"], _AC + "hilton-honors-aspire/"),
    _amex("marriott-bevy", ["Marriott Bonvoy Bevy American Express Card", "Marriott Bonvoy Bevy"], _AC + "marriott-bonvoy-bevy/"),
    _amex("marriott-brilliant", ["Marriott Bonvoy Brilliant American Express Card", "Marriott Bonvoy Brilliant"], _AC + "marriott-bonvoy-brilliant/"),
    _amex("cash-magnet", ["Cash Magnet Card"], _AC + "cash-magnet/", expected=False, note="Discontinued (site owner, 2026-09-20)."),
    _amex("everyday-preferred", ["Amex EveryDay Preferred Credit Card"], _AC + "amex-everyday-preferred/", expected=False, note="Discontinued (site owner, 2026-09-20)."),
    # Amex business
    _amex("business-gold", ["American Express Business Gold Card", "Business Gold Card"], _AB + "american-express-business-gold-card-amex/", "business"),
    _amex("business-platinum", ["Business Platinum Card", "The Business Platinum Card from American Express"], _AB + "american-express-business-platinum-credit-card-amex/", "business"),
    _amex("business-green", ["Business Green Rewards Card"], _AB + "american-express-business-green-card-amex/", "business"),
    _amex("blue-business-plus", ["Blue Business Plus Credit Card", "Blue Business Plus"], _AB + "american-express-blue-business-plus-credit-card-amex/", "business"),
    _amex("blue-business-cash", ["Blue Business Cash Card", "Blue Business Cash"], "en-us/business/credit-cards/blue-business-cash/", "business"),
    _amex("graphite", ["Graphite Business Cash Unlimited Card", "Graphite Business Cash Unlimited"], _AB + "graphite-business-cash-unlimited-card/", "business"),
    _amex("hilton-business", ["Hilton Honors American Express Business Card", "Hilton Honors Business Credit Card"], _AB + "hilton-honors/", "business"),
    _amex("delta-gold-business", ["Delta SkyMiles Gold Business American Express Card", "Delta SkyMiles Gold Business"], "en-us/business/credit-cards/delta-skymiles-gold/", "business"),
    _amex("delta-platinum-business", ["Delta SkyMiles Platinum Business American Express Card", "Delta SkyMiles Platinum Business"], "en-us/business/credit-cards/delta-skymiles-platinum/", "business"),
    _amex("delta-reserve-business", ["Delta SkyMiles Reserve Business Card", "Delta SkyMiles Reserve Business"], "en-us/business/credit-cards/delta-skymiles-reserve/", "business"),
    _amex("marriott-business", ["Marriott Bonvoy Business Credit Card", "Marriott Bonvoy Business American Express Card"], _AB + "amex-marriott-bonvoy-business-credit-card/", "business"),
    _amex("amazon-business", ["Amazon Business American Express Card", "Amazon Business Card"], _AB + "amazon-business-card/", "business", expected=False,
          note="No live application page visible (site owner, 2026-09-20)."),
    _amex("amazon-business-prime", ["Amazon Business Prime American Express Card", "Amazon Business Prime Card"], _AB + "amazon-business-prime-card/", "business", expected=False,
          note="No live application page visible (site owner, 2026-09-20)."),
]


def _c(issuer, cid, names, url, kind="personal", expected=True, note=""):
    return Card(id=f"{issuer}-{cid}", issuer=issuer, names=names, kind=kind, urls=[url] if url else [], expected=expected, note=note)


_CITI = "https://www.citi.com/credit-cards/"
_CAP = "https://www.capitalone.com/credit-cards/"
_CAPB = "https://www.capitalone.com/small-business/credit-cards/"
_WF = "https://www.wellsfargo.com/credit-cards/"
_BOA = "https://www.bankofamerica.com/credit-cards/products/"
_BOAB = "https://www.bankofamerica.com/smallbusiness/credit-cards/products/"
_USB = "https://www.usbank.com/credit-cards/"
_FNBO = "https://www.fnbo.com/personal-banking/credit-cards/"
_BARC = "https://cards.barclaycardus.com/banking/cards/"
_DISC = "https://www.discover.com/credit-cards/"

CARDS += [
    # Citi (retail store cards are not tracked)
    _c("citi", "strata-premier", ["Citi Strata Premier Card", "Citi Strata Premier"], _CITI + "citi-strata-premier-credit-card"),
    _c("citi", "strata-elite", ["Citi Strata Elite Card", "Citi Strata Elite"], _CITI + "citi-strata-elite-credit-card"),
    _c("citi", "strata", ["Citi Strata Card"], _CITI + "citi-strata-credit-card"),
    _c("citi", "double-cash", ["Citi Double Cash Card", "Citi Double Cash"], _CITI + "citi-double-cash-credit-card"),
    _c("citi", "custom-cash", ["Citi Custom Cash Card", "Citi Custom Cash"], _CITI + "citi-custom-cash-credit-card"),
    _c("citi", "diamond-preferred", ["Citi Diamond Preferred Card"], _CITI + "citi-diamond-preferred-credit-card"),
    _c("citi", "simplicity", ["Citi Simplicity Card"], _CITI + "citi-simplicity-credit-card"),
    _c("citi", "rewards-plus", ["Citi Rewards+ Card", "Citi Rewards Plus Card"], _CITI + "citi-rewards-plus-credit-card"),
    _c("citi", "aadvantage-platinum-select", ["Citi AAdvantage Platinum Select World Elite Mastercard", "AAdvantage Platinum Select"], _CITI + "citi-aadvantage-platinum-select-world-elite-mastercard"),
    _c("citi", "aadvantage-executive", ["Citi AAdvantage Executive World Elite Mastercard", "AAdvantage Executive"], _CITI + "citi-aadvantage-executive-world-legend-mastercard"),
    _c("citi", "aadvantage-globe", ["Citi AAdvantage Globe Mastercard", "AAdvantage Globe"], _CITI + "citi-aadvantage-globe-mastercard"),
    _c("citi", "aadvantage-mileup", ["AAdvantage MileUp Card", "American Airlines AAdvantage MileUp"], _CITI + "aadvantage-mile-up-credit-card"),
    _c("citi", "aadvantage-business", ["Citi AAdvantage Business World Elite Mastercard", "AAdvantage Business"], _CITI + "citi-aadvantage-business-credit-card", "business"),
    _c("citi", "costco", ["Costco Anywhere Visa Card by Citi", "Costco Anywhere Visa"], _CITI + "costco-anywhere-visa-card"),
    _c("citi", "costco-business", ["Costco Anywhere Visa Business Card by Citi", "Costco Anywhere Visa Business"], _CITI + "costco-anywhere-visa-business-card", "business"),
    # Capital One
    _c("capone", "venture-x", ["Venture X Rewards", "Venture X"], _CAP + "venture-x/"),
    _c("capone", "venture", ["Venture Rewards Travel Card", "Venture Rewards", "Venture Rewards Credit Card"], _CAP + "venture/"),
    _c("capone", "ventureone", ["VentureOne Rewards", "VentureOne"], _CAP + "ventureone/"),
    _c("capone", "quicksilver", ["Quicksilver Cash Rewards", "Quicksilver"], _CAP + "quicksilver/"),
    _c("capone", "quicksilverone", ["QuicksilverOne Cash Rewards", "QuicksilverOne"], _CAP + "quicksilverone/"),
    _c("capone", "savor", ["Savor Rewards", "Savor Cash Rewards", "Savor"], _CAP + "savor/"),
    _c("capone", "savorone", ["SavorOne Rewards", "SavorOne Cash Rewards", "SavorOne"], _CAP + "savorone/"),
    _c("capone", "spark-cash-plus", ["Spark Cash Plus"], _CAPB + "spark-cash-plus/", "business"),
    _c("capone", "spark-cash", ["Spark Cash Select", "Spark Cash"], _CAPB + "spark-cash/", "business"),
    _c("capone", "spark-miles", ["Spark Miles"], _CAPB + "spark-miles/", "business"),
    _c("capone", "spark-miles-select", ["Spark Miles Select"], _CAPB + "spark-miles-select/", "business"),
    _c("capone", "venture-x-business", ["Venture X Business"], _CAPB + "venture-x-business/", "business"),
    # Wells Fargo
    _c("wellsfargo", "active-cash", ["Wells Fargo Active Cash Card", "Active Cash Card", "Active Cash"], "https://creditcards.wellsfargo.com/active-cash-credit-card/"),
    _c("wellsfargo", "autograph", ["Wells Fargo Autograph Visa Card", "Wells Fargo Autograph Card", "Autograph Card"], "https://creditcards.wellsfargo.com/autograph-visa-credit-card/"),
    _c("wellsfargo", "autograph-journey", ["Wells Fargo Autograph Journey Visa Card", "Wells Fargo Autograph Journey Card", "Autograph Journey Card", "Autograph Journey"], "https://creditcards.wellsfargo.com/autograph-journey-visa-credit-card/"),
    _c("wellsfargo", "reflect", ["Wells Fargo Reflect Visa Card", "Wells Fargo Reflect Card", "Reflect Card"], "https://creditcards.wellsfargo.com/reflect-visa-credit-card/"),
    _c("wellsfargo", "choice-privileges", ["Wells Fargo Choice Privileges Mastercard", "Choice Privileges Mastercard", "Choice Privileges"], "https://creditcards.wellsfargo.com/wells-fargo-choice-privileges-credit-cards/"),
    _c("wellsfargo", "attune", ["Wells Fargo Attune Visa Card", "Wells Fargo Attune Card", "Attune Card"], "https://creditcards.wellsfargo.com/attune-visa-credit-card/"),
    _c("wellsfargo", "signify-business", ["Wells Fargo Signify Business Cash Card", "Signify Business Cash Card", "Signify Business"], "https://creditcards.wellsfargo.com/business-credit-cards/signify-business-cash-credit-card/", "business"),
    _c("wellsfargo", "business-elite", ["Wells Fargo Business Elite Card", "Business Elite Card"], "https://creditcards.wellsfargo.com/business-credit-cards/business-elite-credit-card/", "business"),
    # Bank of America
    _c("boa", "customized-cash", ["Bank of America Customized Cash Rewards Credit Card", "Customized Cash Rewards"], _BOA + "cash-back-credit-card/"),
    _c("boa", "unlimited-cash", ["Bank of America Unlimited Cash Rewards Credit Card", "Unlimited Cash Rewards"], _BOA + "unlimited-cash-back-credit-card/"),
    _c("boa", "travel-rewards", ["Bank of America Travel Rewards Credit Card", "Travel Rewards"], _BOA + "travel-rewards-credit-card/"),
    _c("boa", "premium-rewards", ["Bank of America Premium Rewards Credit Card", "Premium Rewards"], _BOA + "premium-rewards-credit-card/"),
    _c("boa", "premium-rewards-elite", ["Bank of America Premium Rewards Elite Credit Card", "Premium Rewards Elite"], _BOA + "premium-rewards-elite-credit-card/"),
    _c("boa", "alaska", ["Atmos Rewards Ascent Visa Signature Credit Card", "Atmos Rewards Ascent", "Alaska Airlines Visa Signature Credit Card"], _BOA + "alaska-airlines-credit-card/"),
    _c("boa", "business-unlimited-cash", ["Business Advantage Unlimited Cash Rewards Mastercard", "Unlimited Cash Rewards Mastercard", "Business Advantage Unlimited Cash Rewards"], _BOAB + "unlimited-cash-rewards-business-credit-card/", "business"),
    _c("boa", "business-customized-cash", ["Business Advantage Customized Cash Rewards Mastercard", "Customized Cash Rewards Mastercard", "Business Advantage Customized Cash Rewards"], _BOAB + "cash-rewards-business-credit-card/", "business"),
    _c("boa", "business-travel-rewards", ["Business Advantage Travel Rewards World Mastercard", "Business Advantage Travel Rewards"], _BOAB + "travel-rewards-business-credit-card/", "business"),
    _c("boa", "alaska-business", ["Alaska Airlines Visa Business Credit Card", "Atmos Rewards Visa Business Credit Card"], _BOAB + "alaska-airlines-business-credit-card/", "business"),
    # U.S. Bank
    _c("usbank", "altitude-connect", ["U.S. Bank Altitude Connect Visa Signature Card", "Altitude Connect"], _USB + "altitude-connect-visa-signature-credit-card.html"),
    _c("usbank", "altitude-go", ["U.S. Bank Altitude Go Visa Signature Card", "Altitude Go"], _USB + "altitude-go-visa-signature-credit-card.html"),
    _c("usbank", "cash-plus", ["U.S. Bank Cash+ Visa Signature Card", "Cash+ Visa Signature Card", "Cash+"], _USB + "cash-plus-visa-signature-credit-card.html"),
    _c("usbank", "smartly", ["U.S. Bank Smartly Visa Signature Card", "Bank Smartly Visa Signature Card", "Smartly"], _USB + "bank-smartly-visa-signature-credit-card.html"),
    _c("usbank", "shield", ["U.S. Bank Shield Visa Card", "Shield Visa Card", "Shield"], _USB + "shield-visa-credit-card.html"),
    _c("usbank", "business-altitude-connect", ["U.S. Bank Business Altitude Connect Visa Signature Card", "Business Altitude Connect"], "https://www.usbank.com/business-banking/business-credit-cards/business-altitude-connect-credit-card.html", "business"),
    _c("usbank", "triple-cash", ["U.S. Bank Triple Cash Rewards Visa Business Card", "Triple Cash Rewards Visa Business", "Triple Cash"], "https://www.usbank.com/business-banking/business-credit-cards/business-triple-cash-back-credit-card.html", "business"),
    _c("usbank", "business-leverage", ["Business Leverage Visa Signature Card", "U.S. Bank Business Leverage Visa Signature Card", "Business Leverage"], "https://www.usbank.com/business-banking/business-credit-cards/business-leverage-rewards-credit-card.html", "business"),
    # FNBO
    _c("fnbo", "getaway", ["Getaway Credit Card", "FNBO Getaway"], _FNBO + "getaway"),
    _c("fnbo", "evergreen", ["Evergreen Credit Card", "FNBO Evergreen"], _FNBO + "evergreen"),
    _c("fnbo", "greenselect", ["GreenSelect Credit Card", "FNBO GreenSelect"], _FNBO + "greenselect"),
    _c("fnbo", "visa-secured", ["Visa Secured Card", "FNBO Visa Secured"], _FNBO + "visa-secured-card"),
    _c("fnbo", "evergreen-business", ["Evergreen Business Edition Credit Card", "Evergreen Business Credit Card", "FNBO Evergreen Business"], "https://www.fnbo.com/small-business/credit-cards/evergreen", "business"),
    # Barclays (retail store cards are not tracked)
    _c("barclays", "jetblue", ["JetBlue Card"], _BARC + "jetblue-card/"),
    _c("barclays", "jetblue-plus", ["JetBlue Plus Card"], _BARC + "jetblue-plus-card/"),
    _c("barclays", "jetblue-premier", ["JetBlue Premier Card"], _BARC + "jetblue-premier-card/"),
    # Not on Barclays' own sitemap/listing pages (site owner, 2026-09-23) - added by hand from the card's own page,
    # so automated discovery will not find it on its own; keep this entry rather than relying on discovery to re-add it.
    _c("barclays", "hawaiian", ["Hawaiian Airlines World Elite Mastercard"],
       "https://cards.barclaycardus.com/banking/credit-card/hawaiian-airlines/combo-app/hawaiian-hbl-boh-combo-app-alt-1/"),
    _c("barclays", "wyndham-earner", ["Wyndham Rewards Earner Card"], _BARC + "wyndham-rewards-earner-card/"),
    _c("barclays", "wyndham-earner-plus", ["Wyndham Rewards Earner Plus Card"], _BARC + "wyndham-rewards-earner-plus-card/"),
    _c("barclays", "wyndham-earner-premier", ["Wyndham Rewards Earner Premier Card"], _BARC + "wyndham-rewards-earner-premier-card/"),
    _c("barclays", "wyndham-earner-business", ["Wyndham Rewards Earner Business Card"], _BARC + "wyndham-rewards-earner-business-card/", "business"),
    _c("barclays", "frontier", ["Frontier Airlines World Mastercard"], _BARC + "frontier-airlines-world-mastercard/"),
    _c("barclays", "breeze", ["Breeze Airways Card", "Breeze Easy Visa Signature Card"], _BARC + "breeze-airways/"),
    _c("barclays", "emirates-premium", ["Emirates Skywards Premium World Elite Mastercard"], _BARC + "emirates-skywards-premium-world-elite-mastercard/"),
    _c("barclays", "emirates-rewards", ["Emirates Skywards Rewards World Elite Mastercard"], _BARC + "emirates-skywards-rewards-world-elite-mastercard/"),
    _c("barclays", "lufthansa", ["Lufthansa Miles & More World Elite Mastercard", "Lufthansa Miles More World Elite Mastercard"], _BARC + "lufthansa-miles-more-world-elite-mastercard/"),
    _c("barclays", "aarp", ["AARP Essential Rewards Mastercard"], _BARC + "aarp-essential-rewards-mastercard/"),
    _c("barclays", "carnival", ["Carnival Rewards Mastercard"], _BARC + "carnival-rewards-mastercard/"),
    # Discover
    _c("discover", "it-cash-back", ["Discover it Cash Back Credit Card", "Discover it Cash Back"], _DISC + "cash-back/it-card/"),
    _c("discover", "it-chrome", ["Discover it Chrome Gas & Restaurants Credit Card", "Discover it Chrome"], _DISC + "cash-back/chrome/"),
    _c("discover", "it-miles", ["Discover it Miles Credit Card", "Discover it Miles"], _DISC + "travel/"),
    _c("discover", "it-student-cash-back", ["Discover it Student Cash Back Credit Card", "Discover it Student Cash Back"], _DISC + "student-credit-card/it-card/"),
    _c("discover", "it-student-chrome", ["Discover it Student Chrome Credit Card", "Discover it Student Chrome"], _DISC + "student-credit-card/chrome-card/"),
    _c("discover", "it-secured", ["Discover it Secured Cash Back Credit Card", "Discover it Secured Credit Card", "Discover it Secured"], _DISC + "secured-credit-card/"),
    # Bilt: only Palladium is tracked (site owner, 2026-09-21); Blue and Obsidian are not
    _c("bilt", "palladium", ["Bilt Palladium Card", "Bilt Palladium"], "https://www.bilt.com/card/palladium"),
]

CARDS += [
    # Bank of America: the rest of the card hub (student, secured, co-brand) and the business product pages
    _c("boa", "atmos-summit", ["Atmos Rewards Summit Visa Infinite Credit Card", "Atmos Rewards Summit"], _BOA + "alaska-airlines-infinite-credit-card/"),
    _c("boa", "air-france-klm", ["Air France KLM Visa Signature Credit Card", "Air France KLM"], _BOA + "air-france-credit-card/"),
    _c("boa", "allways-rewards", ["Allways Rewards Visa Card", "Allegiant Allways Rewards"], _BOA + "allegiant-credit-card/"),
    _c("boa", "royal-one", ["Royal ONE Visa Signature Credit Card", "Royal ONE"], _BOA + "royal-one-credit-card/"),
    _c("boa", "royal-one-plus", ["Royal ONE Plus Visa Signature Credit Card", "Royal ONE Plus"], _BOA + "royal-one-plus-credit-card/"),
    _c("boa", "norwegian-cruise", ["Norwegian Cruise Line World Mastercard"], _BOA + "norwegian-cruise-lines-credit-card/"),
    _c("boa", "komen", ["Susan G. Komen Customized Cash Rewards Credit Card", "Susan G Komen Customized Cash Rewards"], _BOA + "susan-komen-credit-card/"),
    _c("boa", "bankamericard", ["BankAmericard Credit Card", "BankAmericard"], _BOA + "bankamericard-credit-card/"),
    _c("boa", "student-customized-cash", ["Customized Cash Rewards Credit Card for Students"], _BOA + "student-cash-back-credit-card/"),
    _c("boa", "student-unlimited-cash", ["Unlimited Cash Rewards Credit Card for Students"], _BOA + "unlimited-cash-back-student-credit-card/"),
    _c("boa", "student-travel-rewards", ["Travel Rewards Credit Card for Students"], _BOA + "student-rewards-credit-card/"),
    _c("boa", "student-bankamericard", ["BankAmericard Credit Card for Students"], _BOA + "low-interest-student-credit-card/"),
    _c("boa", "customized-cash-secured", ["Customized Cash Rewards Secured Credit Card"], _BOA + "cash-back-secured-credit-card/"),
    _c("boa", "unlimited-cash-secured", ["Unlimited Cash Rewards Secured Credit Card"], _BOA + "unlimited-cash-back-secured-credit-card/"),
    _c("boa", "travel-rewards-secured", ["Travel Rewards Visa Secured Credit Card", "Travel Rewards Secured Credit Card"], _BOA + "travel-rewards-secured-credit-card/"),
    _c("boa", "bankamericard-secured", ["BankAmericard Secured Credit Card"], _BOA + "secured-credit-card/"),
    _c("boa", "business-platinum-plus", ["Platinum Plus Mastercard Business Credit Card", "Platinum Plus Business"], _BOAB + "platinum-plus-business-credit-card/", "business"),
    _c("boa", "business-unlimited-cash-secured", ["Unlimited Cash Rewards Secured Business Credit Card"], _BOAB + "unlimited-cash-rewards-secured-business-credit-card/", "business"),
    # U.S. Bank: business cards from the business hub and the remaining personal cards
    _c("usbank", "business-altitude-power", ["Business Altitude Power Visa Signature Card", "Business Altitude Power"], "https://www.usbank.com/business-banking/business-credit-cards/business-altitude-power-credit-card.html", "business"),
    _c("usbank", "business-essentials", ["Business Essentials Visa Card", "U.S. Bank Business Essentials Visa Card", "Business Essentials"], "https://www.usbank.com/business-banking/business-credit-cards/business-essentials-credit-card.html", "business"),
    _c("usbank", "business-essentials-plus", ["Business Essentials Plus Visa Signature Card", "U.S. Bank Business Essentials Plus Visa Signature Card", "Business Essentials Plus"], "https://www.usbank.com/business-banking/business-credit-cards/business-essentials-plus-credit-card.html", "business"),
    _c("usbank", "business-shield", ["Business Shield Visa Card", "Business Shield"], "https://www.usbank.com/business-banking/business-credit-cards/business-shield-credit-card.html", "business"),
    _c("usbank", "amazon-business", ["Amazon Business Credit Card", "Amazon Business Prime"], "https://www.usbank.com/business-banking/business-credit-cards/amazon-business-credit-cards.html", "business"),
    _c("usbank", "split", ["Split Card World Mastercard", "Split Card"], _USB + "split-card-world-mastercard-credit-card.html"),
    _c("usbank", "cash-plus-secured", ["Cash+ Secured Visa Card", "Cash+ Secured"], _USB + "cash-plus-secured-visa-credit-card.html"),
    _c("usbank", "altitude-go-secured", ["Altitude Go Secured Visa Card", "Altitude Go Secured"], _USB + "altitude-go-secured-visa-credit-card.html"),
    _c("usbank", "secured-visa", ["Secured Visa Card"], _USB + "secured-visa-credit-card.html"),
]

CARDS += [
    # Found on Chase's own category pages (missed by the sitemap-based list)
    _chase("world-of-hyatt-business", ["World of Hyatt Business Credit Card", "World of Hyatt Business"], "business-credit-cards/world-of-hyatt/hyatt-business-card", "business"),
    _chase("southwest-performance-business", ["Southwest Rapid Rewards Performance Business Credit Card", "Southwest Performance Business"], "business-credit-cards/southwest/performance-business", "business"),
    # Amex-issued cards sold through a brokerage (their own pages; family rules are handled separately)
    _c("schwab", "platinum", ["Platinum Card from American Express Exclusively for Charles Schwab", "American Express Platinum Card for Schwab", "Schwab Platinum Card"], "https://www.schwab.com/credit-cards/platinum-card"),
    _c("morganstanley", "blue-cash-preferred", ["Morgan Stanley Blue Cash Preferred American Express Card", "Morgan Stanley Blue Cash Preferred"], "https://us.etrade.com/l/morgan-stanley-blue-cash-preferred"),
    _c("morganstanley", "platinum", ["Morgan Stanley Platinum American Express Card", "Platinum Card from American Express Exclusively for Morgan Stanley", "Morgan Stanley Platinum"], "https://us.etrade.com/l/morgan-stanley-platinum"),
]


# Cards the owner approved from a "New card found" issue (reply "/track"). Kept in JSON, not in this module, so the
# card-status workflow can add to it without anyone editing Python. Each entry becomes an ordinary tracked card.
with open(os.path.join(os.path.dirname(__file__), "tracked_cards.json")) as _f:
    TRACKED = json.load(_f)
CARDS += [Card(id=cid, issuer=e["issuer"], names=[e["name"]], kind=e["kind"], urls=[e["url"]]) for cid, e in TRACKED.items()]

# Candidate pages the owner said not to track (reply "/ignore"): new-card detection never raises them again.
with open(os.path.join(os.path.dirname(__file__), "ignored_cards.json")) as _f:
    IGNORED_CANDIDATES = json.load(_f)


# Cards the site owner has said not to track (2026-09-20).
NOT_TRACKED = {
    "citi-custom-cash": "Does not exist or has no welcome offer; not considered (site owner).",
    "citi-diamond-preferred": "Does not exist or has no welcome offer; not considered (site owner).",
    "citi-simplicity": "Does not exist or has no welcome offer; not considered (site owner).",
    "citi-rewards-plus": "Does not exist or has no welcome offer; not considered (site owner).",
    "citi-costco": "Does not exist or has no welcome offer; not considered (site owner).",
    "citi-costco-business": "Does not exist or has no welcome offer; not considered (site owner).",
    "usbank-split": "Discontinued (site owner, 2026-09-20).",
    "wellsfargo-attune": "Does not exist (site owner, 2026-09-20).",
    "wellsfargo-business-elite": "Does not exist (site owner, 2026-09-20).",
    "capone-quicksilverone": "Not to be included (site owner).",
    "capone-savorone": "Not to be included (site owner).",
    "capone-spark-miles": "Does not exist (site owner).",
    "capone-spark-miles-select": "Does not exist (site owner).",
}

# Cards that can no longer be applied for. Kept in a JSON file (not this module) so the card-status workflow can add
# to it from a GitHub issue comment without anyone editing Python; see scripts/apply_card_status.py. Each entry is
# treated exactly like a NOT_TRACKED card: never requested, never in data/cards.json.
with open(os.path.join(os.path.dirname(__file__), "discontinued_cards.json")) as _f:
    DISCONTINUED = json.load(_f)
NOT_TRACKED.update({cid: entry["note"] for cid, entry in DISCONTINUED.items()})
CARDS = [dataclasses.replace(c, expected=False, note=NOT_TRACKED[c.id]) if c.id in NOT_TRACKED else c for c in CARDS]

# Facts supplied by the site owner (2026-09-20) that the issuers' pages do not state readably.
# id -> (annual fee, first year waived)
OWNER_FEES = {
    "usbank-business-altitude-connect": (95.0, True),    # $0 intro first year, $95 second year on
    "bilt-palladium": (495.0, False),   # site owner, 2026-09-21; no waiver mentioned, so assumed not waived until confirmed
    # $0 annual fee; the Amex pages never state a fee readably (site owner, 2026-09-20)
    "amex-blue-cash-everyday": (0.0, False),
    "amex-delta-blue": (0.0, False),
    "amex-hilton-honors": (0.0, False),
}
OWNER_NOTES = {
    "usbank-altitude-connect": "The welcome bonus is truly the same on Altitude Connect and Altitude Go (site owner).",
    "usbank-altitude-go": "The welcome bonus is truly the same on Altitude Connect and Altitude Go (site owner).",
}
CARDS = [dataclasses.replace(c, known_fee=OWNER_FEES[c.id][0], known_fee_first_year_waived=OWNER_FEES[c.id][1]) if c.id in OWNER_FEES else c for c in CARDS]
CARDS = [dataclasses.replace(c, note=OWNER_NOTES[c.id]) if c.id in OWNER_NOTES else c for c in CARDS]


# Fees last seen on the issuers' own pages (2026-09-20). A different fee on a later run is flagged.
with open(os.path.join(os.path.dirname(__file__), "last_known_fees.json")) as _f:
    LAST_KNOWN_FEES = json.load(_f)

# Cards whose first-year annual fee is waived (from the September 2026 issuer reads and the site owner).
with open(os.path.join(os.path.dirname(__file__), "last_known_fee_waived.json")) as _f:
    LAST_KNOWN_FEE_WAIVED = set(json.load(_f))

CARDS = [dataclasses.replace(c, expected_fee=LAST_KNOWN_FEES.get(c.id)) for c in CARDS]


# Offers last read successfully. Used only when a card's live page cannot be read; always flagged and dated.
with open(os.path.join(os.path.dirname(__file__), "last_known_offers.json")) as _f:
    LAST_KNOWN_OFFERS = json.load(_f)

CARDS = [dataclasses.replace(c, last_known_offer=LAST_KNOWN_OFFERS[c.id]["text"], last_known_on=LAST_KNOWN_OFFERS[c.id]["seen"])
         if c.id in LAST_KNOWN_OFFERS else c for c in CARDS]

# Offers last read from a hotel program's own credit card page (cardfinder.hotels). Never used on its own account:
# cardfinder.choose compares each with the issuer's offer above and keeps the better one.
with open(os.path.join(os.path.dirname(__file__), "last_known_hotel_offers.json")) as _f:
    LAST_KNOWN_HOTEL_OFFERS = json.load(_f)


# Cards whose pages were read and stated no welcome offer; the site owner confirmed on 2026-09-20 that they truly have none.
# Not included: Wells Fargo Attune and Business Elite, whose pages were never found (their offers are unknown).
NO_OFFER_CONFIRMED = {c.id for c in CARDS if c.expected and not c.last_known_offer}

# Rows the site owner checked (2026-09-20): old/new pairs where the second figure is the real offer.
REVIEWED_OK = {"chase-sapphire-reserve-business", "chase-southwest-premier-business", "wellsfargo-choice-privileges",
               # Delta Business struck-through pairs: the second figure is the current bonus (site owner, 2026-09-21)
               "amex-delta-gold-business", "amex-delta-platinum-business", "amex-delta-reserve-business",
               # World of Hyatt: only the first part counts (30,000 after $3,000 in 3 months), per the bonus-value rules
               "chase-world-of-hyatt"}

# Advertised as cash back but paid as Ultimate Rewards points, 100 points per dollar (site owner, 2026-09-20).
# Ultimate Rewards are worth 1.0 cent as cash and 1.5 cents for travel (data/valuations.json).
CASH_PAID_AS_POINTS = {cid: ("ultimate-rewards", 100) for cid in
                       ("chase-freedom-flex", "chase-freedom-unlimited", "chase-ink-cash", "chase-ink-unlimited")}


# Which free night certificate values a card's free night awards (data/valuations.json, freeNightCertificates).
FREE_NIGHT_CERTIFICATE = {
    "chase-marriott-boundless": "marriott-50k",   # each award is worth up to 50,000 points (site owner)
    "amex-marriott-business": "marriott-50k",     # "redemption level up to 50,000 points" on the offer
    # Assumption, not yet confirmed by the owner: Hilton Free Night Rewards valued at Frequent Miler's Hilton certificate.
    "amex-hilton-honors": "hilton", "amex-hilton-surpass": "hilton", "amex-hilton-aspire": "hilton", "amex-hilton-business": "hilton",
}


# The points currency or program each card's welcome bonus is paid in (ids in data/valuations.json).
CARD_CURRENCY = {}
for _issuer, _currency, _ids in [
    ("amex", "amex-membership-rewards", ("blue-business-plus", "business-gold", "business-green", "business-platinum", "gold", "platinum")),
    ("amex", "delta-skymiles", ("delta-blue", "delta-gold", "delta-gold-business", "delta-platinum", "delta-platinum-business", "delta-reserve", "delta-reserve-business")),
    ("amex", "hilton-honors", ("hilton-aspire", "hilton-business", "hilton-honors", "hilton-surpass")),
    ("amex", "marriott-bonvoy", ("marriott-bevy", "marriott-brilliant", "marriott-business")),
    ("schwab", "amex-membership-rewards", ("platinum",)),
    ("morganstanley", "amex-membership-rewards", ("platinum",)),
    ("barclays", "frontier-bonus-miles", ("frontier",)),
    ("bilt", "bilt", ("palladium",)),
    ("barclays", "jetblue-trueblue", ("jetblue", "jetblue-plus", "jetblue-premier")),
    ("barclays", "atmos-rewards", ("hawaiian",)),
    ("barclays", "miles-and-more", ("lufthansa",)),
    ("barclays", "wyndham-rewards", ("wyndham-earner", "wyndham-earner-business", "wyndham-earner-plus", "wyndham-earner-premier")),
    ("boa", "air-france-klm-flying-blue", ("air-france-klm",)),
    ("boa", "atmos-rewards", ("alaska", "alaska-business", "atmos-summit")),
    ("boa", "default-bank-points", ("business-travel-rewards", "premium-rewards", "premium-rewards-elite", "student-travel-rewards", "travel-rewards")),
    ("capone", "capital-one-miles", ("venture", "venture-x", "venture-x-business", "ventureone")),
    ("chase", "avios", ("aer-lingus", "british-airways", "iberia")),
    ("chase", "aeroplan", ("aeroplan",)),
    ("chase", "ultimate-rewards", ("freedom-flex", "freedom-unlimited", "ink-cash", "ink-unlimited", "ink-preferred", "sapphire-preferred", "sapphire-reserve", "sapphire-reserve-business")),
    ("chase", "ihg-one-rewards", ("ihg-premier", "ihg-premier-business", "ihg-premier-select", "ihg-traveler")),
    ("chase", "marriott-bonvoy", ("marriott-bold", "marriott-bountiful", "marriott-boundless")),
    ("chase", "southwest-rapid-rewards", ("southwest-performance-business", "southwest-plus", "southwest-premier", "southwest-premier-business", "southwest-priority")),
    ("chase", "united-mileageplus", ("united-business", "united-club-business", "united-club-infinite", "united-explorer", "united-gateway", "united-quest")),
    ("chase", "world-of-hyatt", ("world-of-hyatt", "world-of-hyatt-business")),
    ("citi", "american-aadvantage", ("aadvantage-business", "aadvantage-executive", "aadvantage-globe", "aadvantage-mileup", "aadvantage-platinum-select")),
    ("citi", "citi-thankyou", ("strata", "strata-elite", "strata-premier")),
    ("usbank", "default-bank-points", ("altitude-connect", "altitude-go", "business-altitude-connect")),
    ("wellsfargo", "wells-fargo-rewards", ("autograph", "autograph-journey")),
    ("wellsfargo", "choice-privileges", ("choice-privileges",)),
]:
    for _id in _ids:
        CARD_CURRENCY[f"{_issuer}-{_id}"] = _currency

# Cards paying in a currency Frequent Miler gives no value for. They cannot be value-ranked until the owner supplies one.
UNVALUED = {
    "barclays-breeze": "BreezePoints have no Frequent Miler value.",
    "barclays-carnival": "Carnival points have no Frequent Miler value.",
    "barclays-emirates-premium": "Emirates Skywards has no Frequent Miler value.",
    "barclays-emirates-rewards": "Emirates Skywards has no Frequent Miler value.",
    "boa-allways-rewards": "Allegiant Allways points have no Frequent Miler value.",
    "boa-norwegian-cruise": "Norwegian Cruise Line points have no Frequent Miler value.",
    # 2026-09-22: the live page's offer text read as a truncated fragment ("20,000 points equivalent) when you spend
    # ...", missing whatever came before the parenthetical) and needsReview is set. The card appears to be cash
    # back (the fuller text mentions redeeming for cash, statement credit, ACH deposit, or a check, and "2% Cash
    # Back" as its ongoing rate), with "points equivalent" likely just a comparison, not a real FNBO currency. Needs
    # a person to check the actual page and either fix the extraction or confirm the true bonus.
    "fnbo-evergreen": "The live offer read is garbled (a truncated sentence fragment); the true bonus is unclear.",
    "fnbo-evergreen-business": "The live offer read is garbled (a truncated sentence fragment); the true bonus is unclear.",
}


# A points currency the owner gave when approving a new card ("/track currency=...").
for _cid, _entry in TRACKED.items():
    if _entry.get("currency"):
        CARD_CURRENCY[_cid] = _entry["currency"]


# A discontinued card has no fee, note or points currency worth maintaining, and the catalog tests expect every entry in
# these tables to be a card that is still in data/cards.json. Done last so it also covers cards added to the JSON file.
for _cid in DISCONTINUED:
    OWNER_FEES.pop(_cid, None)
    OWNER_NOTES.pop(_cid, None)
    CARD_CURRENCY.pop(_cid, None)
