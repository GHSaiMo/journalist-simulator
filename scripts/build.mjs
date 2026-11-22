import { rollup } from 'rollup';
import resolve from '@rollup/plugin-node-resolve';
import terser from '@rollup/plugin-terser';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');
const publicDir = path.join(rootDir, 'public');
const publicBundleDir = path.join(publicDir, 'dist');
const outDeployDir = path.join(rootDir, 'dist');

fs.mkdirSync(publicBundleDir, { recursive: true });

const bundle = await rollup({
  input: path.join(rootDir, 'src', 'game.js'),
  plugins: [resolve(), terser()],
});

const bundleFile = path.join(publicBundleDir, 'app.bundle.js');
await bundle.write({
  file: bundleFile,
  format: 'iife',
  name: 'JournalistSimulator',
});
await bundle.close();

// Mirror complete static site into ./dist for 1-click deployment on Vercel / Netlify / Cloudflare Pages / GitHub Pages
fs.rmSync(outDeployDir, { recursive: true, force: true });
fs.cpSync(publicDir, outDeployDir, { recursive: true });

const kb = (fs.statSync(bundleFile).size / 1024).toFixed(1);
console.log(`Built JournalistSimulator -> public/dist/app.bundle.js (${kb} KB) & synced ./dist/`);
