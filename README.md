# KAFB2B API Client

KAFB2B 도매시장 API를 호출하기 위한 간단한 Python 클라이언트입니다. 환경 변수에서 인증 정보와 도매시장 설정을 읽고, 실행 인자로 받은 조회 조건으로 API를 호출합니다.

## 기능

- `.env` 또는 시스템 환경 변수에서 API 설정 로드
- access token 발급
- 응답 JSON 내부의 `TKN_INFO` 자동 탐색
- token 만료 응답 감지 시 1회 재발급 후 재시도
- 정산 가격 정보 조회: `excclcPrcInfo.do`
- 거래 정보 조회: `trnsoInfo.do`

## 요구 사항

- Python 3.12 이상
- uv

## 설치

```powershell
uv sync
```

## 환경 변수

프로젝트 루트에 `.env` 파일을 만들고 필수 값을 설정합니다.

```dotenv
KAFB2B_API_URL=https://kafb2b.or.kr/api/v2/whsl
SRCV_KEYVAL=서비스키
SCR_KEYVAL=시크릿키

KAFB2B_WHMK_CD=도매시장코드
KAFB2B_WHSL_CPR_CD=도매시장법인코드
```

필수 값:

- `KAFB2B_API_URL`: API 기본 URL 또는 token 발급 endpoint
- `SRCV_KEYVAL`: 서비스 키
- `SCR_KEYVAL`: 시크릿 키
- `KAFB2B_WHMK_CD`: 도매시장 코드
- `KAFB2B_WHSL_CPR_CD`: 도매시장 법인 코드

`KAFB2B_API_URL`에는 리소스 기본 URL 또는 token 발급 endpoint를 넣을 수 있습니다.

- 기본 URL 예: `https://kafb2b.or.kr/api/v2/whsl`
- token endpoint 예: `https://kafb2b.or.kr/api/v2/whsl/access_token.do`

## 실행

```powershell
uv run python main.py 20251120 --page 1
```

`main.py`는 조회일자를 필수 인자로 받고, 페이지 번호는 `--page` 옵션으로 받습니다. `--page`를 생략하면 `1`을 사용합니다.

```powershell
uv run python main.py 20251120
```

도매시장 코드와 도매시장 법인 코드는 환경 변수에서 읽어 정산 가격 정보와 거래 정보를 순서대로 조회합니다.

## 주요 함수

### `request_access_token(api_url, service_key, secret_key, timeout=10)`

KAFB2B API에 인증 정보를 전송해 access token을 발급받습니다. 응답 JSON 어디에 있든 `TKN_INFO` 키를 재귀적으로 찾아 token 문자열을 반환합니다.

### `request_sales_price(INQ_REQUST_YMD, PGE_NO, WHMK_CD, WHSL_CPR_CD, timeout=10)`

정산 가격 정보 endpoint인 `excclcPrcInfo.do`를 호출합니다.

### `request_trans_info(INQ_REQUST_YMD, PGE_NO, WHMK_CD, WHSL_CPR_CD, timeout=10)`

거래 정보 endpoint인 `trnsoInfo.do`를 호출합니다.

## 조회 파라미터

| 이름 | 설명 | 예시 |
| --- | --- | --- |
| `INQ_REQUST_YMD` | 조회 요청 일자, `YYYYMMDD` 형식 | `20251120` |
| `PGE_NO` | 페이지 번호 | `1` |
| `WHMK_CD` | 도매시장 코드 | `.env`의 `KAFB2B_WHMK_CD` |
| `WHSL_CPR_CD` | 도매시장 법인 코드 | `.env`의 `KAFB2B_WHSL_CPR_CD` |

## 오류 처리

- 필수 환경 변수가 없으면 `RuntimeError`가 발생합니다.
- token 발급 응답이 JSON이 아니거나 `TKN_INFO`가 없으면 `RuntimeError`가 발생합니다.
- 조회 API에서 token 만료 메시지가 감지되면 token을 다시 발급받아 1회 재시도합니다.
- CLI 실행 중 예외가 발생하면 `[ERROR] ...` 형식으로 stderr에 출력하고 종료 코드 `1`로 종료합니다.
