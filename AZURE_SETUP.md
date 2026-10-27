# Azure Setup Guide — Kesser Financial Dashboard (live app)

This is a plain-language, step-by-step guide to creating the Azure
resources this app needs. It deliberately mirrors the pattern already
proven out by the Medicare Dashboard app (`jrobertsaperioncare/Medicare-Dashboard2`)
but keeps Kesser's data and logins fully separate from it — a new,
dedicated database (not the Medicare dashboard's), a new sign-in app
registration, and a new deploy identity. The one thing it shares is the
existing `aperion-care-sql` SQL *server* (reusing it is simpler to manage
and you're on the same ownership anyway) — but a shared server is just a
shared login endpoint; the actual data lives in a separate database that
only Kesser's own identity can reach, so nothing about "same server" means
shared data or shared logins.

No step here requires coding. It's all clicking through the Azure Portal
(portal.azure.com) plus a couple of copy-paste commands. Each step says who
does it (you, if you have Azure "Contributor" rights on the subscription, or
whoever on your team manages Azure — your IT/ops teammate).

---

## The pieces, in plain English

| Resource | What it actually is | Analogy |
|---|---|---|
| **Resource Group** | A folder that groups related Azure resources together | A labeled folder holding everything for this one app |
| **Static Web App** | Hosts the website files (HTML/CSS/JS) and handles sign-in | The "front door" — what you type a URL into |
| **Function App** | Runs the backend code that answers data requests | The "kitchen" — does the work behind the scenes |
| **SQL Server + Database** | Where the actual financial data lives | The filing cabinet (server) and one folder in it (database) |
| **Managed Identity** | A robot account Azure uses so the Function App can prove who it is to the database and to GitHub, with no stored password | A keycard instead of a written-down password |
| **Entra App Registration** | Tells Microsoft "this is the Kesser app, let Aperion employees sign into it with their work account" | The guest list for who's allowed in, tied to a specific front door |

---

## Step 0 — Decide the names (already decided below)

Azure requires some names to be **globally unique** (Static Web Apps, Function
Apps, SQL Server names) — nobody else in the world can have already taken
them. The names below are proposed; if any is already taken, Azure will say
so when you try to create it, and you just add a suffix (e.g. `-2` or your
company initials).

| Resource | Proposed name |
|---|---|
| Resource Group | `kesser-dashboard-rg` (for the new resources below; the database itself lives in whatever resource group `aperion-care-sql` is already in — `45-AZRGx`, per your screenshot) |
| Region | Central US (matches your other app — keeps things close to your team/data) |
| SQL Server | `aperion-care-sql` (existing — reused, not new) |
| SQL Database | `kesser-financial-db` (new database on that existing server) |
| Function App | `kesser-dashboard-api` |
| Static Web App | `kesser-financial-dashboard` |
| Managed Identity (GitHub deploy) | `gh-deploy-kesser-dashboard` |
| Entra App Registration | `Kesser Financial Dashboard` |

---

## Step 1 — Create the Resource Group

1. Azure Portal → search "Resource groups" → **+ Create**
2. Subscription: your existing one (same as the Medicare dashboard's)
3. Resource group name: `kesser-dashboard-rg`
4. Region: Central US
5. Review + Create

---

## Step 2 — Add a new database to the existing SQL server

This reuses the existing `aperion-care-sql` server (same ownership, simpler
to manage) but creates a brand-new, separate database on it — Kesser's data
lives in its own database (`kesser-financial-db`), completely apart from
the Medicare dashboard's `reimbursement-db`. In Step 5 below, Kesser's
Function App gets its own identity that is granted access to *only*
`kesser-financial-db` — it has no ability to see or touch `reimbursement-db`,
and vice versa. Same server (same login endpoint), fully separate data and
fully separate logins.

1. Azure Portal → search "SQL databases" → **+ Create**
2. Resource group: whichever one `aperion-care-sql` is already in (`45-AZRGx`
   per your screenshot)
3. Database name: `kesser-financial-db`
4. Server: select the **existing** `aperion-care-sql` server from the
   dropdown (do not create a new one)
5. Compute + storage: choose **Serverless** tier, smallest size (General
   Purpose, 1 vCore, auto-pause after 1 hour of inactivity) — this is the
   cheapest option and auto-pauses when nobody's using it, which fits a
   small internal dashboard well. You can scale it up later with no data
   loss if it's ever too slow.
6. Review + Create

(No new server, no new authentication setup needed — `aperion-care-sql` is
already configured for Entra-only authentication, since that's how the
Medicare dashboard's Function App already connects to it with no stored
password. The new database automatically uses the same setup.)

---

## Step 3 — Create the Function App (backend)

1. Azure Portal → search "Function App" → **+ Create**
2. Resource group: `kesser-dashboard-rg`
3. Function App name: `kesser-dashboard-api`
4. Runtime stack: **Node.js**, version 20
5. Region: Central US
6. Hosting: **Flex Consumption** or **Consumption (Serverless)** plan —
   cheapest option, scales to zero when nobody's using it. (The Medicare
   dashboard uses a Premium plan for performance reasons; this app can start
   on Consumption and move to Premium later if it's ever too slow to wake up.)
7. Review + Create
8. Once created: go to the Function App → **Identity** (left menu) → under
   "System assigned" → switch **Status to On** → Save. This gives the
   Function App its own Managed Identity (its "keycard") — note isn't
   needed here, just leave it on; we'll use it in Step 5.

---

## Step 4 — Create the Static Web App (frontend)

1. Azure Portal → search "Static Web Apps" → **+ Create**
2. Resource group: `kesser-dashboard-rg`
3. Name: `kesser-financial-dashboard`
4. Plan type: **Standard** (Free tier doesn't support linking a standalone
   Function App as the backend, which is the pattern we're copying)
5. Region: Central US
6. Deployment source: choose **"Other"** (not GitHub, for now — we'll wire
   up the GitHub Actions deploy separately in Step 6 so it's scoped
   correctly rather than using the auto-generated, overly-broad token flow)
7. Review + Create
8. Once created: go to the Static Web App → **APIs** (left menu) → **Link**
   → select the `kesser-dashboard-api` Function App from Step 3. This is
   what connects the frontend and backend together (same pattern as
   `aperion-medicare-dashboard` + `prod-function-app-webapp-cus`).

---

## Step 5 — Let the Function App talk to the database (no password)

This step lets the Function App's Managed Identity (its "keycard" from Step
3) log into the database — so the app never stores a SQL password anywhere.

1. Go to the SQL Database (`kesser-financial-db`) → **Query editor** in the
   left menu → sign in with your Entra admin account (set in Step 2)
2. Run this, replacing nothing (the Function App's name IS its identity name):
   ```sql
   CREATE USER [kesser-dashboard-api] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [kesser-dashboard-api];
   ALTER ROLE db_datawriter ADD MEMBER [kesser-dashboard-api];
   ```
3. Go to the Function App → **Configuration** → **Application settings** →
   add two new settings:
   - `SQL_SERVER` = `aperion-care-sql.database.windows.net`
   - `SQL_DATABASE` = `kesser-financial-db`
4. Save (this restarts the Function App, which is expected)

---

## Step 6 — Set up sign-in (Entra / company Microsoft accounts)

This lets your named colleagues sign in with their normal Aperion work
(Microsoft) account — no separate password to create or remember.

1. Azure Portal → search "App registrations" → **+ New registration**
2. Name: `Kesser Financial Dashboard`
3. Supported account types: **"Accounts in this organizational directory
   only (Aperion Care only — Single tenant)"**
4. Redirect URI: leave blank for now (we'll add it once the Static Web
   App's URL is known — it looks like
   `https://<your-app-name>.azurestaticapps.net/.auth/login/aad/callback`)
5. Register
6. On the app's page, copy the **Application (client) ID** — you'll need
   this for Step 7.
7. Left menu → **Certificates & secrets** → **New client secret** → copy
   the secret **value** immediately (it's only shown once).
8. Left menu → **Authentication** → **Add a platform** → **Web** → paste
   in the redirect URI from step 4 once you know the Static Web App's
   default hostname (visible on the Static Web App's Overview page).

Keep the Client ID and secret value somewhere safe for now — they get
added as settings on the Static Web App (not committed to code or sent to
me), covered in Step 7.

---

## Step 7 — Set up the GitHub deploy identity (what lets pushes auto-deploy)

This is the "robot account" that GitHub Actions uses to push new code to
Azure, with no stored password — it proves who it is using a trust
relationship with GitHub directly (OIDC).

1. Azure Portal → search "Managed Identities" → **+ Create**
2. Resource group: `kesser-dashboard-rg`
3. Name: `gh-deploy-kesser-dashboard`
4. Region: Central US
5. Review + Create
6. Open the new identity → **Federated credentials** → **+ Add credential**
   - Scenario: **GitHub Actions deploying Azure resources**
   - Organization: `morielhamui`
   - Repository: `Kesser_Financial_Dashboard`
   - Entity type: **Branch**
   - Branch name: `main` (or whichever branch should deploy to production —
     let me know if you want this scoped to `claude/youthful-darwin-fa0gmz`
     instead while the app is still being actively developed)
   - Name: `main-branch-deploy`
   - Add
7. Go to the Function App (`kesser-dashboard-api`) → **Access control
   (IAM)** → **Add role assignment** → Role: **Website Contributor** →
   Members: select the `gh-deploy-kesser-dashboard` managed identity →
   Review + assign. (This is the ONLY permission this identity gets —
   just enough to deploy code to this one Function App, nothing else.)
8. Copy down these three values — you'll give them to me (not as chat
   text with the actual values if you're security-conscious about pasting
   secrets into chat; adding them directly as GitHub repo secrets is safer
   — see Step 8):
   - **Client ID** of `gh-deploy-kesser-dashboard` (Overview page)
   - **Tenant ID** (same Overview page, or any Azure resource's Overview)
   - **Subscription ID** (same Overview page)

---

## Step 8 — Add the secrets to GitHub (not to me, not in chat)

Go to `github.com/morielhamui/Kesser_Financial_Dashboard` → **Settings** →
**Secrets and variables** → **Actions** → **New repository secret**, and
add each of these:

| Secret name | Value |
|---|---|
| `DEPLOY_CLIENT_ID` | the Client ID from Step 7 |
| `DEPLOY_TENANT_ID` | the Tenant ID from Step 7 |
| `DEPLOY_SUBSCRIPTION_ID` | the Subscription ID from Step 7 |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | Static Web App → Overview → "Manage deployment token" → copy |
| `AZURE_CLIENT_ID` | the Entra app's Client ID from Step 6 |
| `AZURE_CLIENT_SEC` | the Entra app's client secret value from Step 6 |

None of these need to be sent to me — once they're in GitHub as secrets, the
deploy workflow I write will reference them by name automatically.

---

## What happens after this

Once Steps 1–8 are done, let me know and I'll:
1. Finish building the Node.js backend (`api/` folder) and the GitHub
   Actions workflow that deploys to these exact resource names.
2. Convert the dashboard pages to pull live data from the new API instead
   of the static Artifact snapshots.
3. Push to `main`, which will trigger the first real deploy — at that
   point you'll have a working `https://kesser-financial-dashboard.azurestaticapps.net`
   URL (or similar) that your named colleagues can sign into with their
   Aperion Microsoft account.

You don't have to do all 8 steps before I start — I can build the code in
parallel. The only hard dependency is: I need the **exact resource names**
you end up using (if any had to change due to a naming conflict) before the
final deploy workflow will work.
