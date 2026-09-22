import { marked } from "marked";
import changelogMd from "../../CHANGELOG.md?raw";

// Safe to render as HTML: the source is CHANGELOG.md, a file only the maintainer edits, never user input.
const html = marked.parse(changelogMd, { async: false });

export function ChangelogPage() {
  return (
    <section>
      <div className="changelog" dangerouslySetInnerHTML={{ __html: html }} />
    </section>
  );
}
