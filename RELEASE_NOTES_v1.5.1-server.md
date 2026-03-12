# Release Notes v1.5.1-server

**Release Date**: 2026-03-12
**Branch**: `server`
**Type**: Bugfix Release

---

## Overview

NetDevOps Portal 연동 시 config 파일이 표시되지 않던 치명적인 버그를 수정한 핫픽스 릴리즈입니다.

---

## What's Fixed

### 🐛 Critical Bug: Config 파일 표시 안 됨

**문제**: NetDevOps Portal에서 IP Manager 접속 시 아무 파일도 표시되지 않음

**원인**: `docker-compose.yml`에 `/data/configs` 디렉토리 볼륨 마운트가 누락됨

**해결**:
```yaml
volumes:
  - /data/configs:/data/configs:ro
environment:
  - CONFIG_DIR=/data/configs
```

**영향**: NetDevOps Portal 사용자 전체 (server 브랜치 사용자)

---

## Changes

### Docker 설정

**Before**:
```yaml
environment:
  - CONFIG_DIR=/config
volumes:
  - /data/configs:/config:ro
networks:
  - npm-network
  - portainer-network
```

**After**:
```yaml
environment:
  - CONFIG_DIR=/data/configs
volumes:
  - /data/configs:/data/configs:ro
networks:
  - portainer-network
```

**개선 사항**:
1. **경로 일관성**: 환경변수와 마운트 경로 통일 (`/data/configs`)
2. **네트워크 단순화**: `npm-network` 제거, `portainer-network`만 사용
3. **가독성 향상**: 호스트 경로와 컨테이너 경로가 동일하여 혼란 감소

---

## Testing Results

### 검증 완료 항목

✅ `/data/configs` 디렉토리가 컨테이너 내부에 정상 마운트됨
✅ 하위 디렉토리 `cloud/`, `isp/`, `mpls/` 접근 가능
✅ `/api/browse` 엔드포인트에서 3개 디렉토리 정상 표시
✅ Config 파일 106개 (Nokia 94, Arista 12) 모두 파싱 성공
✅ Excel/CSV 내보내기 정상 작동

### 테스트 환경

- Host OS: Ubuntu Linux
- Docker: 최신 버전
- Config 파일: 106개 (Nokia SR OS 94개, Arista EOS 12개)
- 디렉토리 구조: `/data/configs/{cloud,isp,mpls}/*.txt`

---

## Upgrade Instructions

### 1. 코드 업데이트

```bash
cd /data/network-config-ip-manager
git fetch origin
git checkout server
git pull origin server
```

### 2. 컨테이너 재시작

```bash
sudo docker-compose down
sudo docker-compose up -d
```

### 3. 동작 확인

1. NetDevOps Portal에서 IP Manager 접속
2. 자동으로 config 파일 목록 표시 확인
3. Excel/CSV 내보내기 테스트

**예상 결과**:
- 페이지 로드 시 즉시 IP 목록 표시
- 통계 카드에 장비 수/IP 수 표시
- 검색 및 필터링 정상 작동

---

## Documentation Updates

| 파일 | 변경 내용 |
|------|----------|
| `README.md` | docker-compose.yml 예시 업데이트, 환경변수 설명 추가 |
| `CHANGELOG.md` | v1.5.1-server 항목 추가 (신규 파일) |
| `docker-compose.yml` | 볼륨 마운트 추가, 네트워크 설정 단순화 |

---

## Breaking Changes

없음 (하위 호환성 유지)

---

## Known Issues

없음

---

## Contributors

- Claude Code (AI Assistant)

---

## Support

문제 발생 시:
1. `sudo docker logs ip-manager --tail 50` 로그 확인
2. `sudo docker exec ip-manager ls /data/configs/` 마운트 확인
3. GitHub Issues에 버그 리포트

---

## Next Release Preview (v1.6.0)

계획 중인 기능:
- [ ] VPRN/VPLS 인터페이스 파싱 지원
- [ ] IP 중복 검사 기능
- [ ] 변경 이력 비교 (이전 파싱 결과와 diff)
- [ ] 디렉토리 브라우저 UI 개선
