# Google Calendar web OAuth setup

Mini Muse connects to Google Calendar through the standard Google Calendar API. The hosted app uses a **Web application** OAuth client; users never upload `google_credentials.json` or paste access tokens.

## One-time Google Cloud setup

1. In Google Cloud Console, select the project for this app and enable **Google Calendar API**.
2. In **Google Auth Platform**, complete Branding, Audience, and Data Access. For a personal account, choose External and add the intended accounts as test users while the app is in testing.
3. In **Clients**, create a client of type **Web application**.
4. Add this authorized redirect URI:

   `https://my-llm-playground-bvapyfhmkp7xn5ji9raank.streamlit.app/`

5. Copy the client ID and client secret. Do not commit them or add them to source files.

## Streamlit deployment secrets

In Streamlit Community Cloud, open **Settings → Secrets** and add:

```toml
GOOGLE_OAUTH_CLIENT_ID = "..."
GOOGLE_OAUTH_CLIENT_SECRET = "..."
GOOGLE_OAUTH_REDIRECT_URI = "https://my-llm-playground-bvapyfhmkp7xn5ji9raank.streamlit.app/"
```

## User flow in Mini Muse

1. Enable Google Calendar in **Connectors**.
2. Click **Connect Google Calendar**.
3. The app sends the user to Google’s consent page.
4. Google redirects back to the hosted app with an authorization code.
5. The app exchanges the code for a token and stores it only for that active session.
6. Calendar tools become available; creating an event still requires approval.

## Security rules

- Never place OAuth credentials or user tokens in Git, prompts, logs, or results.
- Request only the Calendar scopes required to read events and create events.
- Treat tokens as session-only. A user reconnects after a session expires or is cleared.
- Keep `create_event` approval-gated.
