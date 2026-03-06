"""
Arista EOS Config IP Parser
Nokia ip_parser.py의 IpRecord 클래스를 재사용.

참조: docs/arista-eos-config-syntax.md
"""
import re
from pathlib import Path
from ipaddress import IPv4Network, IPv4Address, AddressValueError

from parser.ip_parser import (
    IpRecord,
    prefix_to_mask,
    get_network_address,
    extract_peer_from_desc,
)


# ─────────────────────────────────────────────
# 정규식 상수
# ─────────────────────────────────────────────

RE_DEVICE        = re.compile(r'^! device:\s+[\w\-]+\s+\(([^,]+),\s*(EOS-[\w.]+)\)', re.IGNORECASE)
RE_HOSTNAME      = re.compile(r'^hostname\s+(\S+)')
RE_IFACE_START   = re.compile(r'^interface\s+(\S+)', re.IGNORECASE)
RE_IP_ADDR       = re.compile(r'^\s+ip address\s+([\d.]+/\d+)(\s+secondary)?')
RE_DESCRIPTION   = re.compile(r'^\s+description\s+"?(.+?)"?\s*$')
RE_VRF_IFACE     = re.compile(r'^\s+vrf\s+(\S+)')
RE_VIRT_ROUTER   = re.compile(r'^\s+ip virtual-router address\s+([\d.]+)')
RE_VRRP_IP       = re.compile(r'^\s+vrrp\s+\d+\s+ipv4\s+([\d.]+)')

# Static Route — 파싱 순서: VRF+인터페이스 → VRF → Global+인터페이스 → Global 기본
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

# BGP 정보
RE_BGP_AS        = re.compile(r'^router bgp (\d+)')
RE_BGP_ROUTER_ID = re.compile(r'^\s+router-id\s+([\d.]+)')

# 파일명에서 날짜 추출 (예: _20260304.txt)
RE_FILENAME_DATE = re.compile(r'_(\d{4})(\d{2})(\d{2})\.txt$', re.IGNORECASE)

# L3 타입 분류
_L3_ALWAYS  = ('loopback', 'vlan')   # 항상 L3 (no switchport 없어도)
_L3_EXCLUDE = ('management', 'vxlan') # 파싱 제외

# 인터페이스 풀네임 → 숏네임 prefix 매핑 (순서 중요: 긴 이름 먼저)
_IFACE_SHORT_PREFIX = [
    ('Port-Channel', 'Po'),
    ('Ethernet',     'Et'),
    ('Loopback',     'Lo'),
    ('Vlan',         'Vl'),
    ('Vxlan',        'Vx'),
    ('Management',   'Ma'),
]


def _shorten_iface(name: str) -> str:
    """
    Arista 인터페이스 풀네임 → 숏네임 변환.
    예: Ethernet3 → Et3, Port-Channel1 → Po1, Loopback0 → Lo0, Vlan75 → Vl75
    변환 불가 시 원본 반환.
    """
    for full, short in _IFACE_SHORT_PREFIX:
        if name.startswith(full):
            return short + name[len(full):]
    return name


# ─────────────────────────────────────────────
# 벤더 감지
# ─────────────────────────────────────────────

def detect_vendor(config_text: str) -> str:
    """
    config 텍스트를 분석하여 'nokia' 또는 'arista' 반환.
    판별 불가 시 'unknown' 반환.
    """
    lines = config_text.split('\n')
    for line in lines[:15]:
        stripped = line.lstrip('\ufeff').strip()
        if stripped.startswith('# TiMOS-'):
            return 'nokia'
        if stripped.startswith('! device:') and 'EOS-' in stripped:
            return 'arista'
        if stripped.startswith('! Command:'):
            return 'arista'
    # CLI 프롬프트로 추가 판단
    first = lines[0].lstrip('\ufeff').strip() if lines else ''
    if '#show running-config' in first or '#sh run' in first:
        return 'arista'
    if '# admin display-config' in first:
        return 'nokia'
    return 'unknown'


