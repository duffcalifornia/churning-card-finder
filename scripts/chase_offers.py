#!/usr/bin/env python3
"""Kept for compatibility: runs card_offers.py for Chase. Use card_offers.py directly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from card_offers import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["--issuer", "chase"] + sys.argv[1:]))
