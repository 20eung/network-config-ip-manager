# Arista EOS Config 문법 레퍼런스

> Arista EOS config 파일을 파싱할 때 알아야 할 구조와 문법을 정리한 문서입니다.
> Nokia `docs/nokia-timos-config-syntax.md`와 대응되는 Arista 전용 레퍼런스입니다.

---

## 목차

1. [config 파일 구조 개요](#1-config-파일-구조-개요)
2. [파일 헤더 형식](#2-파일-헤더-형식)
3. [EOS 버전 및 장비 모델 분류](#3-eos-버전-및-장비-모델-분류)
4. [인터페이스 종류와 명명 규칙](#4-인터페이스-종류와-명명-규칙)
5. [L3 인터페이스 블록 문법](#5-l3-인터페이스-블록-문법)
6. [Static Route 문법](#6-static-route-문법)
7. [VRF 구조](#7-vrf-구조)
8. [VRRP / Virtual-Router IP](#8-vrrp--virtual-router-ip)
9. [파일 인코딩 및 특수 케이스](#9-파일-인코딩-및-특수-케이스)
10. [Nokia TiMOS와의 주요 차이점](#10-nokia-timos와의-주요-차이점)
11. [Python 파싱 구현 예시](#11-python-파싱-구현-예시)
12. [장비 모델별 요약 매트릭스](#12-장비-모델별-요약-매트릭스)

---

## 1. config 파일 구조 개요

Arista EOS config 파일은 **3 스페이스 들여쓰기** 기반의 계층 블록 구조입니다.
탭 문자는 사용하지 않습니다.

```
! Command: show running-config
! device: EXAMPLE-SITE1-7020SR-Leaf-1 (DCS-7020SR-24C2, EOS-4.27.6M)
!
hostname EXAMPLE_SITE1_7020SR_Leaf_1
!
interface Ethernet3
   description EXAMPLE_REMOTE1_7020SR_Leaf_1 - Eth5
   mtu 9214
   no switchport
   ip address 192.0.2.58/30
!
interface Loopback0
   ip address 192.0.2.7/32
!
ip route 0.0.0.0/0 192.0.2.1
!
```

블록 구조 규칙:
- 블록 구분자: `!` (느낌표) — Nokia의 `exit`와 달리 닫는 키워드 없음
- 들여쓰기: **3 스페이스**로 블록 내부를 표현
- 주석: `!`로 시작 (Nokia는 `#`)
- `! Command:`, `! device:` 등의 메타 줄은 파싱 무시

---

## 2. 파일 헤더 형식

### 2.1 첫 줄: CLI 프롬프트 (장비 호스트명 포함)

config를 터미널에서 캡처한 파일은 첫 줄에 CLI 프롬프트가 포함됩니다.

```
EXAMPLE_SITE1_7020SR_Leaf_1#show running-config
```
```
EXAMPLE-SITE2-7280SR2-BB10#sh run
```
```
EXAMPLE_SITE3_MMR_7304X3_Spine_1(s1)#show running-config
```

특이사항:
- 호스트명에 언더스코어(`_`) 또는 하이픈(`-`) 사용
- 섀시/슬롯 번호가 있는 경우 `hostname(s1)#` 형태 — 슬롯 번호는 괄호 안에 포함
- 파일 앞에 UTF-8 BOM(`\ufeff`)이 있을 수 있음

### 2.2 메타 주석 줄

```
! Command: show running-config
! device: EXAMPLE-SITE1-7020SR-Leaf-1 (DCS-7020SR-24C2, EOS-4.27.6M)
```

`! device:` 줄에서 장비 모델과 EOS 버전을 추출합니다.

**형식**: `! device: {hostname} ({model}, {eos-version})`

```
! device: EXAMPLE-SITE1-7020SR-Leaf-1 (DCS-7020SR-24C2, EOS-4.27.6M)
! device: EXAMPLE-SITE2-7280SR2-BB10 (DCS-7280SR2-48YC6, EOS-4.23.0F)
! device: EXAMPLE-SITE3-MMR-7304X3-Spine-1 (DCS-7304, EOS-4.24.3M)
! device: EXAMPLE-SITE4-7280SR2-BR1 (DCS-7280SR2-48YC6, EOS-4.32.5.1M)
```

**파싱 정규식**:

```python
RE_DEVICE = re.compile(
    r'^! device:\s+([\w\-]+)\s+\(([^,]+),\s*(EOS-[\w.]+)\)',
    re.IGNORECASE
)
# group(1) = hostname (from device line)
# group(2) = model     (e.g., "DCS-7020SR-24C2")
# group(3) = eos_ver   (e.g., "EOS-4.27.6M")
```

### 2.3 hostname 명령

config 파일 내부에 `hostname` 명령이 별도로 있습니다.

```
hostname EXAMPLE_SITE1_7020SR_Leaf_1
hostname EXAMPLE-SITE2-7280SR2-BB10
```

> **중요**: `! device:` 줄의 호스트명과 `hostname` 명령의 값이 하이픈/언더스코어 차이로 다를 수 있습니다.
> 파싱 시 `hostname` 명령의 값을 우선 사용하세요.

```python
RE_HOSTNAME = re.compile(r'^hostname\s+(\S+)')
```

---

## 3. EOS 버전 및 장비 모델 분류

### 3.1 EOS 버전 명명 체계

```
EOS-{메이저}.{마이너}.{패치}{트레인}
         │         │
         │         └── F: Feature release
         │             M: Maintenance release (권장)
         └── 4.x.x: 현재 주요 버전 계열
```

예:
```
EOS-4.23.0F    → 4.23 Feature 릴리즈
EOS-4.24.3M    → 4.24 Maintenance 릴리즈
EOS-4.27.6M    → 4.27 Maintenance 릴리즈
EOS-4.32.5.1M  → 4.32 Maintenance 릴리즈 (sub-patch 포함)
```

### 3.2 장비 모델 및 EOS 버전 목록

| 장비 모델 | EOS 버전 | 역할 | 비고 |
|----------|---------|------|------|
| DCS-7020SR-24C2 | 4.27.6M | Leaf / EVPN | Ethernet 1~24, Ethernet25/1~26/1 |
| DCS-7280SR2-48YC6 | 4.23.0F, 4.32.5.1M | BB / BR | Ethernet 1~48, Ethernet49/1~54/1 |
| DCS-7304 | 4.24.3M | Spine (Modular) | Ethernet3/1/1 ~ 3/N/1 (슬롯/카드/포트) |

### 3.3 EOS 버전 정규식

```python
RE_EOS_VER = re.compile(r'EOS-([\d.]+[FM]?)', re.IGNORECASE)
```

---

## 4. 인터페이스 종류와 명명 규칙

### 4.1 Ethernet 인터페이스

| 형식 | 예시 | 장비 유형 |
|------|------|---------|
| `EthernetN` | `Ethernet1`, `Ethernet48` | 고정형 (7020SR, 7280SR2) |
| `EthernetN/1` | `Ethernet25/1`, `Ethernet49/1` | QSFP 분할 포트 |
| `EthernetS/C/N` | `Ethernet3/1/1`, `Ethernet3/31/1` | 모듈형 섀시 (7304X3) — 슬롯/카드/포트 |

**정규식** (모든 형식 통합):
```python
RE_IFACE_ETHERNET = re.compile(
    r'^interface\s+(Ethernet\d+(?:/\d+)*)',
    re.IGNORECASE
)
```

### 4.2 Port-Channel (LAG)

```
interface Port-Channel1
interface Port-Channel21
interface Port-Channel2000
```

**정규식**:
```python
RE_IFACE_PORTCHANNEL = re.compile(
    r'^interface\s+(Port-Channel\d+)',
    re.IGNORECASE
)
```

### 4.3 Loopback

```
interface Loopback0
interface Loopback1
```

Loopback1은 VTEP(VXLAN Tunnel Endpoint) 용도로 사용됩니다.

### 4.4 VLAN 인터페이스 (SVI)

```
interface Vlan75
interface Vlan4094
```

> Nokia의 IES service 블록과 대응. VLAN 인터페이스는 L2 VLAN에 IP를 부여하는 SVI(Switched Virtual Interface)입니다.

### 4.5 Management

```
interface Management1
```

일반적으로 IP 설정 없이 shutdown 상태이거나 OOB 관리 IP가 할당됩니다.
파싱 시 제외하거나 별도 표시 권장.

### 4.6 Vxlan

```
interface Vxlan1
   vxlan source-interface Loopback1
   vxlan vlan 75 vni 10075
```

IP 주소가 없으므로 IP 파싱에서 제외.

---

## 5. L3 인터페이스 블록 문법

### 5.1 L3 인터페이스 식별

Arista에서 인터페이스는 기본적으로 L2(스위치포트) 모드입니다.
`no switchport` 명령이 있어야 L3(라우팅) 모드입니다.

예외:
- `Loopback` 인터페이스: 항상 L3
- `Vlan` 인터페이스(SVI): 항상 L3
- `Management` 인터페이스: 항상 L3 (파싱 제외 권장)

```
interface Ethernet3
   description EXAMPLE_REMOTE1_7020SR_Leaf_1 - Eth5
   mtu 9214
   no switchport          ← 이 줄이 있어야 L3
   ip address 192.0.2.58/30
!
```

### 5.2 L3 인터페이스 핵심 필드

| 키워드 | 설명 | 필수 여부 |
|--------|------|-----------|
| `no switchport` | L3 모드 활성화 | L3 식별자 (Loopback/Vlan 제외) |
| `ip address X.X.X.X/N` | IP/prefix | 선택 |
| `ip address X.X.X.X/N secondary` | 보조 IP | 선택 |
| `vrf VRF_NAME` | VRF 귀속 | 선택 |
| `description "..."` 또는 `description ...` | 설명 | 선택 |
| `shutdown` | 비활성화 | 없으면 Active |
| `mtu N` | MTU 크기 | 선택 |

> **Nokia와 차이**: Nokia는 `no shutdown`이 있어야 Active.
> Arista는 반대로 `shutdown`이 **없으면** Active, `shutdown`이 **있으면** Shutdown.

### 5.3 완전한 L3 인터페이스 예시

```
interface Ethernet10
   description CORP_Azure_ER_1638
   no switchport
   vrf CORP_Azure_ER_1638
   ip address 10.10.40.170/30
   shape rate 2 percent
!
```

```
interface Vlan609
   description CORP_Azure_ER_1609_Downlink(SITE2-FW)
   mtu 9214
   vrf CORP_Azure_ER_1609
   ip address 10.10.40.146/29
   ip virtual-router address 10.10.40.145
!
```

```
interface Loopback0
   ip address 192.0.2.7/32
!
```

### 5.4 VLAN 범위 지정 ⚠️

`interface Vlan` 뒤에 범위가 아닌 단일 번호만 옵니다. 범위 지정은 `vlan` 선언부에서만 사용됩니다.

```
vlan 469,1469          ← 복수 VLAN ID (선언부)
   name CORP_DX_469

interface Vlan469      ← 단일 VLAN ID (인터페이스 설정)
   ip address 192.0.2.177/30
```

### 5.5 파싱 전략

```python
def is_l3_interface(iface_type: str, lines_in_block: list[str]) -> bool:
    """
    인터페이스 블록이 L3인지 판단.
    Loopback, Vlan은 항상 L3.
    Ethernet, Port-Channel은 'no switchport'가 있어야 L3.
    Management는 파싱 제외 권장.
    """
    lower_type = iface_type.lower()
    if lower_type.startswith('loopback'):
        return True
    if lower_type.startswith('vlan'):
        return True
    if lower_type.startswith('management'):
        return False
    if lower_type.startswith('vxlan'):
        return False
    # Ethernet, Port-Channel: 'no switchport' 필요
    return any(l.strip() == 'no switchport' for l in lines_in_block)
```

---

## 6. Static Route 문법

### 6.1 기본 형식 (Global)

```
ip route DEST/PREFIX NEXT-HOP
```

예:
```
ip route 203.0.113.0/26 203.0.113.194
```

### 6.2 출구 인터페이스 명시 형식 ⚠️

```
ip route DEST/PREFIX INTERFACE NEXT-HOP
```

예:
```
ip route 203.0.113.0/26 Ethernet1 203.0.113.194
ip route 172.16.0.0/16 Port-Channel1 203.0.113.178
```

인터페이스명 다음에 next-hop IP가 옵니다. `INTERFACE`만 있고 `NEXT-HOP`이 없는 경우:
```
ip route 0.0.0.0/0 Ethernet1    ← next-hop 없이 출구 인터페이스만
```

### 6.3 VRF 형식

```
ip route vrf VRF_NAME DEST/PREFIX NEXT-HOP
ip route vrf VRF_NAME DEST/PREFIX NEXT-HOP name ROUTE_NAME
```

예:
```
ip route vrf CORP_Azure_ER_75 10.20.8.0/24 10.20.22.220 name CORP
ip route vrf CORP_Azure_ER_1609 10.0.0.0/8 10.10.40.148
ip route vrf CORP_DX_469 0.0.0.0/0 10.20.159.254 name DEFAULT_ROUTE
```

### 6.4 `name` 필드 (Description 역할)

Nokia의 `description "..."` 에 해당하는 필드. 따옴표 없이 키워드 뒤에 위치합니다.

```
ip route vrf CORP_Azure_ER_1638 10.78.0.0/16 10.10.40.169 name CORP_Azure_ER_1638
ip route vrf CORP_DX_469 0.0.0.0/0 10.20.159.254 name DEFAULT_ROUTE
ip route vrf CORP_DX_469 10.10.48.0/24 10.20.159.254 name VDI_HOST
```

### 6.5 Static Route 형식 요약

| 형식 | 예시 | VRF | 출구 인터페이스 | name |
|------|------|-----|---------------|------|
| 기본 | `ip route 0.0.0.0/0 192.0.2.1` | - | - | - |
| 출구 인터페이스 | `ip route 0.0.0.0/0 Eth1 192.0.2.1` | - | ✅ | - |
| VRF | `ip route vrf VRF 0.0.0.0/0 192.0.2.1` | ✅ | - | - |
| VRF + name | `ip route vrf VRF 0.0.0.0/0 192.0.2.1 name DESC` | ✅ | - | ✅ |
| VRF + 출구 + name | `ip route vrf VRF 0.0.0.0/0 Eth1 192.0.2.1 name DESC` | ✅ | ✅ | ✅ |

### 6.6 파싱 정규식

```python
# VRF + 출구 인터페이스 + name (가장 복잡한 형식 — 먼저 처리)
RE_ROUTE_VRF_IFACE_NAME = re.compile(
    r'^ip route vrf (\S+) ([\d./]+) (\S+) ([\d.]+)(?: name (\S+))?$'
)

# VRF + next-hop + name
RE_ROUTE_VRF = re.compile(
    r'^ip route vrf (\S+) ([\d./]+) ([\d.]+)(?: name (\S+))?$'
)

# 출구 인터페이스 + next-hop (Global)
RE_ROUTE_IFACE = re.compile(
    r'^ip route ([\d./]+) ([A-Za-z][\S]*) ([\d.]+)$'
)

# 기본 (Global)
RE_ROUTE_BASIC = re.compile(
    r'^ip route ([\d./]+) ([\d.]+)$'
)
```

> **파싱 순서 중요**: VRF 형식을 Global 형식보다 먼저 처리해야 합니다.
> 출구 인터페이스 형식은 3번째 필드가 영문자로 시작하는지로 구분합니다.

---

## 7. VRF 구조

### 7.1 VRF 선언

```
vrf instance VRF_NAME
!
```

예:
```
vrf instance PARTNER_Azure_ER
!
vrf instance CORP_AWS_DX_153
!
vrf instance CORP_Azure_ER_1609
!
```

### 7.2 인터페이스에 VRF 귀속

```
interface EthernetN
   no switchport
   vrf VRF_NAME
   ip address X.X.X.X/N
!
```

`vrf` 명령은 `ip address` 이전에 위치해야 합니다 (EOS 제약).

### 7.3 VRF 파싱 전략

```python
RE_VRF_DECL = re.compile(r'^vrf instance (\S+)')
RE_VRF_IFACE = re.compile(r'^\s+vrf (\S+)')  # 인터페이스 블록 내부
```

---

## 8. VRRP / Virtual-Router IP

### 8.1 VRRP (Virtual Router Redundancy Protocol)

```
interface Vlan1075
   vrf CORP_Azure_ER_75
   ip address 10.20.22.218/29
   vrrp 1 priority-level 150
   vrrp 1 ipv4 10.20.22.217         ← VRRP 가상 IP
!
```

- `vrrp N ipv4 X.X.X.X`: VRRP 그룹 N의 가상 IP
- `vrrp N priority-level N`: VRRP 우선순위 (높을수록 Master)
- `no vrrp N preempt`: 선점 비활성화

### 8.2 IP Virtual-Router (EVPN Anycast)

EVPN 환경에서 게이트웨이 이중화에 사용합니다.

```
interface Vlan609
   vrf CORP_Azure_ER_1609
   ip address 10.10.40.146/29
   ip virtual-router address 10.10.40.145   ← EVPN Anycast 가상 IP
!
```

글로벌 MAC 설정:
```
ip virtual-router mac-address 00:1c:73:00:00:01
```

### 8.3 파싱 정규식

```python
RE_VRRP_IP    = re.compile(r'^\s+vrrp \d+ ipv4 ([\d.]+)')
RE_VIRT_ROUTER = re.compile(r'^\s+ip virtual-router address ([\d.]+)')
```

---

## 9. 파일 인코딩 및 특수 케이스

### 9.1 UTF-8 BOM

Nokia와 동일하게 파일 앞에 UTF-8 BOM(`\ufeff`)이 있는 경우가 있습니다.

```python
config_text = path.read_text(encoding='utf-8-sig', errors='replace')
```

### 9.2 줄 끝 문자

Nokia와 동일하게 `\r\n`이 혼재할 수 있습니다.

```python
line.rstrip('\r\n')
```

### 9.3 description 따옴표 혼용

Arista에서 description은 따옴표가 있는 경우와 없는 경우가 혼재합니다.

```
interface Port-Channel1
   description "To_EXAMPLE_Internet-PortChannel#2"   ← 따옴표 있음

interface Ethernet3
   description EXAMPLE_REMOTE1_7020SR_Leaf_1 - Eth5  ← 따옴표 없음
```

**파싱 정규식**:
```python
RE_DESCRIPTION = re.compile(r'^\s+description\s+"?(.+?)"?\s*$')
```

### 9.4 파일명 형식

```
{사이트}_{장비명}_{날짜}.txt
```

예:
```
EXAMPLE_SITE1_7020SR_Leaf1_20260304.txt
EXAMPLE_SITE4_7280SR2_BR1_20260304.txt
EXAMPLE_SITE2_7280SR2_BB10_20260222.txt
```

파일명에서 날짜를 추출하는 정규식:
```python
RE_FILENAME_DATE = re.compile(r'_(\d{8})\.txt$')
```

> **주의**: `hostname` 명령과 파일명의 장비명이 다를 수 있습니다.
> config 내부 `hostname` 값을 장비 식별자로 우선 사용하세요.

---

## 10. Nokia TiMOS와의 주요 차이점

| 항목 | Nokia TiMOS | Arista EOS |
|------|------------|------------|
| 주석 문자 | `#` | `!` |
| 들여쓰기 | 4 스페이스 | 3 스페이스 |
| 블록 닫기 | `exit` 키워드 | 없음 (`!`로 섹션 구분) |
| L3 인터페이스 식별 | `address X.X.X.X/N`이 있으면 L3 | `no switchport` 키워드 필요 |
| Active 상태 기본값 | `no shutdown`이 있어야 Active | `shutdown`이 없으면 Active |
| Static Route | `static-route` / `static-route-entry` | `ip route` |
| Static Route VRF | 별도 VRF 블록 내에 선언 | `ip route vrf VRF` (인라인) |
| 장비 식별자 | `system > name "..."` | `hostname` 명령 |
| 헤더 형식 | `# TiMOS-...` | `! device: hostname (model, EOS-ver)` |
| VRF 표현 | IES service 블록 | `vrf instance` + 인터페이스 내 `vrf` |
| LAG 포트명 | `lag-1`, `lag-2` | `Port-Channel1`, `Port-Channel2000` |
| Loopback | `interface "system"` (특수) | `interface Loopback0`, `Loopback1` |

---

## 11. Python 파싱 구현 예시

### 11.1 파일 헤더 파싱 (모델, EOS 버전, 호스트명)

```python
import re

RE_DEVICE   = re.compile(r'^! device:\s+([\w\-]+)\s+\(([^,]+),\s*(EOS-[\w.]+)\)', re.IGNORECASE)
RE_HOSTNAME = re.compile(r'^hostname\s+(\S+)')

def parse_header(config_text: str) -> dict:
    """
    Returns {'hostname': ..., 'model': ..., 'eos_version': ...}
    """
    result = {'hostname': '', 'model': '', 'eos_version': ''}
    for line in config_text.split('\n')[:30]:
        line = line.strip()
        m = RE_DEVICE.match(line)
        if m and not result['model']:
            result['model'] = m.group(2).strip()
            result['eos_version'] = m.group(3).strip()
        m = RE_HOSTNAME.match(line)
        if m:
            result['hostname'] = m.group(1)
            break  # hostname 발견 후 조기 종료
    return result
```

### 11.2 인터페이스 IP 파싱

```python
RE_IFACE_START = re.compile(r'^interface\s+(\S+)', re.IGNORECASE)
RE_IP_ADDR     = re.compile(r'^\s+ip address\s+([\d.]+/\d+)(\s+secondary)?')
RE_DESCRIPTION = re.compile(r'^\s+description\s+"?(.+?)"?\s*$')
RE_VRF_IFACE   = re.compile(r'^\s+vrf\s+(\S+)')
RE_VIRT_ROUTER = re.compile(r'^\s+ip virtual-router address\s+([\d.]+)')
RE_VRRP_IP     = re.compile(r'^\s+vrrp \d+ ipv4\s+([\d.]+)')

L3_ALWAYS = {'loopback', 'vlan'}         # 항상 L3
L3_EXCLUDE = {'management', 'vxlan'}     # 제외 대상

def parse_interfaces(config_text: str) -> list[dict]:
    """
    L3 인터페이스의 IP 주소 목록 반환.
    반환값: [{'interface': ..., 'ip': ..., 'description': ...,
              'vrf': ..., 'admin_state': ..., 'virtual_ip': ...}, ...]
    """
    interfaces = []
    lines = config_text.split('\n')
    current = None
    block_lines = []

    def flush_current():
        nonlocal current, block_lines
        if current is None:
            return
        iname_lower = current['interface'].lower()

        exclude = any(iname_lower.startswith(x) for x in L3_EXCLUDE)
        always_l3 = any(iname_lower.startswith(x) for x in L3_ALWAYS)
        has_no_switchport = any(l.strip() == 'no switchport' for l in block_lines)

        is_l3 = (always_l3 or has_no_switchport) and not exclude
        if is_l3 and current.get('ip'):
            interfaces.append(current)
        current = None
        block_lines = []

    for line in lines:
        raw = line.rstrip('\r\n')
        stripped = raw.strip()

        # 새 인터페이스 블록 시작
        m = RE_IFACE_START.match(stripped)
        if m:
            flush_current()
            current = {
                'interface': m.group(1),
                'ip': '',
                'description': '',
                'vrf': '',
                'admin_state': 'Active',  # 기본값: Active
                'virtual_ip': '',
            }
            block_lines = []
            continue

        if current is None:
            continue

        # 블록 구분자 ('!' 단독 줄) → 블록 종료
        if stripped == '!':
            flush_current()
            continue

        block_lines.append(raw)

        m = RE_IP_ADDR.match(raw)
        if m and not m.group(2):  # secondary 제외 (primary만)
            current['ip'] = m.group(1)
            continue

        m = RE_DESCRIPTION.match(raw)
        if m:
            current['description'] = m.group(1).strip()
            continue

        m = RE_VRF_IFACE.match(raw)
        if m:
            current['vrf'] = m.group(1)
            continue

        if stripped == 'shutdown':
            current['admin_state'] = 'Shutdown'
            continue

        m = RE_VIRT_ROUTER.match(raw)
        if m:
            current['virtual_ip'] = m.group(1)
            continue

        m = RE_VRRP_IP.match(raw)
        if m and not current.get('virtual_ip'):
            current['virtual_ip'] = m.group(1)
            continue

    flush_current()
    return interfaces
```

### 11.3 Static Route 파싱

```python
# 파싱 순서: VRF 형식 → Global 형식 (VRF 먼저)
RE_ROUTE_VRF_IFACE = re.compile(
    r'^ip route vrf (\S+) ([\d.]+/\d+) ([A-Za-z]\S*) ([\d.]+)(?:\s+name (\S+))?$'
)
RE_ROUTE_VRF = re.compile(
    r'^ip route vrf (\S+) ([\d.]+/\d+) ([\d.]+)(?:\s+name (\S+))?$'
)
RE_ROUTE_IFACE = re.compile(
    r'^ip route ([\d.]+/\d+) ([A-Za-z]\S*) ([\d.]+)$'
)
RE_ROUTE_BASIC = re.compile(
    r'^ip route ([\d.]+/\d+) ([\d.]+)$'
)

def parse_static_routes(config_text: str) -> list[dict]:
    """
    모든 형식의 Static Route 파싱.
    반환값: [{'prefix': ..., 'next_hop': ..., 'vrf': ...,
              'exit_interface': ..., 'description': ..., 'admin_state': ...}, ...]
    """
    routes = []
    for line in config_text.split('\n'):
        stripped = line.strip()
        if not stripped.startswith('ip route'):
            continue

        # ① VRF + 출구 인터페이스
        m = RE_ROUTE_VRF_IFACE.match(stripped)
        if m:
            routes.append({
                'vrf': m.group(1),
                'prefix': m.group(2),
                'exit_interface': m.group(3),
                'next_hop': m.group(4),
                'description': m.group(5) or '',
                'admin_state': 'Active',
            })
            continue

        # ② VRF + next-hop
        m = RE_ROUTE_VRF.match(stripped)
        if m:
            routes.append({
                'vrf': m.group(1),
                'prefix': m.group(2),
                'exit_interface': '',
                'next_hop': m.group(3),
                'description': m.group(4) or '',
                'admin_state': 'Active',
            })
            continue

        # ③ Global + 출구 인터페이스
        m = RE_ROUTE_IFACE.match(stripped)
        if m:
            routes.append({
                'vrf': '',
                'prefix': m.group(1),
                'exit_interface': m.group(2),
                'next_hop': m.group(3),
                'description': '',
                'admin_state': 'Active',
            })
            continue

        # ④ Global 기본
        m = RE_ROUTE_BASIC.match(stripped)
        if m:
            routes.append({
                'vrf': '',
                'prefix': m.group(1),
                'exit_interface': '',
                'next_hop': m.group(2),
                'description': '',
                'admin_state': 'Active',
            })

    return routes
```

### 11.4 벤더 자동 감지

Nokia와 Arista 파일을 자동으로 구분하는 함수:

```python
def detect_vendor(config_text: str) -> str:
    """
    'nokia' 또는 'arista' 반환.
    """
    lines = config_text.split('\n')
    for line in lines[:10]:
        stripped = line.strip()
        # Nokia TiMOS 헤더
        if stripped.startswith('# TiMOS-'):
            return 'nokia'
        # Arista EOS 헤더
        if stripped.startswith('! device:') and 'EOS-' in stripped:
            return 'arista'
        if stripped.startswith('! Command:'):
            return 'arista'
    # CLI 프롬프트로 추가 판단
    first_line = lines[0].lstrip('\ufeff').strip() if lines else ''
    if '#show running-config' in first_line or '#sh run' in first_line:
        return 'arista'
    if '# admin display-config' in first_line:
        return 'nokia'
    return 'unknown'
```

---

## 12. 장비 모델별 요약 매트릭스

| 장비 모델 | EOS 버전 | Ethernet 포트 형식 | L3 인터페이스 종류 | Static Route | VRRP | EVPN/VXLAN |
|----------|---------|-----------------|-----------------|-------------|------|------------|
| DCS-7020SR-24C2 | 4.27.6M | Eth1~24, Eth25/1, 26/1 | Eth(no sw), Vlan(SVI), Loopback | VRF 위주 | VRRP + virtual-router | ✅ (Leaf) |
| DCS-7280SR2-48YC6 | 4.23.0F | Eth1~48, Eth49/1~54/1 | Eth(no sw), Vlan(SVI), Loopback | Global + VRF | VRRP | - |
| DCS-7280SR2-48YC6 | 4.32.5.1M | 동일 | Eth(no sw), Loopback | Global (출구 인터페이스 포함) | - | - |
| DCS-7304 | 4.24.3M | EthS/C/N (3/1/1~3/N/1) | Eth(no sw), Loopback | - | - | - |

> **범례**:
> - `Eth(no sw)` = `no switchport`가 있는 Ethernet 인터페이스
> - `Vlan(SVI)` = VLAN 인터페이스 (Switched Virtual Interface)
> - `EVPN/VXLAN` = EVPN/VXLAN 기능 사용 여부

---

*최종 업데이트: 2026-03-06*
*Arista EOS 장비 config 파일(EOS-4.23.0F ~ EOS-4.32.5.1M) 분석 결과를 바탕으로 작성*
