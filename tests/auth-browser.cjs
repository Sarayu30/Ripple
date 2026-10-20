const http = require('http');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');

let policy;
const server = http.createServer((req, res) => {
  if (policy) res.setHeader('Content-Security-Policy', policy);
  const name = req.url === '/' ? 'index.html' : req.url.replace('/static/', '');
  if (!/^[a-zA-Z0-9.-]+$/.test(name)) {res.writeHead(404); res.end(); return;}
  const file = path.join(__dirname, '../app/static', name);
  if (!fs.existsSync(file)) {res.writeHead(404); res.end(); return;}
  res.setHeader('Content-Type', name.endsWith('.js') ? 'text/javascript' : name.endsWith('.css') ? 'text/css' : name.endsWith('.woff2') ? 'font/woff2' : 'text/html');
  res.end(fs.readFileSync(file));
});
(async () => {
  const {contentSecurityPolicy} = await import('../frontend/vercel.mjs');
  policy = contentSecurityPolicy('https://fixture.neon.tech/auth/auth');
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1050}, reducedMotion: 'reduce'});
    const base = 'http://127.0.0.1:' + server.address().port;
    const authUrl = 'https://fixture.neon.tech/auth/auth';
    const user = {id:'00000000-0000-4000-8000-000000000001', name:'Documentation account', email:'fixture@example.com', emailVerified:true, createdAt:new Date().toISOString(), updatedAt:new Date().toISOString()};
    const jwt = 'header.' + Buffer.from(JSON.stringify({exp:Math.floor(Date.now()/1000)+900})).toString('base64url') + '.fixture';
    let signedIn = true, minted = 0, synchronized = 0;
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.route('**/static/auth-config.js', route => route.fulfill({contentType:'text/javascript', body:'window.RipplePublicAuth = ' + JSON.stringify({mode:'neon', url:authUrl})}));
    await page.route(authUrl + '/**', async route => {
      const req = route.request(), url = new URL(req.url());
      let body = null;
      if (url.pathname.endsWith('/get-session') && signedIn) body = {user, session:{id:'fixture-session', userId:user.id, token:'opaque-cookie', expiresAt:new Date(Date.now()+86400000).toISOString(), createdAt:user.createdAt, updatedAt:user.updatedAt}};
      else if (url.pathname.endsWith('/token')) {minted++; body = {token:jwt};}
      else if (url.pathname.endsWith('/sign-out')) {signedIn = false; body = {success:true};}
      await route.fulfill({status:200, headers:{'Content-Type':'application/json', 'Access-Control-Allow-Origin':base, 'Access-Control-Allow-Credentials':'true', 'Access-Control-Allow-Headers':'content-type,neon-auth-client-info', 'Access-Control-Expose-Headers':'set-auth-jwt', ...(signedIn ? {'set-auth-jwt':jwt} : {})}, body:JSON.stringify(body)});
    });
    await page.route(base + '/api/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/api/auth/session') {assert.equal(route.request().headers().authorization, 'Bearer ' + jwt); synchronized++;}
      await route.fulfill({contentType:'application/json', body: JSON.stringify(url.pathname === '/api/tests' ? [] : url.pathname === '/api/config' ? {providers:{groq:true}, maxUploadMB:100, maxDuration:180} : {})});
    });
    await page.goto(base);
    await page.evaluate(() => window.RippleAuth.ready);
    assert.equal(minted, 1); assert.equal(synchronized, 1);
    await page.getByRole('button', {name:'Sign out', exact:true}).click();
    await page.locator('#account-form').waitFor();
    await page.evaluate(() => document.fonts.ready);
    fs.mkdirSync('docs/screenshots', {recursive:true});
    await page.screenshot({path:'docs/screenshots/14-account-signin.png', animations:'disabled'});
    await page.getByRole('button', {name:'Create account', exact:true}).click();
    assert.equal(await page.locator('[name=name]').isVisible(), true);
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(errors, []);
    // Optional read-only check against the configured Neon tenant: no signups,
    // emails or user mutations. It verifies the SDK's anonymous session request.
    if (process.env.RIPPLE_LIVE_AUTH_URL) {
      policy = contentSecurityPolicy(process.env.RIPPLE_LIVE_AUTH_URL);
      await page.unroute(authUrl + '/**');
      await page.unroute('**/static/auth-config.js');
      await page.route('**/static/auth-config.js', route => route.fulfill({contentType:'text/javascript', body:'window.RipplePublicAuth = ' + JSON.stringify({mode:'neon', url:process.env.RIPPLE_LIVE_AUTH_URL})}));
      await page.goto(base);
      await page.locator('#account-form').waitFor({timeout:30000});
      assert.deepEqual(errors, []);
      console.log('PASS: live Neon anonymous session and login screen (no accounts created).');
    }
    console.log('PASS: bundled Neon SDK session, JWT exchange, logout, signup view and mobile layout.');
  } finally {await browser.close(); server.close();}
})().catch(error => {console.error(error.message); server.close(); process.exitCode = 1;});
