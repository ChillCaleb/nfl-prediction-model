# Deploy NFL POA to Cloud Run

This app is packaged for Cloud Run with `Dockerfile`. The container runs Streamlit on `0.0.0.0` and uses Cloud Run's `PORT` environment variable, defaulting to `8080` for local runs.

## Local smoke test

```bash
docker build -t nfl-poa-streamlit .
docker run --rm -p 8080:8080 -e PORT=8080 --env-file .env nfl-poa-streamlit
```

Open `http://localhost:8080`.

If you do not pass `.env`, the app still runs, but Groq AI summaries are unavailable until `GROQ_API_KEY` is configured.

## Deploy from Google Cloud Console

1. Push the repo to GitHub with `Dockerfile`, `.dockerignore`, `requirements.txt`, `streamlit_app.py`, `frontend_services.py`, `Database/`, `Model/`, and `Legacy_Files/`.
2. Do not commit `.env`. It is ignored by Docker and should stay private.
3. In Google Cloud Console, go to Cloud Run > Services > Connect repository.
4. Select the GitHub repository and branch.
5. Choose Dockerfile as the build source.
6. Set the service name to `nfl-poa`.
7. Set the container port to `8080`.
8. In Variables & Secrets, reference a Secret Manager secret named `groq-api-key` as environment variable `GROQ_API_KEY`.
9. Choose whether the app should allow unauthenticated access, then deploy.

## Deploy with gcloud

Run this from a machine with `gcloud` installed and authenticated, or from Google Cloud Shell.

```bash
PROJECT_ID=nfl-poa
REGION=us-central1
SERVICE=nfl-poa

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
```

Create the Groq secret once:

```bash
set -a
source .env
set +a

printf '%s' "$GROQ_API_KEY" | gcloud secrets create groq-api-key \
  --replication-policy=automatic \
  --data-file=-
```

If the secret already exists, add a new version instead:

```bash
set -a
source .env
set +a

printf '%s' "$GROQ_API_KEY" | gcloud secrets versions add groq-api-key \
  --data-file=-
```

Deploy from source:

```bash
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-secrets GROQ_API_KEY=groq-api-key:latest
```

## References

- Cloud Run container contract: https://docs.cloud.google.com/run/docs/container-contract
- Deploy Cloud Run services from source: https://docs.cloud.google.com/run/docs/deploying-source-code
- Configure Cloud Run secrets: https://docs.cloud.google.com/run/docs/configuring/services/secrets
- Continuous deployment from a repository: https://docs.cloud.google.com/run/docs/continuous-deployment
