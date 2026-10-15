import {createClient} from '@supabase/supabase-js';

let client;
const options = window.RipplePublicAuth || {mode: 'local'};
const ready = (async () => {
  if (options.mode !== 'supabase') return;
  if (!/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(options.url) || !options.publishableKey?.startsWith('sb_publishable_')) {
    throw new Error('Account setup is incomplete. Contact the workspace operator.');
  }
  client = createClient(options.url, options.publishableKey, {
    auth: {flowType: 'pkce', detectSessionInUrl: true, persistSession: true, autoRefreshToken: true},
  });
  let recover = new URLSearchParams(location.search).get('flow') === 'recovery';
  let initialUser;
  client.auth.onAuthStateChange((event, session) => {
    if (event === 'PASSWORD_RECOVERY') recover = true;
    if (initialUser && (!session || session.user.id !== initialUser)) location.reload();
  });
  const {data, error} = await client.auth.getSession();
  if (error) throw new Error('Sign-in could not be restored. Refresh and sign in again.');
  if (!data.session || recover) {
    document.querySelector('.sidebar').inert = true;
    const main = document.querySelector('#main');
    main.innerHTML = `<section class="card auth-card"><div class="eyebrow">YOUR PRIVATE RIPPLE WORKSPACE</div>
      <h1>${recover ? 'Choose a new password.' : 'Explore your next idea.'}</h1>
      <p>Sign in or create an account. Your simulations, videos and conversations belong to your account.</p>
      <form id="account-form"><label class="field" ${recover ? 'hidden' : ''}><span>Email</span><input name="email" type="email" autocomplete="email" ${recover ? '' : 'required'}></label>
      <label class="field"><span>Password</span><input name="password" type="password" autocomplete="${recover ? 'new-password' : 'current-password'}" minlength="12" required></label>
      <p id="account-message" role="status" aria-live="polite"></p><div class="actions">
      <button class="btn primary" type="submit">${recover ? 'Update password' : 'Sign in'}</button>
      ${recover ? '' : '<button class="btn" type="button" id="account-signup">Create account</button><button class="btn" type="button" id="account-reset">Forgot password?</button>'}
      </div></form></section>`;
    const form = document.querySelector('#account-form');
    const message = document.querySelector('#account-message');
    const act = async kind => {
      if (kind !== 'reset' && !form.reportValidity()) return;
      if (kind === 'reset' && !form.elements.email.reportValidity()) return;
      form.querySelectorAll('button').forEach(button => button.disabled = true);
      message.textContent = 'Please wait…';
      try {
        const email = form.elements.email.value.trim(), password = form.elements.password.value;
        const result = kind === 'reset'
          ? await client.auth.resetPasswordForEmail(email, {redirectTo: location.origin + '/?flow=recovery'})
          : kind === 'signup'
          ? await client.auth.signUp({email, password, options: {emailRedirectTo: location.origin + '/'}})
          : kind === 'recover'
          ? await client.auth.updateUser({password})
          : await client.auth.signInWithPassword({email, password});
        if (result.error) throw result.error;
        form.elements.password.value = '';
        if (kind === 'recover' || result.data?.session) { location.replace(location.origin + '/'); return; }
        message.textContent = kind === 'reset'
          ? 'If an account matches, a recovery email will arrive shortly. Open it in this browser.'
          : 'Check your email to confirm your account. Open the confirmation in this browser, then sign in.';
      } catch {
        message.textContent = 'Unable to complete this request. Check your details and try again, or use password recovery.';
      } finally { form.querySelectorAll('button').forEach(button => button.disabled = false); }
    };
    form.onsubmit = event => { event.preventDefault(); act(recover ? 'recover' : 'signin'); };
    if (!recover) {
      document.querySelector('#account-signup').onclick = () => act('signup');
      document.querySelector('#account-reset').onclick = () => act('reset');
    }
    await new Promise(() => {});
  }
  initialUser = data.session.user.id;
  const synchronize = async session => {
    const result = await fetch('/api/auth/session', {method: 'POST', headers: {
      Authorization: 'Bearer ' + session.access_token, 'X-Ripple-Client': '1',
    }});
    if (!result.ok) throw new Error('Your session could not be verified. Sign in again or contact the operator.');
  };
  // HttpOnly same-origin cookie protects media and report links as well as fetches.
  await synchronize(data.session);
  client.auth.onAuthStateChange((event, session) => {
    if (event === 'TOKEN_REFRESHED' && session) setTimeout(() => synchronize(session).catch(() => {}), 0);
  });
  const button = document.createElement('button');
  button.className = 'btn'; button.textContent = 'Sign out';
  button.onclick = async () => {
    button.disabled = true;
    try {
      await fetch('/api/auth/logout', {method: 'POST', headers: {'X-Ripple-Client': '1'}});
      await client.auth.signOut({scope: 'local'});
      location.replace(location.origin + '/');
    } catch { button.disabled = false; button.textContent = 'Retry sign out'; }
  };
  document.querySelector('.header-right').prepend(button);
})();
ready.catch(() => {});
window.RippleAuth = {ready, token: async () => client ? (await client.auth.getSession()).data.session?.access_token : null};
