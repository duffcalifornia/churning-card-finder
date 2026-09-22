import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" lets the built site be hosted from any path (GitHub Pages project pages, Netlify, Vercel).
export default defineConfig({ base: "./", plugins: [react()] });
