import { useEffect } from "react";

/**
 * Overrides the page <title>, the existing <meta name="description">, and adds a <link rel="canonical"> while
 * mounted, restoring the previous title/description/canonical on unmount. The description tag is *modified in
 * place*, not duplicated: index.html already has one, and a crawler (like a browser) only honors the first
 * "description" meta tag it finds in the document, so appending a second one at the end of <head> would silently
 * do nothing. The canonical tag is treated the same way: the prerendered pages (scripts/prerender.mjs) already
 * carry one, and two canonical links on a page are ignored by Google, so an existing one is updated in place and
 * only created (and removed again) when there is none.
 */
export function useSeo(title: string, description: string, canonicalUrl: string): void {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = title;

    const descriptionTag = document.querySelector('meta[name="description"]');
    const previousDescription = descriptionTag?.getAttribute("content") ?? null;
    if (descriptionTag && description) descriptionTag.setAttribute("content", description);

    const existing = document.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    const previousCanonical = existing?.getAttribute("href") ?? null;
    const canonical = existing ?? document.createElement("link");
    canonical.rel = "canonical";
    canonical.href = canonicalUrl;
    if (!existing) document.head.appendChild(canonical);

    return () => {
      document.title = previousTitle;
      if (descriptionTag && previousDescription !== null) descriptionTag.setAttribute("content", previousDescription);
      if (existing) {
        if (previousCanonical !== null) existing.setAttribute("href", previousCanonical);
      } else {
        document.head.removeChild(canonical);
      }
    };
  }, [title, description, canonicalUrl]);
}
