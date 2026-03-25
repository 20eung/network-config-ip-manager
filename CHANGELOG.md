# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.6.0-server] - 2026-03-25

### Added
- **구분(망구분) 필드 추가**: `/data/configs` 하위 서브폴더명을 대문자로 표시 (CLOUD, ISP, MPLS)
  - 테이블 컬럼, Excel/CSV 내보내기, 컬럼 설정 모달에 반영
  - CLOUD(파랑), ISP(보라), MPLS(노랑) 색상 배지 표시
- **망구분 필터**: 유형(System IP / Interface IP / Static Route)과 독립적으로 선택 가능한 망구분 필터 추가
- **카드 망구분 카운터**: 총장비수·총IP수·System IP·Interface IP·Static Route 카드에 망구분별 세부 카운터 표시
- **Gitea 커밋 날짜 표시**: `git logs/HEAD` 파일 직접 파싱으로 최신 커밋 시각을 디렉토리 바에 표시 (git 바이너리 불필요)
  - `docker-compose.yml`에 `/data/gitea-server/git-repo/.git` 읽기 전용 마운트 추가

### Changed
- **IP 정렬 개선**: 네트워크·CIDR 컬럼 클릭 시 텍스트 순이 아닌 IP 주소 숫자 기준으로 정렬
- **필터 레이아웃 개선**: 망구분/유형 필터를 한 줄에 표시, 아이콘 + 라벨 칩 디자인 적용
- **Config 시간 표시**: 최근 Config 카드에 날짜와 시간(HH:MM:SS) 분리 표시, UTC → KST 자동 변환
- **텍스트 변경**: '최신 Config' → '최근 Config', 'Gitea' → 'Gitea 커밋'

---

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
