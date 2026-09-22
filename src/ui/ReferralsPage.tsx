import { useEffect } from "react";

// Not linked from the site's main navigation, and kept out of search results below (belt and suspenders: a
// hash-only route like #referrals is not normally crawled or indexed as its own URL in the first place). Reachable
// only via a direct link or the footer.
export const BMAC_URL = "https://www.buymeacoffee.com/duffcalifornia";

const REFERRAL_LINKS: { card: string; url: string; note?: string }[] = [
  // { card: "Chase Sapphire Preferred", url: "https://...", note: "75,000 points after $5,000 in 3 months" },
];

export function ReferralsPage() {
  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex";
    document.head.appendChild(meta);
    return () => {
      document.head.removeChild(meta);
    };
  }, []);

  return (
    <section>
      <h2>Support this project</h2>
      <p>
        This page isn't linked from the site's main navigation. If you found the site useful and you're applying
        for a card anyway, using one of these links (where available) supports the project at no cost to you. It
        has no effect on the rankings shown anywhere else on the site — the Cheat Sheet and Card Finder have no
        knowledge that this page exists.
      </p>
      <p>
        All that I ask is that if you do apply using one of these links and get approved, please submit a
        suggestion with a subject of "Referral" and let me know which link you used in the comments. This helps
        me know when to take links down and helps with my own record keeping.
      </p>
      {REFERRAL_LINKS.length === 0 ? (
        <p className="note">No referral links added yet.</p>
      ) : (
        <ul>
          {REFERRAL_LINKS.map((l) => (
            <li key={l.card}>
              <a href={l.url} target="_blank" rel="noreferrer">{l.card}</a>
              {l.note ? ` — ${l.note}` : ""}
            </li>
          ))}
        </ul>
      )}
      <p>
        You can also{" "}
        <a href={BMAC_URL} target="_blank" rel="noreferrer">buy me a coffee</a> directly, no card application needed.
      </p>
    </section>
  );
}
