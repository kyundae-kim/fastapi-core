# fastapi-core 문서-소스 정합성 체크리스트

> 목적: 개발 문서가 현재 구현을 정확히 설명하도록, 변경 시 확인할 코드 기준점과 문서 책임을 정리한다.
> 소스코드가 최종 기준이며, 구현과 문서가 다르면 문서를 먼저 수정한다.

## 1. 기준 코드

| 변경 영역 | 기준 코드 | 함께 확인할 문서 |
| --- | --- | --- |
| 앱 조립, lifespan, `app.state`, CORS | `fastapi_core/factory.py` | `README.md`, `docs/api.md`, `docs/config.md`, `docs/examples.md` |
| managed resource와 typed readiness registry | `fastapi_core/extensions.py` | `README.md`, `docs/api.md`, `docs/examples.md`, `docs/srs.md`, `docs/test.md` |
| 앱별 OAuth2, authorization, correlation/error contract | `fastapi_core/dependencies/auth.py`, `fastapi_core/http.py`, `fastapi_core/factory.py` | `README.md`, `docs/api.md`, `docs/config.md`, `docs/examples.md`, `docs/srs.md`, `docs/test.md` |
| 앱 설정과 환경변수 | `fastapi_core/config.py` | `README.md`, `docs/config.md`, `docs/api.md`, `.env.example` |
| DocMesh 설정 fallback 및 서비스 선택 | `fastapi_core/docmesh_settings.py` | `docs/config.md`, `docs/api.md`, `docs/examples.md`, `.env.example` |
| 인증 dependency와 권한 검사 | `fastapi_core/dependencies/auth.py` | `README.md`, `docs/api.md`, `docs/examples.md`, `docs/srs.md` |
| 서비스 client dependency | `fastapi_core/dependencies/services.py`, `fastapi_core/dependencies/__init__.py` | `docs/api.md`, `docs/config.md`, `docs/messaging.md`, `docs/srs.md` |
| auth/health HTTP 계약 | `fastapi_core/routers/auth.py`, `fastapi_core/routers/health.py`, `fastapi_core/schemas/` | `README.md`, `docs/api.md`, `docs/examples.md`, `docs/srs.md` |
| 실제 검증 범위 | `test_fastapi_core/` | `docs/test.md` |

## 2. 문서별 책임 경계

- `docs/prd.md`: 사용자 가치, 제품 범위, 수용 결과만 관리한다. 함수명·경로·스키마명은 넣지 않는다.
- `docs/srs.md`: 목표 계약을 관리한다. 구체 함수명, endpoint, 상태 코드, lifecycle 제약을 둔다.
- `docs/api.md`: 현재 구현된 공개 API와 실제 상태 코드를 기준으로 한다.
- `docs/config.md`: 실제 `AppConfig`, 환경변수 alias, 서비스 설정 로더와 fallback만 설명한다.
- `docs/examples.md`: 현재 테스트 또는 구현 경로로 뒷받침되는 복사 가능한 예제만 둔다.
- `docs/messaging.md`: NATS를 포함한 메시징의 현재 `service_clients`/readiness/lifespan 통합 범위와 서비스별 확장 지점을 구분한다.
- `docs/test.md`: 존재하는 테스트 파일, marker, 실행 결과, 미검증 항목만 기록한다.

## 3. 변경 후 점검

- [ ] `create_app()`의 인자, `app.state` 키, lifespan 종료 동작이 README/API/config/examples와 일치한다.
- [ ] managed resource의 startup/rollback/shutdown 순서와 `get_resource()` 공개 계약이 API/SRS/examples/test와 일치한다.
- [ ] typed readiness의 required/timeout/redaction 정책과 제거된 legacy state 경계가 API/config/test와 일치한다.
- [ ] 앱별 OAuth2 scheme, role/scope/permission 정책, problem-details 및 correlation ID 계약이 API/SRS/examples/test와 일치한다.
- [ ] route, response schema, auth/readiness 상태 코드가 API/examples/SRS와 일치한다.
- [ ] 환경변수 이름, alias, 기본값, CSV 파싱 규칙이 config 문서와 `.env.example`에 일치한다.
- [ ] 패키지 루트 export와 dependency package export를 구분해 문서화한다.
- [ ] 구현되지 않은 helper 또는 route를 기본 제공 API처럼 설명하지 않는다.
- [ ] 테스트 파일 인벤토리와 pytest 결과는 실제 수집/실행 결과로만 갱신한다.
- [ ] 변경한 공개 표면은 `uv run pytest -q`로 검증한다.
