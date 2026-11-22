import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.resolve(__dirname, '..', 'public');
const port = Number(process.argv[2] || process.env.PORT || 1926);

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.glb': 'model/gltf-binary',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.mp4': 'video/mp4',
};

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
  const relPath = urlPath === '/' ? 'index.html' : urlPath.replace(/^\/+/, '');
  const fullPath = path.resolve(publicDir, relPath);

  if (!fullPath.startsWith(publicDir) || !fs.existsSync(fullPath) || fs.statSync(fullPath).isDirectory()) {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('404 Not Found');
    return;
  }

  const ext = path.extname(fullPath).toLowerCase();
  const stat = fs.statSync(fullPath);
  res.writeHead(200, {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'Content-Length': stat.size,
    'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
  });
  fs.createReadStream(fullPath).pipe(res);
});

server.listen(port, '0.0.0.0', () => {
  const nets = os.networkInterfaces();
  let lanIp = null;
  for (const list of Object.values(nets)) {
    for (const info of list || []) {
      if (info.family === 'IPv4' && !info.internal) {
        lanIp = info.address;
        break;
      }
    }
    if (lanIp) break;
  }
  console.log(`\n📷 Journalist Simulator running:`);
  console.log(`   ➜ Local:   http://127.0.0.1:${port}/`);
  if (lanIp) console.log(`   ➜ Network: http://${lanIp}:${port}/`);
});
