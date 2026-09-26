import { useEffect } from "react";

/**
 * Overrides the page <title>, the existing <meta name="description">, and adds a <link rel="canonical"> while
 * mounted, restoring the previous title/description and removing the canonical tag on unmount. The description
 * tag is *modified in place*, not duplicated: index.html already has one, and a crawler (like a browser) only
 * honors the first "description" meta tag it finds in the document, so appending a second one at the end of
 * <head> would silently do nothing. There's no existing canonical tag to collide with, so that one is just
 * created and removed, the same pattern ReferralsPage already uses for its noindex meta tag.
 */
export function useSeo(title: string, description: string, canonicalUrl: string): void {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = title;

    const descriptionTag = document.querySelector('meta[name="description"]');
    const previousDescription = descriptionTag?.getAttribute("content") ?? null;
    if (descriptionTag && description) descriptionTag.setAttribute("content", description);

    const canonical = document.createElement("link");
    canonical.rel = "canonical";
    canonical.href = canonicalUrl;
    document.head.appendChild(canonical);

    return () => {
      document.title = previousTitle;
      if (descriptionTag && previousDescription !== null) descriptionTag.setAttribute("content", previousDescription);
      document.head.removeChild(canonical);
    };
  }, [title, description, canonicalUrl]);
}
