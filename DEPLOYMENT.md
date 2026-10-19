# Deploy Ripple with Vercel, Render Free and Neon

Ripple supports public signup through **Neon Auth (Managed Better Auth)** and keeps application records in **Neon PostgreSQL**. Every simulation is assigned to the verified account that created it. There is no Supabase project or Clerk application to configure.

The repository is prepared for deployment, but a successful build is not a completed production launch. Follow the acceptance checks below on the actual published domains.

## What runs where?

| Component | Host | Responsibility |
| --- | --- | --- |
| Website | Vercel | Static UI, public Auth URL, same-origin API routing |
| Accounts | Neon Auth | Signup, login, email verification, recovery and sessions |
| Application database | Neon PostgreSQL | Account-owned simulations, results, usage records and checkpoints |
| Python API and queue | Render Free web service, Docker runtime | Groq calls, FFmpeg and queued execution |
| Temporary media | Backend's temporary disk | Uploaded video, sampled images and audio, deleted after analysis |
| Saved research | Neon PostgreSQL | Text observations, chat, replay history and version metadata |

**Vercel hosts the frontend.** Video processing uses FFmpeg and simulations can outlive ordinary requests, so the Python process runs on Render. Do not deploy it as a Vercel Function. See [Vercel's function limits](https://vercel.com/docs/functions/limitations). Visitors use one Vercel website address; the owner's computer is not a server.

Run exactly **one instance with one Uvicorn worker**. The PostgreSQL ownership lock intentionally prevents two backend processes from running against the same application schema. Stop the old instance before replacing it; rolling deployments with overlapping instances are not supported. Disable automatic deployment while validating a first release.

### Temporary uploads, saved results

Use Vercel's free website tier, **Render Free**, and the existing Neon project. No object-storage service or persistent disk is needed. Check each account's plan and quotas; no paid resource is required by this configuration.

Uploads, extracted frames and audio exist temporarily in `DATA_DIR`. Once text observations are saved in PostgreSQL, the source files are deleted. Failed/cancelled processing also removes media; a periodic cleanup retries failed deletions. Saved simulations have no original video playback or image gallery. Reports, suggestions, chat, replay events and hypothetical versions use saved text and remain available after disk loss. This does not alter Groq's retention policies.

If Render restarts before content observations are saved, the missing upload cannot be reconstructed: Ripple marks the run as needing a fresh upload. Once observations are saved, downstream stages can resume from PostgreSQL. Legacy JSON caches are imported on startup when the old disk is present; existing local results retain their owner.

Render Free also sleeps after 15 minutes without traffic and takes about a minute to wake. The service can be suspended when free quotas are exhausted; review the current [free-tier rules](https://render.com/docs/free). The existing public Neon Auth URL and application database can remain unchanged.

## 1. Enable Neon Auth

1. Open your Neon project and production branch. Open **Better Auth / Neon Auth** and enable the service.
2. Choose the database for authentication. A separate database named `auth` is valid, but naming a database does not itself enable authentication. Neon manages its own `neon_auth` schema. Keep `DATABASE_URL` pointing to the existing application database; changing it would select different application records.
3. In **Configuration**, copy the **Auth Base URL**. It looks like `https://YOUR-ENDPOINT.neonauth.REGION.aws.neon.tech/auth/auth`; the first `auth` is the database name, so `/auth/auth` can be correct.
4. Enable **Sign-up with Email** and **Verify at Sign-up**. Use verification codes for the shared development email service. Ripple supports entering these codes, resending a code, and returning from a verification link. Links require your own SMTP provider.
5. Add the exact published website origin to trusted domains. Avoid broad preview-domain wildcards. Allow localhost only on your development branch.
6. Set the application name to Ripple and configure your own SMTP sender before a public launch. Test delivery and recovery using a real inbox you control.

Only `NEON_AUTH_BASE_URL` is public. Ripple does not need a Neon admin API key or database password in the browser. See Neon's [React setup](https://neon.com/docs/auth/quick-start/react), [email verification](https://neon.com/docs/auth/guides/email-verification), and [production checklist](https://neon.com/docs/auth/production-checklist).

## 2. Configure the backend

In Render choose **New → Web Service**, connect GitHub, and select the Ripple repository. Set branch **version_2**, runtime **Docker**, root directory blank, Dockerfile path **./Dockerfile**, and instance type **Free ($0/month)**. The Docker image already includes FFmpeg and creates the writable temporary directory `/app/data`. Do not add a disk or a Render database.

Under Advanced, use health check path **/healthz**. Leave the Docker command unset; the image starts one Uvicorn worker on Render's `PORT` (default `10000`). Using the assigned port avoids a port-discovery restart colliding with the running worker's database lock. Keep Auto-Deploy off for the initial release. If deploying from a Blueprint instead, `render.yaml` declares only a Free web service.

Set these environment variables through the hosting dashboard, never in a Git commit:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Existing Neon application connection string with TLS enabled |
| `DATABASE_SCHEMA` | `ripple`, or your existing application schema |
| `GROQ_API_KEY` | Server-only provider key |
| `AUTH_MODE` | `neon` |
| `NEON_AUTH_BASE_URL` | The public URL copied above |
| `APP_ENV` | `production` |
| `PUBLIC_ORIGIN` | Exact Vercel production origin, for example `https://ripple.example.com` |
| `ALLOWED_HOSTS` | Public website hostname, e.g. `ripple-rust-phi.vercel.app`; Render's own `RENDER_EXTERNAL_HOSTNAME` is added automatically |
| `ORIGIN_SECRET` | A randomly generated value with at least 32 characters; use the same value in Vercel |
| `DATA_DIR` | `/app/data` |
| `JOB_MODE` | `durable` |
| `MAX_RUNNING_JOBS` | `1` for the Free service |
| `AGENT_CONCURRENCY` | `1` |
| `REQUEST_INTERVAL_SECONDS` | `4` |
| `MAX_UPLOAD_MB` | `25` as a conservative initial Free-service limit |

Keep provider model names and limits from `.env.example`. Never place a key in a model-name field. The backend rejects incomplete production configuration rather than starting without protection.

The application uses a bounded Psycopg pool and direct Neon connections for session settings and worker locking. Existing Neon `-pooler` URLs are normalized to the corresponding direct endpoint internally. Account records stay in the Auth database; application queries continue using the application schema.

Generate `ORIGIN_SECRET` with a password manager and paste it directly into both dashboards. Never use a `NEXT_PUBLIC_`, `VITE_`, or other public-variable prefix for credentials. The backend denies requests that bypass Vercel's origin-secret header.

After deploying, wait for **Live**, then open `https://YOUR-SERVICE.onrender.com/healthz`. It should return `{"status":"ready"}`. The backend root intentionally returns 403: visitors should use Vercel. Copy only the public Render origin into Vercel's `RIPPLE_BACKEND_ORIGIN`.

## 3. Configure Vercel

Import the GitHub repository and select the intended branch (`version_2` currently contains this work). The repository includes `vercel.json`, `.vercelignore`, and a Build Output API generator. Use the repository root and the supplied build configuration.

Set only these deployment variables on Vercel:

| Variable | Visibility/use |
| --- | --- |
| `NEON_AUTH_BASE_URL` | Public browser configuration |
| `RIPPLE_BACKEND_ORIGIN` | HTTPS backend origin, without a path, password or custom port |
| `ORIGIN_SECRET` | Sensitive server-side routing variable; never bundled into public assets |

**Do not put `DATABASE_URL`, `GROQ_API_KEY`, SMTP credentials or Neon admin keys in Vercel.** This frontend does not need them. The artifact copies an explicit list of static file types; it excludes `.env`, Python source, private media and application data. The routing configuration references the origin secret by environment variable name, not by its value. API responses disable CDN caching.

Use a separate Neon branch and backend for previews. Do not route untrusted preview builds into the production API. This architecture uses a single `PUBLIC_ORIGIN`; a preview requires its own matching configuration and Neon trusted domain.

## 4. Verify before opening public signup

- Create two accounts through the deployed UI, verify both emails, sign in, sign out, and reset a password. Verify that neither account can retrieve the other's simulation URL, export, report, chat, or comparison.
- Test on desktop Chrome, mobile and Safari with ordinary privacy settings. Neon uses cross-origin cookies in this integration; browsers that block third-party cookies may need a same-site Auth domain/proxy design. That deployment change is not implemented here. Do not ask users to weaken browser privacy settings as a permanent workaround.
- Submit a small video with explicit consent. Confirm upload, processing, replay, chat and export through the actual Vercel proxy. Test a near-limit upload. Provider calls incur usage; use a test account and small viewer panel.
- Restart after content analysis and verify that saved work resumes with an empty temporary disk. Restart before content analysis and verify a clear re-upload message. Cancel a queued/running job, then delete it and check removal of its saved records.
- Confirm that direct backend application routes are denied (only `/healthz` is public), private API responses are not cached, and no credential appears in downloaded JavaScript or public configuration.
- Back up PostgreSQL and rehearse restoring it. Temporary media is intentionally excluded. Set quota alerts and an operational owner. Free hosting is suitable for a limited demo, not guaranteed production uptime; Render may sleep or suspend usage when free allowances are exhausted.

Neon JWTs are verified using the tenant's public JWKS, exact issuer/audience, EdDSA signature and expiry. Ripple also requires a verified email and rejects banned/anonymous claims. Access JWTs remain valid until expiry (normally 15 minutes); sign-out clears the browser session and Ripple cookie but cannot revoke an already copied JWT instantly. See [Neon's JWT guide](https://neon.com/docs/auth/guides/plugins/jwt).

## Limits and recovery

The default admission limits are 2 active jobs per account, 8 queued/running jobs globally, 100 saved simulations per account, 500 viewer units per account per rolling 24 hours (2,000 globally), and 30 chat requests per account (200 globally). Retries consume another viewer allowance. Deleting a simulation does not reset usage. These limits bound requests, not provider dollar cost. Configure account-level provider spending limits too.

`JOB_MODE=durable` persists the queue in PostgreSQL and resumes running records after an exclusive backend restart. Saved checkpoints prevent completed stages from being discarded, but an interrupted provider request may be billed again. Failed media deletion retains a retryable record instead of claiming success.

Existing local simulations retain the `local` owner. Public accounts are **not** automatically granted access to them. Any ownership migration must be an explicit, backed-up administrative operation.

## Remaining production work

This is a deployment candidate, not a claim of completed SaaS operations. Remaining work includes live acceptance checks above, browser-compatible Auth hosting, custom email delivery, infrastructure monitoring/alerting, tested backups, stronger abuse controls/CAPTCHA and IP limits, retention/account-deletion procedures, and legal/privacy policies appropriate to your service. There is no distributed worker fleet, object storage, billing system, automatic disaster recovery, or empirical calibration of the AI predictions. The Neon SDK is pinned to its current beta release; review updates and repeat the authentication suite before upgrading.

Run local checks with `npm run build`, `npm run test:auth`, `npm run test:auth-browser`, `npm run test:deploy`, `npm run test:ui`, `npm run test:browser`, and `python -m pytest`. Backend tests create and remove a unique test schema and never select the application schema. CI uses a disposable PostgreSQL service and needs no production secrets.
