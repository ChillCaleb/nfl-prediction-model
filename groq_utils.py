import os
from pathlib import Path

import requests
from dotenv import dotenv_values


ROOT_DIR = Path(__file__).resolve().parent
ROOT_ENV = ROOT_DIR / ".env"
FINDERS_ENV = ROOT_DIR / "Finders" / ".env"

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
KEY_VARIABLES = (
    "GROQ_API_KEY",
    "GROQ_API_KEY_FALLBACK",
    "GROQ_FALLBACK_API_KEY",
    "GROQ_API_KEYS",
)


def _load_env_file(path):
    if not path.exists():
        return {}
    return dotenv_values(path)


def _split_keys(value):
    if not value:
        return []

    keys = []
    for chunk in str(value).replace("\n", ",").split(","):
        key = chunk.strip()
        if key:
            keys.append(key)
    return keys


def get_groq_model():
    root_env = _load_env_file(ROOT_ENV)
    finders_env = _load_env_file(FINDERS_ENV)

    return (
        root_env.get("GROQ_MODEL")
        or os.getenv("GROQ_MODEL")
        or finders_env.get("GROQ_MODEL")
        or DEFAULT_GROQ_MODEL
    )


def get_groq_api_keys():
    root_env = _load_env_file(ROOT_ENV)
    finders_env = _load_env_file(FINDERS_ENV)
    sources = (
        (".env", root_env),
        ("environment", os.environ),
        ("Finders/.env", finders_env),
    )

    api_keys = []
    seen = set()
    for variable in KEY_VARIABLES:
        for source_name, source in sources:
            for key in _split_keys(source.get(variable)):
                if key in seen:
                    continue
                seen.add(key)
                api_keys.append((f"{source_name}:{variable}", key))

    return api_keys


def post_groq_chat_completion(payload, timeout=15):
    api_keys = get_groq_api_keys()
    if not api_keys:
        raise RuntimeError(
            "No Groq API key found. Set GROQ_API_KEY in .env or add "
            "GROQ_API_KEY_FALLBACK / GROQ_API_KEYS."
        )

    errors = []
    for source_name, api_key in api_keys:
        try:
            response = requests.post(
                GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response, source_name
        except requests.RequestException as exc:
            errors.append((source_name, exc))

    tried_sources = ", ".join(source_name for source_name, _ in errors)
    raise RuntimeError(
        f"Groq request failed after trying {len(errors)} API key source(s): "
        f"{tried_sources}. Last error: {errors[-1][1]}"
    )
