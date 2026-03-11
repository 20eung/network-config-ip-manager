# Nokia & Arista Config IP Manager

> Nokia SR OS 및 Arista EOS 장비의 config 파일을 파싱하여 IP 관리대장을 자동으로 생성하는 웹 대시보드

[![Version](https://img.shields.io/badge/Version-v1.4.0--server-blue)](https://github.com/20eung/network-config-ip-manager/tree/server)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![openpyxl](https://img.shields.io/badge/Export-Excel%20%7C%20CSV-217346?logo=microsoftexcel&logoColor=white)]()
[![License](https://img.shields.io/badge/License-Internal%20Use-lightgrey)]()

> **브랜치 안내**
> - `main`: **standalone 버전** — 로컬 PC 폴더를 브라우저에서 직접 업로드하여 사용
> - `server` (현재): **서버 연동 버전** — NetDevOps Portal과 통합, 서버 디렉토리 자동 로드 + Authentik 인증

---

## Overview

**server 브랜치**는 NetDevOps Portal 인프라에 통합하여 운영하는 버전입니다.

- 페이지 접속 시 서버에 마운트된 `/config` 디렉토리의 config 파일을 **자동으로 파싱**합니다
- **Authentik Forward Auth**를 통해 포털 로그인 사용자만 접근 가능합니다
- Nokia SR OS와 Arista EOS 장비의 전체 IP 현황을 자동 집계하고 Excel/CSV로 내보낼 수 있습니다

로컬 파일 업로드 기능도 그대로 지원하므로, 서버에 없는 파일은 브라우저에서 직접 업로드할 수 있습니다.

---

## Architecture

```
[Authentik SSO]
      │ Forward Auth
      ▼
[NetDevOps Portal nginx]  ──/services/ip-manager/──▶  [ip-manager container :5001]
                                                              │
                                              /data/configs ──┤ (bind mount :ro)
                                                              │
                                                        /config 디렉토리 자동 파싱
```

**네트워크 구성:**

```
portainer-network (Docker bridge)
├── portal-frontend     :3100 (nginx + React SPA)
├── portal-backend      :8100 (FastAPI 헬스체크)
└── ip-manager          :5001 (이 컨테이너)
```

---

## Features

- 🔄 **서버 자동 로드** — 컨테이너 시작 시 `/config` 디렉토리를 자동으로 파싱하여 즉시 표시
- 📁 **로컬 폴더 업로드** — 서버에 없는 파일은 브라우저에서 직접 업로드 가능
- 🔒 **Authentik 인증** — NetDevOps Portal을 통해 SSO 인증된 사용자만 접근
- 🔍 **실시간 검색 & 필터** — IP 유형별 탭 + 키워드 검색
- 📊 **통계 대시보드** — 장비 수, IP 수, 유형별 집계, 최신 Config 날짜
- ⚙️ **컬럼 커스터마이즈** — 표시 여부 토글 + 드래그로 순서 변경 + 마우스로 너비 조절 (localStorage 영구 저장)
- 📤 **내보내기** — Excel (4개 시트: 전체/Interface IP/Static Route/장비 목록) & CSV
- 🔒 **폐쇄망 환경 완전 지원** — CDN 의존성 없이 정적 파일 내장
- 🗂️ **중복 파일 자동 처리** — 동일 장비의 날짜별 config 중 최신 파일만 파싱
- 🔄 **멀티벤더 지원** — Nokia TiMOS / Arista EOS 파일 자동 감지 및 혼합 디렉토리 파싱
- 📂 **서브디렉토리 재귀 파싱** — 하위 폴더의 `.txt` 파일까지 모두 자동 파싱

---

## Prerequisites

- Docker Engine + docker-compose
- NetDevOps Portal 운영 중 (`portainer-network` Docker 네트워크 존재)
- `/data/configs` 디렉토리 (네트워크 장비 config 백업 경로)
- Authentik 서버 (`auth.hub.sk-net.com` 또는 내부 주소)

---

## Getting Started

### 1. 클론 및 브랜치 전환

```bash
git clone -b server https://github.com/20eung/network-config-ip-manager.git
cd network-config-ip-manager
```

### 2. docker-compose.yml 확인

```yaml
services:
  ip-manager:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ip-manager
    hostname: ip-manager
    restart: unless-stopped
    ports:
      - "5001:5001"
    command: python app.py
    environment:
      - TZ=Asia/Seoul
      - CONFIG_DIR=/config
    volumes:
      - /data/configs:/config:ro
    networks:
      - portainer-network
      - npm-network

networks:
  portainer-network:
    external: true
  npm-network:
    driver: bridge
```

### 3. 빌드 및 실행

```bash
docker-compose up -d --build
```

### 4. 포털에서 접근

NetDevOps Portal에서 **IP Manager** 카드를 클릭하거나 직접 접근합니다.

> **인증**: Authentik Forward Auth가 적용되어 있으므로 포털 로그인이 필요합니다.
> 미인증 상태에서 접근하면 Authentik 로그인 페이지로 리다이렉트됩니다.

---

## Usage

### 서버 자동 로드

컨테이너 시작 후 페이지에 접속하면 `/config` 디렉토리의 파일을 자동으로 파싱하여 표시합니다.

- **다시 불러오기** 버튼: 서버 디렉토리를 재파싱 (config 파일 변경 후 즉시 반영)
- 서버 모드 표시: 상단에 `서버 디렉토리` 아이콘과 경로가 표시됨

### 로컬 파일 업로드

서버에 없는 파일이 필요한 경우 **폴더 선택** 버튼으로 로컬 PC 폴더를 업로드할 수 있습니다.

1. **폴더 선택** 클릭 → OS 파일 탐색기에서 config 폴더 선택
2. 자동으로 벤더 감지 후 파싱 → IP 목록 표시
3. **다시 불러오기** 버튼으로 동일 폴더 재파싱

### 공통 기능

4. 상단 탭(전체 / System IP / Interface IP / Static Route)으로 필터링
5. 검색창에서 키워드 검색 (IP, 장비명, Peer 장비명 등)
6. `⚙` 아이콘으로 컬럼 표시 여부 및 순서 조정
7. 컬럼 헤더 우측 끝을 드래그하여 너비 조절
8. **Excel** 또는 **CSV** 버튼으로 내보내기

---

## Config 디렉토리 구조

`/data/configs` 디렉토리는 서브디렉토리 구조를 지원합니다.

```
/data/configs/
├── ISP/
│   ├── router-a_20260101.txt
│   └── router-b_20260101.txt
├── MPLS/
│   ├── pe-1_20260101.txt
│   └── pe-2_20260101.txt
└── CLOUD/
    └── leaf-1_20260101.txt
```

파일명 규칙: `{hostname}_{YYYYMMDD}.txt` (권장)

동일 장비의 날짜별 파일이 여러 개 있을 경우 **가장 최신 파일만** 자동 선택됩니다.

---

## Authentik 연동 구성

NetDevOps Portal의 nginx에서 Forward Auth를 처리합니다.

**nginx.conf (portal-frontend):**

```nginx
location /services/ip-manager/ {
    auth_request /outpost.goauthentik.io/auth/nginx;
    error_page 401 = @authentik_redirect;

    proxy_pass http://ip-manager:5001/;
    ...
}
```

별도의 Authentik Provider/Application 설정 없이 포털의 Forward Auth 정책이 자동으로 적용됩니다.

---

## Project Structure

```
network-config-ip-manager/
├── app.py                  # Flask 애플리케이션 (API 라우트)
├── parser/
│   ├── ip_parser.py        # Nokia SR OS config 파서 + 벤더 라우팅
│   └── arista_parser.py    # Arista EOS config 파서
├── templates/
│   └── index.html          # 단일 페이지 대시보드 (Bootstrap 5)
├── static/
│   ├── css/                # Bootstrap, Bootstrap Icons (로컬 내장)
│   └── js/                 # Bootstrap Bundle, SortableJS (로컬 내장)
├── docs/
│   ├── images/             # README 스크린샷
│   ├── nokia-timos-config-syntax.md
│   └── arista-eos-config-syntax.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .gitignore
```

---

## API Endpoints

| Method | Endpoint | 설명 |
|--------|----------|------|
| `GET` | `/` | 대시보드 페이지 |
| `POST` | `/api/upload` | 로컬 파일 업로드 및 파싱 (Nokia/Arista 자동 감지) |
| `POST` | `/api/load` | 서버 디렉토리 파싱 (`config_dir` 파라미터) |
| `GET` | `/api/export/excel` | Excel 다운로드 |
| `GET` | `/api/export/csv` | CSV 다운로드 |

---

## Environment Variables

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SECRET_KEY` | 랜덤 생성 | Flask 세션 시크릿 키 |
| `CONFIG_DIR` | `/config` | 서버 사이드 config 기본 경로 (컨테이너 내부 경로) |
| `TZ` | `Asia/Seoul` | 타임존 |

---

## Documentation

| 문서 | 설명 |
|------|------|
| [Nokia TiMOS Config 문법 레퍼런스](docs/nokia-timos-config-syntax.md) | OS 버전별 config 문법 차이, 파싱 정규식, Python 구현 예시 |
| [Arista EOS Config 문법 레퍼런스](docs/arista-eos-config-syntax.md) | EOS 인터페이스/Static Route 문법, VRF/VRRP 구조, Python 구현 예시 |

---

## Roadmap

- [x] Nokia SR OS config 파싱 (System IP, Interface IP, Static Route)
- [x] Arista EOS config 파싱 (v1.3.0)
- [x] Nokia/Arista 혼합 폴더 자동 파싱 (벤더 자동 감지)
- [x] 컬럼 너비 마우스 드래그 조절 (v1.3.0)
- [x] 서버 디렉토리 자동 로드 (server 브랜치)
- [x] 서브디렉토리 재귀 파싱 지원
- [x] NetDevOps Portal 통합 + Authentik Forward Auth
- [ ] VPRN / VPLS 인터페이스 파싱 지원
- [ ] IP 중복 검사 기능
- [ ] 변경 이력 비교 (이전 파싱 결과와 diff)

---

## License

This project is for internal use. All rights reserved.
