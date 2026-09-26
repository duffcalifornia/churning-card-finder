import { useEffect } from "react";

// Not linked from the site's main navigation, and kept out of search results below (belt and suspenders: a
// hash-only route like #referrals is not normally crawled or indexed as its own URL in the first place). Reachable
// only via a direct link or the footer.
export const BMAC_URL = "https://www.buymeacoffee.com/duffcalifornia";

interface ReferralLink {
  card: string;
  url: string;
  note?: string;
}

// The actual URLs live in Vite env vars (VITE_REFERRAL_*, set in Vercel), not here - not to hide them from site
// visitors (that's the opposite of the point of a referral link, and they end up in the built JS bundle regardless,
// same as a hardcoded string would), but so that swapping one out later is an env var change with no commit and no
// trace in git history, rather than a diff anyone browsing the repo could compare against the old one. An unset
// var just drops that entry, which is also how a local dev build with none of these configured falls through to
// the "No referral links added yet" message below.
const REFERRAL_LINKS: ReferralLink[] = (
  [
    { card: "Chase Sapphire Preferred or Chase Sapphire Reserve", url: import.meta.env.VITE_REFERRAL_CHASE_SAPPHIRE },
    { card: "Any personal Chase Marriott Bonvoy card", url: import.meta.env.VITE_REFERRAL_CHASE_MARRIOTT },
    { card: "Any Chase Ink card, or the Sapphire Reserve for Business", url: import.meta.env.VITE_REFERRAL_CHASE_INK },
    {
      card: "Any American Express card, personal or business",
      url: import.meta.env.VITE_REFERRAL_AMEX,
      note: "The link shows the Business Platinum by default, but you can pick any other personal or business Amex card from that page before applying.",
    },
  ] as { card: string; url: string | undefined; note?: string }[]
).filter((l): l is ReferralLink => Boolean(l.url));

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
