import { useEffect } from "react";

// Not linked from the site's main navigation, and kept out of search results below (belt and suspenders: a
// hash-only route like #referrals is not normally crawled or indexed as its own URL in the first place). Reachable
// only via a direct link or the footer.
export const BMAC_URL = "https://www.buymeacoffee.com/duffcalifornia";

const REFERRAL_LINKS: { card: string; url: string; note?: string }[] = [
  { card: "Chase Sapphire Preferred or Chase Sapphire Reserve", url: "https://www.referyourchasecard.com/19y/LGJY8U38RR" },
  { card: "Any personal Chase Marriott Bonvoy card", url: "https://www.referyourchasecard.com/252x/7ZNYOB8EJ1" },
  { card: "Any Chase Ink card, or the Sapphire Reserve for Business", url: "https://www.referyourchasecard.com/21h/SJH75ACD2K" },
  {
    card: "Any American Express card, personal or business",
    url: "https://americanexpress.com/en-us/referral/business-platinum-charge-card?ref=PAULBoQy8&xl=cp01",
    note: "The link shows the Business Platinum by default, but you can pick any other personal or business Amex card from that page before applying.",
  },
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
