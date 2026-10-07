// Runs after `vite build`: writes the homepage and each cheat sheet page into dist/ as static HTML with the app's
// real markup inside #root and per-page head tags, plus a sitemap with real lastmod dates. See src/prerender.tsx.
// The app's source is loaded through Vite's own module runner so the same JSON/TSX/?raw imports resolve as in the build.
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "dist");

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
const jsonLd = (o) => JSON.stringify(o).replace(/</g, "\\u003c");

const vite = await createServer({ root, appType: "custom", server: { middlewareMode: true }, logLevel: "error" });
try {
  const mod = await vite.ssrLoadModule("/src/prerender.tsx");
  const template = await readFile(join(dist, "index.html"), "utf8");
  const SITE = mod.SITE_URL;

  const setMeta = (html, attr, name, value) =>
    html.replace(new RegExp(`(<meta ${attr}="${name}" content=")[^"]*(")`), (_, a, b) => `${a}${esc(value)}${b}`);

  for (const path of mod.prerenderedPaths()) {
    const head = mod.headFor(path);
    const url = `${SITE}${path}`;
    let html = template.replace(/<title>.*?<\/title>/, `<title>${esc(head.title)}</title>`);
    html = setMeta(html, "name", "description", head.description);
    html = setMeta(html, "property", "og:title", head.title);
    html = setMeta(html, "property", "og:description", head.description);
    html = setMeta(html, "property", "og:url", url);
    html = setMeta(html, "name", "twitter:title", head.title);
    html = setMeta(html, "name", "twitter:description", head.description);
    const extra =
      `    <link rel="canonical" href="${url}" />\n` +
      head.jsonLd.map((o) => `    <script type="application/ld+json">${jsonLd(o)}</script>\n`).join("");
    html = html.replace("</head>", `${extra}  </head>`);
    // A hash page (/#methodology, /#finder) shares this HTML with the homepage; the app then shows that page, so
    // the homepage markup must not flash first.
    const clearOnHash = `<script>if(location.hash)document.getElementById("root").innerHTML=""</script>`;
    html = html.replace('<div id="root"></div>', `<div id="root">${mod.renderBody(path)}</div>\n    ${clearOnHash}`);
    if (!html.includes(`<link rel="canonical" href="${url}"`) || !html.includes('id="root"><')) throw new Error(`prerender failed for ${path}`);

    const file = path === "/" ? join(dist, "index.html") : join(dist, `${path}.html`);
    await mkdir(dirname(file), { recursive: true });
    await writeFile(file, html);
    console.log(`prerendered ${path}`);
  }
  await writeFile(join(dist, "sitemap.xml"), mod.sitemapXml());
  console.log("wrote sitemap.xml");
} finally {
  await vite.close();
}
