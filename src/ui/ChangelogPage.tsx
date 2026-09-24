import changelogMd from "../../CHANGELOG.md?raw";
import { groupChangelog, parseChangelogEntries, type ChangelogEntry } from "./changelogGroups";

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const entries = parseChangelogEntries(changelogMd);

function Entry({ entry }: { entry: ChangelogEntry }) {
  return (
    <div>
      <h2>{entry.date}</h2>
      <div dangerouslySetInnerHTML={{ __html: entry.html }} />
    </div>
  );
}

export function ChangelogPage() {
  const now = new Date();
  const currentYear = now.getFullYear();
  const { currentMonthEntries, sameYearMonths, pastYears } = groupChangelog(entries, now);

  return (
    <section>
      <h2>Changelog</h2>
      <div className="changelog">
        {currentMonthEntries.length === 0 ? (
          <p className="note">No changes yet this month.</p>
        ) : (
          currentMonthEntries.map((e) => <Entry key={e.date} entry={e} />)
        )}

        {sameYearMonths.map(({ month, entries: monthEntries }) => (
          <details className="changelog-group" key={month}>
            <summary>{MONTH_NAMES[month]} {currentYear}</summary>
            {monthEntries.map((e) => <Entry key={e.date} entry={e} />)}
          </details>
        ))}

        {pastYears.map(({ year, months }) => (
          <details className="changelog-group" key={year}>
            <summary>{year}</summary>
            {months.map(({ month, entries: monthEntries }) => (
              <details className="changelog-group" key={month}>
                <summary>{MONTH_NAMES[month]} {year}</summary>
                {monthEntries.map((e) => <Entry key={e.date} entry={e} />)}
              </details>
            ))}
          </details>
        ))}
      </div>
    </section>
  );
}
