# Football highlights playlist sync

Mirrors match-highlight videos from five broadcaster playlists into one
YouTube playlist of your own. Runs nightly on GitHub Actions, so it keeps
working when the NAS doesn't.

This is a *backup* view. Pinchflat + Plex remains the primary; this exists
so the highlights are reachable from anything that can open YouTube.

## Sources

| League | Channel | Playlist |
|---|---|---|
| LaLiga | ESPN FC | `PLNMKibI54hWU` |
| Bundesliga | ESPN FC | `PLHue7AF8bVI0` |
| Premier League | NBC Sports | `PLR1b-6EyIaTs` |
| Serie A | CBS Sports Golazo | `PLcS6KNbFQ63k` |
| Champions League | CBS Sports Golazo | `PLWvDauQBKnvI` |

Each has a title filter matching the Pinchflat rules, so roundups, transfer
clips and studio segments are excluded — only `Team v. Team` match packages
get through.

## Setup

### 1. Create the target playlist

On YouTube, create an empty playlist (name it whatever you like, Unlisted is
fine). Open it and copy the `list=` value from the URL — that's the ID.

### 2. Google Cloud project

1. <https://console.cloud.google.com> → new project
2. **APIs & Services → Library** → enable **YouTube Data API v3**
3. **OAuth consent screen** → External → fill the required fields → add your
   own Google account under **Test users**
4. **PUBLISH THE APP.** Publishing status → *Publish app*. Accept the
   unverified-app warning.

   > This step is not optional. While the consent screen is in **Testing**,
   > Google expires refresh tokens after **7 days** and the workflow breaks
   > every week. Published apps issue non-expiring refresh tokens.

5. **Credentials → Create Credentials → OAuth client ID → Desktop app** →
   download the JSON, save it beside `get_refresh_token.py` as
   `client_secret.json`

### 3. Get a refresh token (once, on your own machine)

```bash
pip install google-auth-oauthlib
python get_refresh_token.py
```

A browser opens, you approve, and it prints the three values you need.

### 4. GitHub secrets

Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Value |
|---|---|
| `YT_CLIENT_ID` | from step 3 |
| `YT_CLIENT_SECRET` | from step 3 |
| `YT_REFRESH_TOKEN` | from step 3 |
| `YT_TARGET_PLAYLIST` | playlist ID from step 1 |

### 5. Run it

Actions tab → *Sync football highlight playlists* → **Run workflow**.
Then it runs nightly at 08:37 UTC on its own.

## Quota

`playlistItems.insert` costs 50 units against a 10,000/day quota, so about
200 inserts per day is the ceiling. `MAX_INSERTS_PER_RUN` is set to 150.

Your first run has ~200 eligible videos to backfill, so it will insert 150,
log how many it deferred, and finish the rest the next night. After that
it's a handful of matches a week — nowhere near the limit.

## Changing things

- **Add a league** — add an entry to `SOURCES` in `sync_playlists.py`
- **Change how far back it reaches** — `CUTOFF_DATE` in the workflow
- **Loosen a filter** — set that source's regex to `None` to take everything

## If it stops working

Almost always the refresh token. Check the Actions log for
`invalid_grant`, and if you see it, confirm the consent screen is still
**Published** (step 2.4), then re-run `get_refresh_token.py` and update the
secret.
