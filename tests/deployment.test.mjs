import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, readFile, readdir} from 'node:fs/promises';
import path from 'node:path';
import {buildWeb, configuration} from '../frontend/vercel.mjs';

const env = {RIPPLE_BACKEND_ORIGIN: 'https://backend.example.com', NEON_AUTH_BASE_URL: 'https://fixture.neon.tech/auth/auth', ORIGIN_SECRET: 'private-origin-value-'.repeat(3), GROQ_API_KEY: 'private-groq-canary', DATABASE_URL: 'private-database-canary'};
test('reject secret keys and credential-bearing backend URLs', () => {
  assert.throws(() => configuration({...env, NEON_AUTH_BASE_URL:'postgresql://user:password@host/auth'}));
  assert.throws(() => configuration({...env, NEON_AUTH_BASE_URL:'https://user:password@fixture.neon.tech/auth/auth'}));
  assert.throws(() => configuration({...env, RIPPLE_BACKEND_ORIGIN:'https://user:password@backend.example.com'}));
  assert.throws(() => configuration({...env, ORIGIN_SECRET:''}));
});
test('public artifact excludes server secrets and disables API caching', async () => {
  const output = await mkdtemp(path.resolve('artifacts', 'vercel-test-'));
  await buildWeb(env, output);
  async function content(root) {
    let combined = '';
    for (const entry of await readdir(root, {withFileTypes:true})) {
      const file = path.join(root, entry.name);
      combined += entry.isDirectory() ? await content(file) : (await readFile(file)).toString();
    }
    return combined;
  }
  const text = await content(output);
  for (const name of ['ORIGIN_SECRET','GROQ_API_KEY','DATABASE_URL']) assert.ok(!text.includes(env[name]));
  const config = JSON.parse(await readFile(path.join(output, 'config.json')));
  const route = config.routes.find(r => r.src === '/api/(.*)');
  assert.equal(route.headers['Vercel-CDN-Cache-Control'], 'no-store');
  assert.equal(route.transforms[0].args, '$ORIGIN_SECRET');
  const html = await readFile(path.join(output, 'static/index.html'), 'utf8');
  assert.match(html, /auth\.[a-f0-9]{12}\.js/);
  assert.ok(!text.includes('postgresql://'));
});
