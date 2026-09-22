import type { Profile } from "../engine/types";
import { MAX_PLAYERS, setPlayerCount } from "../state/profile";

interface Props {
  profile: Profile;
  onChange: (p: Profile) => void;
}

export function PlayersStep({ profile, onChange }: Props) {
  return (
    <section>
      <h2>How many people are you finding cards for?</h2>
      <p>
        Each person gets their own card history and eligibility. You will see one combined list, with the people who can apply for
        each card shown beside it.
      </p>
      <label className="field">
        Number of people
        <select value={profile.players.length} onChange={(e) => onChange(setPlayerCount(profile, Number(e.target.value)))}>
          {Array.from({ length: MAX_PLAYERS }, (_, i) => i + 1).map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </label>
      <p className="note">Your answers stay in this browser. Nothing is sent to a server.</p>
    </section>
  );
}
