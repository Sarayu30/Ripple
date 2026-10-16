// Vercel serves only this explicit public artifact, never the Python backend.
import {mkdir, readdir, readFile, writeFile, copyFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export function configuration(env) {
  const origin = env.RIPPLE_BACKEND_ORIGIN || '';
  let backend;
  try { backend = new URL(origin); } catch { throw Error('Set RIPPLE_BACKEND_ORIGIN to the persistent HTTPS backend.'); }
  if (backend.protocol !== 'https:' || backend.username || backend.password || backend.pathname !== '/' || backend.search || backend.hash || backend.port) {
    throw Error('Backend origin must be HTTPS, without credentials, paths or custom ports.');
  }
  const authUrl = (env.NEON_AUTH_BASE_URL || '').replace(/\/$/, '');
  if (!/^https:\/\/[a-z0-9-]+(?:\.[a-z0-9-]+)*\.neon\.(tech|build)\/[A-Za-z0-9_-]+\/auth$/.test(authUrl)) throw Error('Set the public Neon Auth Base URL, not a database connection string.');
  if (!env.ORIGIN_SECRET || env.ORIGIN_SECRET.length < 32) throw Error('Set a server-only ORIGIN_SECRET of at least 32 characters in Vercel and the backend.');
  return {backend: backend.origin, auth: {mode: 'neon', url: authUrl}};
}

export async function buildWeb(env = process.env, output = '.vercel/output') {
  const config = configuration(env);
  const root = path.resolve(output), assets = path.join(root, 'static', 'static');
  await mkdir(assets, {recursive: true});
  let html = await readFile('app/static/index.html', 'utf8');
  for (const entry of await readdir('app/static', {withFileTypes: true})) {
    if (!entry.isFile() || entry.name === 'index.html' || entry.name === 'auth-config.js') continue;
    if (!/^[a-zA-Z0-9.-]+\.(js|css|svg|png|woff2|txt)$/.test(entry.name)) throw Error('Unexpected public asset type.');
    const bytes = await readFile(path.join('app/static', entry.name));
    // Version directly referenced scripts/styles; existing relative font URLs work.
    const referenced = html.includes('/static/' + entry.name + '"');
    const name = referenced ? entry.name.replace(/\.(js|css)$/, '.' + createHash('sha256').update(bytes).digest('hex').slice(0,12) + '.$1') : entry.name;
    await copyFile(path.join('app/static', entry.name), path.join(assets, name));
    html = html.replaceAll('/static/' + entry.name + '"', '/static/' + name + '"');
  }
  await writeFile(path.join(assets, 'auth-config.js'), 'window.RipplePublicAuth = ' + JSON.stringify(config.auth) + ';\n');
  await writeFile(path.join(root, 'static', 'index.html'), html);
  const csp = `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self' ${config.auth.url}; worker-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`;
  const headers = {'Content-Security-Policy': csp, 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY', 'Strict-Transport-Security': 'max-age=31536000'};
  const routes = [
    {src: '/(.*)', headers, continue: true},
    {src: '/api/(.*)', dest: config.backend + '/api/$1', headers: {'Cache-Control': 'private, no-store', 'CDN-Cache-Control': 'no-store', 'Vercel-CDN-Cache-Control': 'no-store', 'x-vercel-enable-rewrite-caching': '0'},
      transforms: [{type: 'request.headers', op: 'set', target: {key: 'x-ripple-origin-secret'}, args: '$ORIGIN_SECRET', env: ['ORIGIN_SECRET']}]},
    {src: '/static/.*\\.[a-f0-9]{12}\\.(js|css)', headers: {'Cache-Control': 'public, max-age=31536000, immutable'}, continue: true},
    {src: '/static/auth-config.js', headers: {'Cache-Control': 'no-store'}, continue: true},
    {handle: 'filesystem'},
    {src: '/', dest: '/index.html', headers: {'Cache-Control': 'no-store'}},
    {src: '/.*', status: 404},
  ];
  await writeFile(path.join(root, 'config.json'), JSON.stringify({version: 3, routes}, null, 2));
  return root;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await buildWeb();
  console.log('Built public Vercel assets and protected backend routing. No server credentials were bundled.');
}