# ─────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────

def _parse_config_date_from_filename(filename: str) -> str:
    """파일명에서 날짜 추출 → 'YYYY-MM-DD'. 없으면 ''."""
    m = RE_FILENAME_DATE.search(filename)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return ''


# ─────────────────────────────────────────────
# 파싱 함수
# ─────────────────────────────────────────────

def extract_device_info(config_text: str, filename: str) -> dict:
    """장비 기본 정보 추출"""
    info = {
        'filename':    filename,
        'hostname':    '',
        'model':       '',
        'os_version':  '',
        'location':    '',   # Arista에는 location 개념 없음
        'config_date': _parse_config_date_from_filename(filename),
        'system_ip':   '',
        'router_id':   '',
        'as_number':   '',
    }

    lines = config_text.split('\n')
    in_bgp = False
    bgp_indent = -1

    for line in lines:
        raw = line.rstrip('\r\n')
        stripped = raw.lstrip('\ufeff').strip()
        indent = len(raw) - len(raw.lstrip())

        # 모델 / OS 버전 (! device: 줄)
        if not info['model']:
            m = RE_DEVICE.match(stripped)
            if m:
                info['model']      = f'Arista {m.group(1).strip()}'
                info['os_version'] = m.group(2).strip()

        # 호스트명
        if not info['hostname']:
            m = RE_HOSTNAME.match(stripped)
            if m:
                info['hostname'] = m.group(1)

        # BGP AS / router-id 추출
        if not in_bgp:
            m = RE_BGP_AS.match(stripped)
            if m:
                in_bgp = True
                bgp_indent = indent
                info['as_number'] = m.group(1)
                continue
        else:
            # BGP 블록 종료 (들여쓰기가 bgp_indent와 같거나 작으면 종료)
            if stripped and not stripped.startswith('!') and indent <= bgp_indent:
                in_bgp = False
            elif not info['router_id']:
                m = RE_BGP_ROUTER_ID.match(raw)
                if m:
                    info['router_id'] = m.group(1)

    return info


def parse_interfaces(config_text: str) -> list[dict]:
    """
    L3 인터페이스 IP 추출.
    반환: [{'interface_name', 'ip', 'secondary_ips', 'description',
             'vrf', 'admin_state', 'virtual_ip'}, ...]
    """
    interfaces = []
    lines = config_text.split('\n')
    current = None
    block_lines = []

    def is_l3(iface_name: str, blines: list[str]) -> bool:
        iname_lower = iface_name.lower()
        if any(iname_lower.startswith(x) for x in _L3_EXCLUDE):
            return False
        if any(iname_lower.startswith(x) for x in _L3_ALWAYS):
            return True
        return any(l.strip() == 'no switchport' for l in blines)

    def flush():
        nonlocal current, block_lines
        if current is None:
            return
        if is_l3(current['interface_name'], block_lines) and current['ip']:
            interfaces.append(current)
        current = None
        block_lines = []

    for line in lines:
        raw = line.rstrip('\r\n')
        stripped = raw.strip()

        # 새 인터페이스 블록 시작
        m = RE_IFACE_START.match(stripped)
        if m:
            flush()
            current = {
                'interface_name': m.group(1),
                'ip':             '',
                'secondary_ips':  [],
                'description':    '',
                'vrf':            '',
                'admin_state':    'Active',  # Arista 기본: Active
                'virtual_ip':     '',
            }
            block_lines = []
            continue

        if current is None:
            continue

        # '!' 단독 줄 → 블록 종료
        if stripped == '!':
            flush()
            continue

        block_lines.append(raw)

        # ip address (primary)
        m = RE_IP_ADDR.match(raw)
        if m:
            if m.group(2):  # secondary
                current['secondary_ips'].append(m.group(1))
            else:
                current['ip'] = m.group(1)
            continue

        # description
        m = RE_DESCRIPTION.match(raw)
        if m:
            current['description'] = m.group(1).strip().strip('"')
            continue

        # vrf
        m = RE_VRF_IFACE.match(raw)
        if m:
            current['vrf'] = m.group(1)
            continue

        # shutdown
        if stripped == 'shutdown':
            current['admin_state'] = 'Shutdown'
            continue

        # ip virtual-router address
        m = RE_VIRT_ROUTER.match(raw)
        if m:
            current['virtual_ip'] = m.group(1)
            continue

        # vrrp N ipv4
        m = RE_VRRP_IP.match(raw)
        if m and not current['virtual_ip']:
            current['virtual_ip'] = m.group(1)

    flush()  # 마지막 블록 처리
    return interfaces


