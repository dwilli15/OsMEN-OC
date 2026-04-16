# Google OAuth Pipeline A

Operator-facing reference for the Google OAuth credential flow.

Use this file instead of reconstructing the flow from chat history.

## Tagged References

`[A-PROJECT]`
Google Cloud project display name: `OsMEN`
Google Cloud project ID: `project-a788f6fd-238c-4c49-aab`
Use the project ID in `gcloud`, not the display name.

`[A-APIS]`
Enabled Google APIs verified in Cloud Shell on 2026-04-14:
- `calendar-json.googleapis.com`
- `gmail.googleapis.com`
- `tasks.googleapis.com`
- `people.googleapis.com`
- `forms.googleapis.com`
- `drive.googleapis.com`
- `docs.googleapis.com`
- `sheets.googleapis.com`
- `slides.googleapis.com`
- `chat.googleapis.com`
- `classroom.googleapis.com`
- `script.googleapis.com`
- `youtube.googleapis.com`

`[A-NOT-API-KEY]`
This flow uses an OAuth client, not an API key.
Do not create or store a Google API key for Gmail, Calendar, Drive, Docs, Sheets, or Tasks account access.

`[A-CONSENT]`
Console step: create OAuth consent screen first.
Expected mode: `External`
Expected test user: `d.osmen.oc@gmail.com`

`[A-CONSOLE-LINKS]`
Google Auth Platform links for this project:
- Branding: `https://console.developers.google.com/auth/branding?project=project-a788f6fd-238c-4c49-aab`
- Audience: `https://console.developers.google.com/auth/audience?project=project-a788f6fd-238c-4c49-aab`
- Data Access: `https://console.developers.google.com/auth/scopes?project=project-a788f6fd-238c-4c49-aab`
- OAuth Clients: `https://console.developers.google.com/auth/clients?project=project-a788f6fd-238c-4c49-aab`

Minimum Google-side setup before first successful `gog` callback:
1. Branding configured
2. Audience set to `External`
3. test user `d.osmen.oc@gmail.com` added
4. Data Access includes at least `https://www.googleapis.com/auth/calendar.readonly`
5. Desktop OAuth client exists and its downloaded JSON is the one being used locally

`[A-CLIENT-DOWNLOAD]`
Console step: create `OAuth client ID` with application type `Desktop app`.
Download the resulting `credentials.json` as a temporary local artifact.
Current temporary plaintext location in this install session:
- `/home/dwill/Downloads/credentials.json`
Recommended final convention if re-downloaded later:
- `~/Downloads/osmen-google-credentials.json`

`[A-RUNTIME-KEYRING]`
Primary runtime token store: `gog` keyring-managed auth state.
Verified local metadata path:
- `~/.config/gogcli/keyring/`
Verified current state before OAuth import:
- `~/.config/gogcli/` exists
- `~/.config/gogcli/keyring/` exists
- `~/.config/gogcli/config.json` does not exist yet

`[A-LOCAL-BACKUP]`
Secondary local backup store for token material:
- `~/.config/osmen/secrets/oauth-tokens.enc.yaml`
This file is local-only and must remain SOPS-encrypted.

`[A-REPO-TEMPLATE]`
Committed public-safe template:
- `config/secrets/oauth-tokens.template.yaml`
Repo files must contain placeholders only, never live OAuth values.

`[A-REGISTRY]`
Secret registry entry:
- `config/secrets-registry.yaml` → `google_oauth_tokens`
This is the source-of-truth metadata entry for where Google OAuth material is stored.

`[A-RUNTIME-CONFIG]`
Current runtime config reference:
- `config/agents.yaml` → `taskwarrior_sync.google_calendar_credentials`
- env var: `GOOGLE_CALENDAR_CREDENTIALS_PATH`
This path is for the Google OAuth client credentials JSON consumed by the runtime, not the `gog` refresh-token keyring.

`[A-IMPORT]`
After `credentials.json` is downloaded, run:

```bash
gog auth credentials set /home/dwill/Downloads/credentials.json
gog auth add d.osmen.oc@gmail.com --services calendar --readonly --listen-addr 127.0.0.1:37777 --redirect-uri http://localhost:37777/oauth2/callback --timeout 15m
```

`[A-SCOPE-TRIAGE]`
Do not start with the full `gog` Google service bundle.
Observed failure mode during this install: broad bundles can request scopes that are not suitable for a consumer/test setup.

Known example:
- the `gog` `gmail` bundle includes `https://www.googleapis.com/auth/gmail.settings.sharing`
- Google documents that scope as administrative/service-account oriented
- this can break consumer OAuth testing even when the consent screen exists

Practical rule:
1. prove the client works with minimal Calendar read-only auth first
2. add additional services incrementally only after the first callback succeeds

`[A-LOCALHOST-CALLBACK]`
Observed compatibility issue:
- downloaded desktop client advertised `redirect_uris: ["http://localhost"]`
- forcing a manual localhost callback avoids ambiguity from auto-generated `127.0.0.1` loopback URLs

Current manual flow behavior:
1. open the printed Google authorization URL
2. approve access
3. Google redirects to `http://localhost:37777/oauth2/callback?...`
4. copy that full URL from the browser address bar
5. paste it back into the waiting `gog auth add` terminal prompt

If Google still shows a generic `something went wrong` page even with the localhost callback:
1. re-open the Data Access page
2. confirm the Calendar read-only scope is present
3. confirm the app is still in Testing mode with the test user listed
4. retry the minimal Calendar flow before adding any broader scopes

`[A-CAPTURE]`
After `gog auth add` succeeds:
1. Record the resulting OAuth token snapshot into the local encrypted file at `~/.config/osmen/secrets/oauth-tokens.enc.yaml`
2. Update the repo template only if expected keys changed
3. Keep live values out of the repo

`[A-CLEANUP]`
After import and encrypted backup are complete:
1. Remove the plaintext download `~/Downloads/osmen-google-credentials.json`
2. Keep runtime auth in `gog` keyring
3. Keep backup auth in local SOPS only

`[A-SEARCH-TAGS]`
Search these tags when resuming work:
- `[A-PROJECT]`
- `[A-CONSENT]`
- `[A-CONSOLE-LINKS]`
- `[A-CLIENT-DOWNLOAD]`
- `[A-SCOPE-TRIAGE]`
- `[A-LOCALHOST-CALLBACK]`
- `[A-RUNTIME-KEYRING]`
- `[A-LOCAL-BACKUP]`
- `[A-RUNTIME-CONFIG]`
- `[A-IMPORT]`
- `[A-CLEANUP]`