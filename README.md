# Pokedex Assistant

This project can run as:

- CLI: terminal assistant
- Web app: public browser app via Streamlit Community Cloud

## Run Locally (CLI)

```bash
python main.py
```

## Run Locally (Web)

```bash
streamlit run streamlit_app.py
```

## Put It On GitHub

From the project root:

```bash
git add .
git commit -m "Add public web app entrypoint"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

If `origin` already exists:

```bash
git push -u origin main
```

## Make It Publicly Usable Without Sign-In

GitHub itself cannot host this Python app directly for anonymous users.
Use Streamlit Community Cloud to deploy from your GitHub repo.

1. Go to https://share.streamlit.io/
2. Sign in once as the maintainer.
3. Select your GitHub repo and branch.
4. Set the main file to `streamlit_app.py`.
5. Deploy.

After deploy, anyone can open the public URL and use the app without signing in or downloading anything.

## Notes

- Keep `pokedex.db` in the repo so deployed app can answer queries.
- If you later move to a larger host, this same web entrypoint can be reused.