def parse_static_routes(config_text: str) -> list[dict]:
    """
    모든 형식의 Static Route 파싱.
    반환: [{'prefix', 'next_hop', 'vrf', 'exit_interface', 'description', 'admin_state'}, ...]
    """
    routes = []
    for line in config_text.split('\n'):
        stripped = line.strip()
        if not stripped.startswith('ip route'):
            continue

        # ① VRF + 출구 인터페이스 (+ name)
        m = RE_ROUTE_VRF_IFACE.match(stripped)
        if m:
            routes.append({
                'vrf':            m.group(1),
                'prefix':         m.group(2),
                'exit_interface': m.group(3),
                'next_hop':       m.group(4),
                'description':    m.group(5) or '',
                'admin_state':    'Active',
            })
            continue

        # ② VRF + next-hop (+ name)
        m = RE_ROUTE_VRF.match(stripped)
        if m:
            routes.append({
                'vrf':            m.group(1),
                'prefix':         m.group(2),
                'exit_interface': '',
                'next_hop':       m.group(3),
                'description':    m.group(4) or '',
                'admin_state':    'Active',
            })
            continue

        # ③ Global + 출구 인터페이스
        m = RE_ROUTE_IFACE.match(stripped)
        if m:
            routes.append({
                'vrf':            '',
                'prefix':         m.group(1),
                'exit_interface': m.group(2),
                'next_hop':       m.group(3),
                'description':    '',
                'admin_state':    'Active',
            })
            continue

        # ④ Global 기본
        m = RE_ROUTE_BASIC.match(stripped)
        if m:
            routes.append({
                'vrf':            '',
                'prefix':         m.group(1),
                'exit_interface': '',
                'next_hop':       m.group(2),
                'description':    '',
                'admin_state':    'Active',
            })

    return routes


# ─────────────────────────────────────────────
# 전체 파싱 (파일 1개)
# ─────────────────────────────────────────────

