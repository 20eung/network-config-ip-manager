# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.5.1-server] - 2026-03-12

### Fixed
- **Docker 볼륨 마운트 누락 수정**: `/data/configs` 디렉토리가 컨테이너에 마운트되지 않아 config 파일이 표시되지 않던 문제 해결
  - `docker-compose.yml`에 `volumes: - /data/configs:/data/configs:ro` 추가
  - `CONFIG_DIR` 환경변수를 `/data/configs`로 통일
  - NetDevOps Portal 연동 시 config 파일이 정상적으로 표시됨

### Changed
- **네트워크 설정 단순화**: `npm-network` 제거, `portainer-network`만 사용하도록 변경
- **README 업데이트**: 볼륨 마운트 경로 명확화 및 환경변수 설명 추가

### Documentation
- docker-compose.yml 예시 코드 업데이트
- Environment Variables 섹션에 경로 일치 요구사항 추가
- Architecture 다이어그램 경로 수정

---

## [v1.5.0-server] - 2026-01-XX

### Added
- NetDevOps Portal 통합 (server 브랜치)
- Authentik Forward Auth 지원
- 서버 디렉토리 자동 로드 기능
- portainer-network 연동

### Changed
- standalone 버전을 main 브랜치로 분리
- server 버전을 별도 브랜치로 관리

---

## [v1.3.0] - 2025-XX-XX

### Added
- Arista EOS config 파싱 지원
- 컬럼 너비 마우스 드래그 조절 기능

---

## [v1.0.0] - Initial Release

### Added
- Nokia SR OS config 파싱 (System IP, Interface IP, Static Route)
- 웹 대시보드 (Bootstrap 5)
- Excel/CSV 내보내기
- Docker 지원
