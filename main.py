import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv


API_DEFAULT_URL = "https://edu.kafb2b.or.kr/api/v2/whsl"


def load_config() -> tuple[str, str, str]:
    """Load API URL and credentials from environment (.env is loaded if present)."""
    load_dotenv()
    api_url = os.getenv("KAFB2B_API_URL", API_DEFAULT_URL)
    service_key = os.getenv("SRCV_KEYVAL")
    secret_key = os.getenv("SCR_KEYVAL")

    missing = [name for name, val in {"SRCV_KEYVAL": service_key, "SCR_KEYVAL": secret_key}.items() if not val]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variable(s): {joined}")

    return api_url, service_key, secret_key


def _find_token(obj) -> Optional[str]:
    """Recursively search a JSON-like structure for key 'TKN_INFO' (case-insensitive)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() == "tkn_info" and isinstance(v, str) and v.strip():
                return v
            found = _find_token(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_token(item)
            if found:
                return found
    return None


def request_access_token(api_url: str, service_key: str, secret_key: str, timeout: int = 10) -> str:
    """
    Request an access token from the KAFB2B API.

    Expected response JSON should contain `TKN_INFO` with the token string.
    """
    payload = {"SRCV_KEYVAL": service_key, "SCR_KEYVAL": secret_key}
    headers = {"Content-Type": "application/json"}

    resp = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()

    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"API response is not JSON: {resp.text[:300]}")

    token = _find_token(data)
    if not token:
        raise RuntimeError(f"API response missing TKN_INFO. Body: {data!r}")
    return token


ACCESS_TOKEN: Optional[str] = None


def main() -> None:
    try:
        api_url, service_key, secret_key = load_config()

        # If the provided URL is a base path, append the expected token endpoint.
        if api_url.lower().endswith((".do", ".json", ".php", ".asp")) or "." in api_url.rsplit("/", 1)[-1]:
            endpoint = api_url
        else:
            endpoint = api_url.rstrip("/") + "/access_token.do"

        token = request_access_token(endpoint, service_key, secret_key)
        global ACCESS_TOKEN
        ACCESS_TOKEN = token
    except Exception as exc:  # keep CLI friendly
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Access token: {ACCESS_TOKEN}")
    print("hello")


if __name__ == "__main__":
    main()
