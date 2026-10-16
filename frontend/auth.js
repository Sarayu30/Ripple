import {createAuthClient} from '@neondatabase/neon-js/auth';
import {startAuthentication} from './auth-flow.mjs';

const options = window.RipplePublicAuth || {mode: 'local'};
let session;
const ready = (async () => {
  if (options.mode === 'local') return;
  if (options.mode !== 'neon' || !/^https:\/\/[a-z0-9-]+(?:\.[a-z0-9-]+)*\.neon\.(tech|build)\/[A-Za-z0-9_-]+\/auth$/.test(options.url)) {
    throw new Error('Account setup is incomplete. Contact the workspace operator.');
  }
  // The official client manages Neon cookies. No database/API secret enters this bundle.
  session = startAuthentication(createAuthClient(options.url));
  await session.ready;
})();
ready.catch(() => {});
window.RippleAuth = {ready, token: async () => session ? session.token() : null};
