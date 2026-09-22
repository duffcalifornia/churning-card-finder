# Self-hosted Public Sans

`public-sans-var.woff2` is Google's own variable-font build of Public Sans (Latin subset only, weights 100–900
in one file), downloaded once so the site never makes a request to Google Fonts. It's open source (SIL Open Font
License), so redistributing it here is fine.

To refresh it (a new version is published upstream, or you want to add another subset):

```bash
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800&display=swap" \
  | grep -A2 '/\* latin \*/' | grep -o 'https://fonts.gstatic.com/[^)]*\.woff2'
```

That prints the current "latin" subset URL (a browser-like `User-Agent` is required — without one, Google serves
older static per-weight files instead of the modern variable-font build). Download it and overwrite
`public-sans-var.woff2`.
