# FoundryDock Update Gateway

Small authenticated proxy used by packaged FoundryDock installs when the main GitHub repository is private.

## Required environment variables

- `GITHUB_TOKEN`: server-side GitHub token with read-only access to releases in `Jarakeen/BFF`.
- `FOUNDRYDOCK_UPDATE_ACCESS_KEY`: app-specific download key. This is not a GitHub credential.
- `GITHUB_REPOSITORY`: optional, defaults to `Jarakeen/BFF`.

## Start command

`uvicorn app:app --host 0.0.0.0 --port $PORT`

The client sends the app-specific key in `X-FoundryDock-Update-Key`. The GitHub token never leaves the gateway.
