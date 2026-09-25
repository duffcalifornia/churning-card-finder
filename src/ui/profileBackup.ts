import type { Profile } from "../engine/types";

/** A saved backup's shape: the profile, plus the date it was made (for describeElapsedSince on restore). */
export type ProfileBackup = Profile & { savedOn: string };

function backupFilename(): string {
  return `card-finder-backup-${new Date().toISOString().slice(0, 10)}.json`;
}

/**
 * A plain-language answer to "how long ago was this backup made?", for the restore banner - not used for any
 * calculation. The site deliberately never tries to auto-adjust the approval-window buckets a backup carries:
 * they're recorded as which of four coarse ranges a card fell into (under 12 months, 12 to 24, and so on), not an
 * exact date, so a card near either edge of its bucket could have already crossed into the next one by the time
 * of restore, or might not have - there's no way to tell from the data alone, and guessing wrong here has real
 * consequences (5/24 and issuer velocity rules). Telling the person how much time has passed and asking them to
 * recheck everything themselves is the only version of this that can't quietly get it wrong.
 */
export function describeElapsedSince(savedOn: string | undefined): string | null {
  if (!savedOn) return null;
  const saved = new Date(savedOn);
  if (Number.isNaN(saved.getTime())) return null;
  // Both dates read in UTC, matching how `savedOn` is written (an ISO date-only string, which Date parses as UTC
  // midnight) - mixing that with the local-timezone getters (getDate() etc.) is the classic off-by-one-day bug,
  // since a UTC midnight timestamp can fall on the previous local calendar day west of UTC.
  const now = new Date();
  let months = (now.getUTCFullYear() - saved.getUTCFullYear()) * 12 + (now.getUTCMonth() - saved.getUTCMonth());
  if (now.getUTCDate() < saved.getUTCDate()) months -= 1;
  if (months <= 0) return "less than a month ago";
  if (months === 1) return "about 1 month ago";
  return `about ${months} months ago`;
}

function downloadBlob(json: string, filename: string): void {
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Saves the profile to a file: the Web Share API when it's available (most mobile browsers), since a plain
 * download link is unreliable there - iOS Safari sometimes just navigates the tab to show the raw JSON instead
 * of actually saving a file - and a share sheet (AirDrop, Files, Messages, email) is a more native way to get a
 * file off a phone than "check your Downloads folder" anyway. Falls back to a plain download where sharing files
 * isn't supported (desktop browsers, mainly). If the user cancels the share sheet or it fails for some other
 * reason, this leaves it at that rather than immediately following a dismissed share sheet with an unrequested
 * plain download.
 */
export async function downloadProfileBackup(profile: Profile): Promise<void> {
  const backup: ProfileBackup = { ...profile, savedOn: new Date().toISOString().slice(0, 10) };
  const json = JSON.stringify(backup, null, 2);
  const filename = backupFilename();
  const file = new File([json], filename, { type: "application/json" });
  const nav = navigator as Navigator & { canShare?: (data: { files: File[] }) => boolean };
  if (nav.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file] });
    } catch {
      // Cancelled or failed - either way, no fallback download.
    }
    return;
  }
  downloadBlob(json, filename);
}
