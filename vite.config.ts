import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "/" (not "./"): the cheat sheet is served from real two-level paths (/cheatsheet/under-travel), where a
// relative "./assets/..." resolves to /cheatsheet/assets/... and 404s, leaving a blank page. The site is served from
// the root of its own domain, so absolute asset paths are right.
export default defineConfig({ base: "/", plugins: [react()] });
