import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv


API_DEFAULT_BASE_URL = "https://edu.kafb2b.or.kr/api/v2/whsl"


class ExpiredTokenError(RuntimeError):
    """Raised when the API reports an expired token."""


def load_config() -> tuple[str, str, str, str]:
    """
    Load configuration for the API.

    Returns a tuple of (resource_base_url, token_endpoint, service_key, secret_key).
    """
    load_dotenv()
    api_base = os.getenv("KAFB2B_API_URL", API_DEFAULT_BASE_URL)
    service_key = os.getenv("SRCV_KEYVAL")
    secret_key = os.getenv("SCR_KEYVAL")

    missing = [name for name, val in {"SRCV_KEYVAL": service_key, "SCR_KEYVAL": secret_key}.items() if not val]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variable(s): {joined}")

    resource_base, token_endpoint = _split_base_and_token_endpoint(api_base)
    return resource_base, token_endpoint, service_key, secret_key


def _split_base_and_token_endpoint(api_base: str) -> tuple[str, str]:
    """Normalize configuration so we always have a base URL and token endpoint."""
    normalized = api_base.rstrip("/")
    last_segment = normalized.rsplit("/", 1)[-1]
    lower_segment = last_segment.lower()
    if lower_segment.endswith((".do", ".json", ".php", ".asp")) or "." in last_segment:
        resource_base = normalized.rsplit("/", 1)[0]
        token_endpoint = normalized
    else:
        resource_base = normalized
        token_endpoint = f"{normalized}/access_token.do"
    return resource_base, token_endpoint


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
    headers = {"Content-Type": "application/json"}
    payload = {"SRCV_KEYVAL": service_key, "SCR_KEYVAL": secret_key}

    resp = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"Token 요청 실패 ({resp.status_code}): {resp.text[:300]}"
        ) from exc

    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"API response is not JSON: {resp.text[:300]}")

    token = _find_token(data)
    if not token:
        raise RuntimeError(f"API response missing TKN_INFO. Body: {data!r}")
    return token


def _post_market_endpoint(url: str, token: str, payload: dict, timeout: int, context: str) -> dict:
    """POST helper that attaches the token and normalizes error handling."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    try:
        data = resp.json()
    except ValueError:
        data = None

    if not resp.ok:
        message = ""
        if isinstance(data, dict):
            message = str(data.get("MESSAGE", "")).strip()
        if message and "만료" in message:
            raise ExpiredTokenError(message or "만료된 토큰입니다.")
        raise RuntimeError(
            f"{context} 요청 실패 ({resp.status_code}): {message or resp.text[:300]}"
        )

    if data is None:
        raise RuntimeError(f"{context} 응답이 JSON이 아닙니다: {resp.text[:300]}")

    return data


def request_sales_price(
    INQ_REQUST_YMD: str,
    PGE_NO: str,
    WHMK_CD: str,
    WHSL_CPR_CD: str,
    timeout: int = 10,
) -> dict:
    """
    판매원장 리스트를 조회한다.

    함수가 호출될 때마다 토큰을 발급받아 요청에 사용한다.
    """
    base_url, token_endpoint, service_key, secret_key = load_config()
    payload = {
        "INQ_REQUST_YMD": INQ_REQUST_YMD,
        "PGE_NO": PGE_NO,
        "WHMK_CD": WHMK_CD,
        "WHSL_CPR_CD": WHSL_CPR_CD,
    }

    def _request() -> dict:
        token = request_access_token(token_endpoint, service_key, secret_key, timeout)
        print(token)
        return _post_market_endpoint(
            f"{base_url}/excclcPrcInfo.do",
            token,
            payload,
            timeout,
            "판매원장",
        )

    try:
        return _request()
    except ExpiredTokenError:
        return _request()


def request_trans_info(
    INQ_REQUST_YMD: str,
    PGE_NO: str,
    WHMK_CD: str,
    WHSL_CPR_CD: str,
    timeout: int = 10,
) -> dict:
    """
    송품/거래 정보 리스트를 조회한다.

    함수가 호출될 때마다 토큰을 발급받아 요청에 사용한다.
    """
    base_url, token_endpoint, service_key, secret_key = load_config()
    payload = {
        "INQ_REQUST_YMD": INQ_REQUST_YMD,
        "PGE_NO": PGE_NO,
        "WHMK_CD": WHMK_CD,
        "WHSL_CPR_CD": WHSL_CPR_CD,
    }

    def _request() -> dict:
        token = request_access_token(token_endpoint, service_key, secret_key, timeout)
        return _post_market_endpoint(
            f"{base_url}/trnsoInfo.do",
            token,
            payload,
            timeout,
            "거래정보",
        )

    try:
        return _request()
    except ExpiredTokenError:
        return _request()


def main() -> None:
    try:
        date = "20251120"
        page = "1"
        whmk = "210001"
        whsl = "21000102"

        sales_response = request_sales_price(date, page, whmk, whsl)
        print("Sales response:")
        print(sales_response)

        trans_response = request_trans_info(date, page, whmk, whsl)
        print("Trans response:")
        print(trans_response)

    except Exception as exc:  # keep CLI friendly
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
