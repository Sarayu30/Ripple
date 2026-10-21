// Kept independent of the SDK so account flows can be tested without real accounts.
export function startAuthentication(client, page = window) {
  const {document, location} = page;
  let cached, expires = 0, pending, initialUser;
  const headers = {'X-Ripple-Client': '1'};
  const home = location.origin + '/';
  const logoutCookie = () => page.fetch('/api/auth/logout', {method: 'POST', headers});
  const reload = () => location.replace(home);
  const token = async () => {
    if (cached && expires > Date.now() + 60000) return cached;
    if (pending) return pending;
    pending = (async () => {
      // The pinned Neon SDK consumes this header locally to bypass its session
      // cache; it is removed before the network request. Check revocation anew.
      const fresh = {fetchOptions: {headers: {'X-Force-Fetch': '1'}}};
      const session = await client.getSession({query: {disableCookieCache: true}, ...fresh});
      if (session.error || !session.data?.session || !session.data.user?.emailVerified) {
        cached = null;
        await logoutCookie();
        throw Error('Your session has ended or your email needs verification. Refresh to sign in.');
      }
      if (initialUser && session.data.user.id !== initialUser) { await logoutCookie(); reload(); throw Error('Account changed.'); }
      // /token shares the SDK's session-cache hook; force its actual JWT response.
      const result = await client.token(fresh);
      if (result.error || !result.data?.token) throw Error('Unable to renew your session. Refresh to sign in.');
      // Decode only for refresh timing. The Python API verifies signature and claims.
      let expiry;
      try {
        const payload = result.data.token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        expiry = JSON.parse(page.atob(payload.padEnd(Math.ceil(payload.length / 4) * 4, '='))).exp * 1000;
      } catch { throw Error('The account service returned an invalid session.'); }
      if (!Number.isFinite(expiry) || expiry <= Date.now()) throw Error('Your session has expired. Sign in again.');
      const sync = await page.fetch('/api/auth/session', {method: 'POST', headers: {...headers, Authorization: 'Bearer ' + result.data.token}});
      if (!sync.ok) throw Error('Your session could not be verified. Confirm your email, then sign in again.');
      cached = result.data.token;
      expires = expiry;
      return cached;
    })().finally(() => { pending = null; });
    return pending;
  };

  const ready = (async () => {
    const query = new URLSearchParams(location.search);
    const recoveryToken = query.get('token');
    const recovering = query.get('flow') === 'recovery';
    // Remove recovery credentials from the address bar/history before navigation.
    if (recovering) page.history.replaceState(null, '', '/?flow=recovery');
    let data, unavailable = false;
    try {
      const session = await client.getSession();
      unavailable = Boolean(session.error);
      data = unavailable ? null : session.data;
    } catch { unavailable = true; }
    if (!data?.session || !data.user?.emailVerified || recovering) {
      document.querySelector('.sidebar').inert = true;
      const main = document.querySelector('#main');
      let mode = recovering ? 'recover' : data?.user && !data.user.emailVerified ? 'verify' : 'signin';
      document.body.classList.add('is-landing');
      main.innerHTML = `<div id="public-home"><h1>See how your content could land.</h1><p>Explore audience reactions, compare creative edits, and ask questions grounded in your saved analysis.</p></div><dialog id="account-dialog" aria-labelledby="account-title"><button class="btn account-close" type="button" aria-label="Close account form">Close ×</button><section class="card auth-card"><div class="eyebrow">YOUR PRIVATE RIPPLE WORKSPACE</div>
        <h1 id="account-title">Explore your next idea.</h1>
        <p>Rehearse your content with an AI audience. Your analysis, suggestions and conversations stay in your account. Uploaded videos are deleted after analysis.</p>
        <form id="account-form">
        <label class="field" id="account-name-field" hidden><span>Your name</span><input name="name" autocomplete="name" maxlength="100"></label>
        <label class="field" id="account-email-field"><span>Email</span><input name="email" type="email" autocomplete="email" required></label>
        <label class="field" id="account-password-field"><span>Password</span><input name="password" type="password" autocomplete="current-password" required></label>
        <label class="field" id="account-code-field" hidden><span>Email verification code</span><input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6"></label>
        <p id="account-message" role="status" aria-live="polite"></p><div class="actions">
        <button class="btn primary" id="account-submit" type="submit">Sign in</button>
        <button class="btn" type="button" id="account-signup">Create account</button>
        <button class="btn" type="button" id="account-reset">Forgot password?</button>
        <button class="btn" type="button" id="account-resend" hidden>Send verification code</button>
        <button class="btn" type="button" id="account-back" hidden>Back to sign in</button>
        </div></form></section></dialog>`;
      const dialog = document.querySelector('#account-dialog');
      const form = document.querySelector('#account-form');
      const message = document.querySelector('#account-message');
      const field = name => form.elements.namedItem(name);
      field('email').value = data?.user?.email || '';
      const setMode = next => {
        mode = next;
        const labels = {signin: ['Explore your next idea.', 'Sign in'], signup: ['Make room for your next idea.', 'Create account'],
          reset: ['Find your way back.', 'Send reset email'], recover: ['Choose a new password.', 'Update password'], verify: ['Check your inbox.', 'Verify email']};
        document.querySelector('#account-title').textContent = labels[mode][0];
        document.querySelector('#account-submit').textContent = labels[mode][1];
        for (const name of ['name', 'email', 'password', 'code']) {
          const show = name === 'name' ? mode === 'signup' : name === 'email' ? mode !== 'recover' : name === 'password' ? ['signin','signup','recover'].includes(mode) : mode === 'verify';
          document.querySelector('#account-' + name + '-field').hidden = !show;
          field(name).disabled = !show;
          field(name).required = show;
        }
        field('password').minLength = mode === 'signin' ? 1 : 12;
        field('password').autocomplete = mode === 'signin' ? 'current-password' : 'new-password';
        document.querySelector('#account-signup').hidden = mode !== 'signin';
        document.querySelector('#account-reset').hidden = mode !== 'signin';
        document.querySelector('#account-resend').hidden = !['signin', 'verify'].includes(mode);
        document.querySelector('#account-back').hidden = mode === 'signin';
        message.textContent = '';
      };
      const act = async kind => {
        if (kind === 'resend' ? !field('email').reportValidity() : !form.reportValidity()) return;
        form.querySelectorAll('button').forEach(button => button.disabled = true);
        message.textContent = 'Please wait…';
        try {
          const email = field('email').value.trim(), password = field('password').value;
          let result;
          if (kind === 'reset') result = await client.requestPasswordReset({email, redirectTo: home + '?flow=recovery'});
          else if (kind === 'recover') {
            if (!recoveryToken || query.has('error')) throw Error('Invalid recovery link.');
            result = await client.resetPassword({newPassword: password, token: recoveryToken});
          } else if (kind === 'signup') result = await client.signUp.email({email, password, name: field('name').value.trim(), callbackURL: home});
          else if (kind === 'verify') result = await client.emailOtp.verifyEmail({email, otp: field('code').value.trim()});
          else if (kind === 'resend') result = await client.emailOtp.sendVerificationOtp({email, type: 'email-verification'});
          else result = await client.signIn.email({email, password, callbackURL: home});
          if (result.error) throw result.error;
          field('password').value = '';
          if (kind === 'signin') { reload(); return; }
          if (kind === 'signup' || kind === 'resend') {
            setMode('verify');
            message.textContent = 'Check your email for a verification code or link. Enter the code here, or open the link and sign in.';
          } else if (kind === 'verify' || kind === 'recover') {
            setMode('signin');
            message.textContent = kind === 'verify' ? 'Email verified. You can now sign in.' : 'Password updated. Sign in with your new password.';
          } else message.textContent = 'If an account matches, a recovery email will arrive shortly.';
        } catch (error) {
          const code = error?.code;
          const messages = {
            INVALID_EMAIL_OR_PASSWORD: 'The email and password do not match an account. Use the same email you registered with, or choose Forgot password.',
            EMAIL_NOT_VERIFIED: 'Verify your email before signing in. Enter your code below, or choose Send verification code.',
            INVALID_CALLBACK_URL: 'This website address is not approved for sign-in. Open the published Ripple website or contact support.',
            INVALID_ORIGIN: 'This website address is not approved for sign-in. Open the published Ripple website or contact support.',
            PASSWORD_TOO_SHORT: 'Use a password with at least 12 characters.',
            PASSWORD_TOO_LONG: 'This password exceeds the account service limit. Choose a shorter password.',
            USER_ALREADY_EXISTS: 'Try signing in or recovering your password for this email.',
            USER_ALREADY_EXISTS_USE_ANOTHER_EMAIL: 'Try signing in or recovering your password for this email.',
            INVALID_OTP: 'That verification code is invalid or expired. Request a new code and try again.',
            OTP_EXPIRED: 'That verification code has expired. Request a new code.',
            SIGNUP_DISABLED: 'New account registration is currently unavailable. Contact the workspace operator.',
          };
          if (code === 'EMAIL_NOT_VERIFIED') { field('password').value = ''; setMode('verify'); }
          message.textContent = messages[code] || (error?.status === 429 ? 'Too many attempts. Please wait a few minutes before trying again.'
            : error?.status === 401 ? messages.INVALID_EMAIL_OR_PASSWORD
            : error instanceof TypeError ? 'The account service could not be reached. Check your connection and try again.'
            : kind === 'recover' ? 'This recovery link may have expired. Go back and request a new one.'
            : 'The account service could not complete this request. Please try again shortly.');
        } finally { form.querySelectorAll('button').forEach(button => button.disabled = false); }
      };
      form.onsubmit = event => { event.preventDefault(); act(mode); };
      document.querySelector('#account-signup').onclick = () => setMode('signup');
      document.querySelector('#account-reset').onclick = () => setMode('reset');
      document.querySelector('#account-back').onclick = () => setMode('signin');
      document.querySelector('#account-resend').onclick = () => act('resend');
      setMode(mode);
      const openAccount = next => {
        setMode(next);
        if (!dialog.open) dialog.showModal();
        field(next === 'recover' ? 'password' : next === 'signup' ? 'name' : 'email').focus();
      };
      page.RippleGuest = {open: openAccount};
      document.querySelector('.account-close').onclick = () => dialog.close();
      dialog.addEventListener('close', () => { field('password').value = ''; field('code').value = ''; });
      const renderPublicHome = () => page.RippleExperience?.landing(document.querySelector('#public-home'));
      renderPublicHome();
      document.documentElement.classList.remove('app-booting');
      page.addEventListener('ripple-experience-ready', renderPublicHome, {once: true});
      if (recovering || mode === 'verify') openAccount(mode);
      if (unavailable) message.textContent = 'Unable to reach the sign-in service. You can try signing in again, or refresh this page.';
      await new Promise(() => {});
    }
    initialUser = data.user.id;
    await token();
    const button = document.createElement('button');
    button.className = 'btn auth-signout'; button.textContent = 'Sign out';
    button.onclick = async () => {
      button.disabled = true;
      cached = null; expires = 0;
      try {
        const result = await client.signOut();
        if (result.error) throw result.error;
        const response = await logoutCookie();
        if (!response.ok) throw Error('Sign out failed.');
        reload();
      } catch { button.disabled = false; button.textContent = 'Retry sign out'; }
    };
    // The landing page hides the workspace header; keep account access available.
    document.body.append(button);
    // Keep protected video/report links usable as the short-lived JWT rotates.
    page.setInterval(() => token().catch(() => {}), 60000);
    page.addEventListener('focus', () => { expires = 0; token().catch(() => {}); });
  })();
  ready.catch(() => {});
  return {ready, token};
}
