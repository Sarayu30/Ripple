import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {startAuthentication} from '../frontend/auth-flow.mjs';

const tick = () => new Promise(resolve => setTimeout(resolve, 0));
test('session network failure keeps sign-in visible and workspace locked', async () => {
  const f = fixture();
  f.client.getSession = async () => { throw new TypeError('Failed to fetch'); };
  let unlocked = false;
  startAuthentication(f.client, f.page).ready.then(() => { unlocked = true; });
  await tick();
  assert.ok(f.page.document.querySelector('#account-form'));
  assert.equal(f.page.document.querySelector('.sidebar').inert, true);
  assert.match(f.page.document.querySelector('#account-message').textContent, /Unable to reach/);
  f.click('signup');
  assert.equal(f.field('name').disabled, false);
  assert.equal(unlocked, false);
  assert.equal(f.calls.length, 0);
  f.dom.window.close();
});
function fixture(url = 'https://ripple.example/') {
  const dom = new JSDOM('<aside class="sidebar"></aside><div class="header-right"></div><main id="main"></main>', {url});
  dom.window.HTMLDialogElement.prototype.showModal = function() { this.open = true; };
  dom.window.HTMLDialogElement.prototype.close = function() { this.open = false; };
  const calls = [];
  const ok = name => async args => { calls.push([name, args]); return {data: {}, error: null}; };
  const client = {getSession: async () => ({data: null}), signUp: {email: ok('signup')}, signIn: {email: ok('signin')},
    requestPasswordReset: ok('requestReset'), resetPassword: ok('reset'), emailOtp: {verifyEmail: ok('verify'), sendVerificationOtp: ok('resend')}};
  const redirects = [];
  const page = {document: dom.window.document, location: {origin: dom.window.location.origin, search: dom.window.location.search, replace: url => redirects.push(url)},
    history: dom.window.history, atob: dom.window.atob.bind(dom.window), fetch: async (url, options) => {calls.push([url, options]); return {ok: true};},
    setInterval() {}, addEventListener() {}};
  return {dom, page, client, calls, redirects, field: name => page.document.querySelector(`[name="${name}"]`),
    click: id => page.document.querySelector('#account-' + id).click()};
}

test('signup verifies email and recovery needs only an email address', async () => {
  const f = fixture(); startAuthentication(f.client, f.page); await tick();
  f.click('signup'); f.field('name').value = 'Test Creator'; f.field('email').value = 'test@example.com'; f.field('password').value = 'a-long-fixture-password';
  f.click('submit'); await tick();
  assert.equal(f.calls[0][0], 'signup'); assert.equal(f.calls[0][1].name, 'Test Creator');
  assert.equal(f.field('password').disabled, true);
  f.field('code').value = '123456'; f.click('submit'); await tick();
  assert.deepEqual(f.calls[1], ['verify', {email: 'test@example.com', otp: '123456'}]);
  f.click('reset'); assert.equal(f.field('password').disabled, true);
  f.click('submit'); await tick();
  assert.deepEqual(f.calls[2], ['requestReset', {email: 'test@example.com', redirectTo: 'https://ripple.example/?flow=recovery'}]);
  f.dom.window.close();
});

test('public landing keeps account form closed until requested', async () => {
  const f = fixture(); startAuthentication(f.client, f.page); await tick();
  assert.equal(f.page.document.querySelector('#account-dialog').open, false);
  assert.ok(f.page.document.querySelector('#public-home'));
  f.page.RippleGuest.open('signup');
  assert.equal(f.page.document.querySelector('#account-dialog').open, true);
  assert.equal(f.field('name').disabled, false);
  assert.equal(f.calls.length, 0);
  f.dom.window.close();
});

test('sign-in distinguishes rejected credentials from unverified email', async () => {
  for (const code of ['INVALID_EMAIL_OR_PASSWORD', 'EMAIL_NOT_VERIFIED']) {
    const f = fixture();
    f.client.signIn.email = async () => ({error:{code,status:code==='EMAIL_NOT_VERIFIED'?403:401,message:'private provider details'}});
    startAuthentication(f.client, f.page); await tick();
    f.page.RippleGuest.open('signin');
    f.field('email').value='fixture@example.com'; f.field('password').value='fixture-password';
    f.click('submit'); await tick();
    const message=f.page.document.querySelector('#account-message').textContent;
    assert.match(message, code==='EMAIL_NOT_VERIFIED' ? /Verify your email/ : /email and password do not match/);
    assert.ok(!message.includes('private provider details'));
    assert.equal(f.field('code').disabled, code!=='EMAIL_NOT_VERIFIED');
    if(code==='EMAIL_NOT_VERIFIED') assert.equal(f.field('password').value,'');
    f.dom.window.close();
  }
});

test('recovery removes token from address bar and submits it only to auth', async () => {
  const f = fixture('https://ripple.example/?flow=recovery&token=recovery-fixture');
  startAuthentication(f.client, f.page); await tick();
  assert.ok(!f.dom.window.location.search.includes('token'));
  f.field('password').value = 'new-fixture-password'; f.click('submit'); await tick();
  assert.deepEqual(f.calls[0], ['reset', {newPassword: 'new-fixture-password', token: 'recovery-fixture'}]);
  assert.ok(f.page.document.querySelector('#account-message').textContent.includes('Password updated'));
  f.dom.window.close();
});

test('signed-in requests deduplicate JWT refresh and synchronize media cookie', async () => {
  const f = fixture(); const session = {session: {token: 'opaque-cookie'}, user: {id: 'alice', emailVerified: true}};
  f.client.getSession = async () => ({data: session});
  const jwt = 'header.' + Buffer.from(JSON.stringify({exp: Math.floor(Date.now()/1000) + 900})).toString('base64url') + '.signature';
  let minted = 0;
  f.client.token = async options => { assert.equal(options.fetchOptions.headers['X-Force-Fetch'], '1'); minted++; await tick(); return {data: {token: jwt}}; };
  const auth = startAuthentication(f.client, f.page); await auth.ready;
  assert.deepEqual(await Promise.all([auth.token(), auth.token()]), [jwt, jwt]);
  assert.equal(minted, 1);
  assert.equal(f.calls[0][0], '/api/auth/session');
  assert.equal(f.calls[0][1].headers.Authorization, 'Bearer ' + jwt);
  f.dom.window.close();
});

test('unverified accounts never receive access to the application', async () => {
  const f = fixture(); f.client.getSession = async () => ({data: {session: {}, user: {id:'alice', email:'test@example.com', emailVerified:false}}});
  startAuthentication(f.client, f.page); await tick();
  assert.equal(f.page.document.querySelector('#account-title').textContent, 'Check your inbox.');
  assert.equal(f.calls.length, 0);
  f.dom.window.close();
});