def parse_config_file(filepath: str) -> list[IpRecord]:
    """단일 Arista EOS config 파일을 파싱하여 IpRecord 목록 반환"""
    path = Path(filepath)
    filename = path.name

    try:
        config_text = path.read_text(encoding='utf-8-sig', errors='replace')
    except Exception:
        return []

    device   = extract_device_info(config_text, filename)
    ifaces   = parse_interfaces(config_text)
    routes   = parse_static_routes(config_text)
    records: list[IpRecord] = []

    def make_base(ip_type: str, cidr: str) -> dict:
        parts = cidr.split('/')
        ip    = parts[0]
        prefix = int(parts[1]) if len(parts) == 2 else 32
        return dict(
            cidr=cidr,
            ip_address=ip,
            prefix_length=prefix,
            subnet_mask=prefix_to_mask(prefix),
            network_address=get_network_address(cidr),
            ip_type=ip_type,
            device_name=device['hostname'] or filename,
            device_model=device['model'],
            location=device['location'],
            os_version=device['os_version'],
            config_date=device['config_date'],
            router_id=device['router_id'],
            as_number=device['as_number'],
            filename=filename,
        )

    # ── 1. System IP (Loopback0) ──
    loopback0 = next(
        (i for i in ifaces if i['interface_name'].lower() == 'loopback0'),
        None
    )
    if loopback0 and loopback0['ip']:
        b = make_base('System IP', loopback0['ip'])
        records.append(IpRecord(
            **b,
            interface_name='Loopback0',
            port='Lo0',
            interface_desc=loopback0['description'],
            port_desc='',
            peer_device='',
            peer_port='',
            next_hop_ip='',
            route_desc='',
            admin_state=loopback0['admin_state'],
        ))

    # ── 2. Interface IP (Loopback0 제외) ──
    for iface in ifaces:
        iname = iface['interface_name']
        if iname.lower() == 'loopback0':
            continue

        peer_device, peer_port = extract_peer_from_desc(iface['description'])
        b = make_base('Interface IP', iface['ip'])

        # VRF 정보는 interface_desc 뒤에 덧붙여 표시 (별도 필드 없음)
        desc = iface['description']
        vrf  = iface['vrf']

        records.append(IpRecord(
            **b,
            interface_name=iname,
            port=_shorten_iface(iname),
            interface_desc=desc,
            port_desc=f'VRF:{vrf}' if vrf else '',
            peer_device=peer_device,
            peer_port=peer_port,
            next_hop_ip='',
            route_desc='',
            admin_state=iface['admin_state'],
        ))

    # ── 로컬 서브넷 맵 (next-hop 출구 인터페이스 추론용) ──
    local_subnet_map: list[tuple] = []
    for _iface in ifaces:
        if not _iface['ip']:
            continue
        try:
            net = IPv4Network(_iface['ip'], strict=False)
            local_subnet_map.append((
                net,
                _iface['interface_name'],
                _shorten_iface(_iface['interface_name']),  # port = 숏네임
                _iface['description'],
                f"VRF:{_iface['vrf']}" if _iface['vrf'] else '',
            ))
        except (AddressValueError, ValueError):
            pass
        for sec in _iface['secondary_ips']:
            try:
                snet = IPv4Network(sec, strict=False)
                local_subnet_map.append((
                    snet,
                    _iface['interface_name'],
                    _shorten_iface(_iface['interface_name']),
                    _iface['description'],
                    f"VRF:{_iface['vrf']}" if _iface['vrf'] else '',
                ))
            except (AddressValueError, ValueError):
                pass

    def find_egress(nh_ip: str, exit_iface: str):
        """next-hop IP로 출구 인터페이스 반환 (interface_name, port, idesc, pdesc)"""
        # 출구 인터페이스가 명시된 경우 우선 사용
        if exit_iface:
            return exit_iface, _shorten_iface(exit_iface), '', ''
        if not nh_ip:
            return '', '', '', ''
        try:
            addr = IPv4Address(nh_ip)
            for net, iname, port, idesc, pdesc in local_subnet_map:
                if addr in net and (net.prefixlen >= 31 or str(addr) != str(net.network_address)):
                    return iname, port, idesc, pdesc
        except (AddressValueError, ValueError):
            pass
        return '', '', '', ''

    # ── 3. Static Route ──
    for route in routes:
        b = make_base('Static Route', route['prefix'])
        peer_device, peer_port = extract_peer_from_desc(route['description'])
        egress_name, egress_port, egress_idesc, egress_pdesc = find_egress(
            route['next_hop'], route.get('exit_interface', '')
        )

        # VRF 정보를 route_desc 앞에 표시
        vrf  = route.get('vrf', '')
        name = route.get('description', '')
        route_desc = f'[VRF:{vrf}] {name}'.strip() if vrf else name

        records.append(IpRecord(
            **b,
            interface_name=egress_name,
            port=egress_port,
            interface_desc=egress_idesc,
            port_desc=egress_pdesc,
            peer_device=peer_device,
            peer_port=peer_port,
            next_hop_ip=route['next_hop'],
            route_desc=route_desc,
            admin_state=route['admin_state'],
        ))

    return records
