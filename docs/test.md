# 테스트 가이드

## 개요

테스트는 **단위 테스트(mock 기반)**와 **통합 테스트(실제 Keycloak 연결)**로 분리됩니다.

- **단위 테스트**: 외부 서비스(Keycloak, DB) 없이 `unittest.mock`으로 의존성을 교체하여 빠른 피드백 제공
- **통합 테스트**: 실제 Keycloak 인스턴스에 연결하여 실환경 문제 조기 탐지

pytest 설정은 `pyproject.toml`의 `[tool.pytest.ini_options]`에 정의되어 있으며, 테스트 루트는 `test_fastapi_template/`입니다.
