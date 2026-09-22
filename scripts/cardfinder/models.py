"""Plain data types shared by the modules."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Card:
    id: str
    issuer: str
    names: List[str]                      # official name first, then aliases used in links and titles
    kind: str = "personal"                # "personal" or "business"
    urls: List[str] = field(default_factory=list)   # known product page URLs, best first
    expected_fee: Optional[float] = None  # last fee we verified; a different fee is flagged, not trusted
    known_fee: Optional[float] = None       # fee supplied by the site owner, used only when the page states none readably
    known_fee_first_year_waived: bool = False
    last_known_offer: Optional[str] = None  # last offer text read successfully; used only when the live page cannot be read
    last_known_on: Optional[str] = None     # date that offer was read
    expected: bool = True                 # False for cards known to be discontinued or not viewable
    note: str = ""


@dataclass
class IssuerConfig:
    name: str
    sitemaps: List[str] = field(default_factory=list)        # sitemap or sitemap index URLs
    listing_pages: List[str] = field(default_factory=list)   # pages that link to many cards
    variant_suffixes: List[str] = field(default_factory=list)  # path suffixes some pages also exist under
    render: bool = False                  # offers only appear after the page's scripts run
    paused: str = ""                      # non-empty = do not request this issuer's pages; the text says why
    fee_near_name: bool = False           # only accept a fee stated right after this card's own name (pages that list other cards' fees)


@dataclass
class Page:
    url: str
    html: str


class FetchError(Exception):
    def __init__(self, status=None, message=""):
        super().__init__(message or f"fetch failed ({status})")
        self.status = status
