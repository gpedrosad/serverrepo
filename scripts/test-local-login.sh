#!/usr/bin/env bash
# Prueba login cuenta + mundo contra el servidor local (sin cliente gráfico).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ACCOUNT="${1:-275783}"
PASSWORD="${2:-123456qa}"
CHAR="${3:-Test Knight}"
HOST="${4:-127.0.0.1}"
PORT="${5:-7171}"

python3 - "$HOST" "$PORT" "$ACCOUNT" "$PASSWORD" "$CHAR" <<'PY'
import socket, struct, sys, time

host, port, account, password, char_name = sys.argv[1:6]
account = int(account)

def add_string(s):
    b = s.encode('latin-1')
    return struct.pack('<H', len(b)) + b

def make_packet(body):
    return struct.pack('<H', len(body)) + body

def read_packet(sock, timeout=60):
    sock.settimeout(timeout)
    hdr = sock.recv(2)
    if len(hdr) < 2:
        raise RuntimeError('sin respuesta (header vacío)')
    size = hdr[0] | (hdr[1] << 8)
    body = b''
    while len(body) < size:
        chunk = sock.recv(size - len(body))
        if not chunk:
            raise RuntimeError('conexión cerrada antes de completar paquete')
        body += chunk
    return body

# Formato OTClient 7.6: byte 1 + OS u16 = 0x0201 como protId
def account_body():
    body = struct.pack('<B', 1)          # ClientEnterAccount
    body += struct.pack('<H', 2)          # OS (setCustomOs hack)
    body += struct.pack('<H', 760)        # protocol
    body += struct.pack('<III', 0, 0, 0)  # dat/spr/pic (server los ignora)
    body += struct.pack('<I', account)
    body += add_string(password)
    return body

def game_body():
    body = struct.pack('<H', 0x020A)
    body += struct.pack('<B', 2)
    body += struct.pack('<H', 760)
    body += struct.pack('<B', 0)
    body += struct.pack('<I', account)
    body += add_string(char_name)
    body += add_string(password)
    return body

print(f'→ Login cuenta {account} en {host}:{port}')
sock = socket.create_connection((host, int(port)), timeout=10)
t0 = time.time()
sock.sendall(make_packet(account_body()))
resp = read_packet(sock, 30)
print(f'  cuenta OK en {time.time()-t0:.1f}s (opcode 0x{resp[0]:02x}, {len(resp)} bytes)')
if resp[0] == 0x0A:
    slen = resp[1] | (resp[2] << 8)
    print('  error:', resp[3:3+slen].decode('latin-1', 'replace'))
    sys.exit(1)
sock.close()

print(f'→ Login mundo: {char_name}')
sock = socket.create_connection((host, int(port)), timeout=10)
t0 = time.time()
sock.sendall(make_packet(game_body()))
resp = read_packet(sock, 90)
dt = time.time() - t0
print(f'  mundo OK en {dt:.1f}s (opcode 0x{resp[0]:02x}, {len(resp)} bytes)')
if resp[0] == 0x14:
    slen = resp[1] | (resp[2] << 8)
    print('  error:', resp[3:3+slen].decode('latin-1', 'replace'))
    sys.exit(1)
if resp[0] != 0x0A:
    print('  respuesta inesperada')
    sys.exit(1)
print('✓ Login al mundo exitoso')
sock.close()
PY
