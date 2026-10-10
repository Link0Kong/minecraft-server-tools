import socket, json, struct

HOST = "mc.furina.fun"
PORT = 25565

def write_varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)

def read_varint(sock):
    num = 0
    shift = 0
    while True:
        b = sock.recv(1)
        if not b:
            raise ConnectionError("closed")
        b = b[0]
        num |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
        if shift > 35:
            raise ValueError("varint too big")
    return num

def pack_string(s):
    b = s.encode("utf-8")
    return write_varint(len(b)) + b

def main():
    try:
        s = socket.create_connection((HOST, PORT), timeout=8)
    except Exception as e:
        print("CONNECT_FAIL:", e)
        return

    # Handshake: packet_id=0, protocol=-1 (0xFFFFFFFF), host, port, next_state=1
    body = write_varint(0) + write_varint(0xFFFFFFFF) + pack_string(HOST) + struct.pack(">H", PORT) + write_varint(1)
    s.sendall(write_varint(len(body)) + body)

    # Status request: packet_id=0
    req = write_varint(0)
    s.sendall(write_varint(len(req)) + req)

    total_len = read_varint(s)
    packet_id = read_varint(s)
    json_len = read_varint(s)
    data = b""
    while len(data) < json_len:
        chunk = s.recv(json_len - len(data))
        if not chunk:
            break
        data += chunk
    s.close()

    info = json.loads(data.decode("utf-8", "replace"))
    desc = info.get("description", {})
    if isinstance(desc, dict):
        motd = desc.get("text", "") or "".join(x.get("text", "") for x in desc.get("extra", []))
    else:
        motd = str(desc)
    players = info.get("players", {})
    print("STATUS: ONLINE")
    print("version:", info.get("version", {}).get("name"))
    print("protocol:", info.get("version", {}).get("protocol"))
    print("motd:", motd)
    print("online_players:", players.get("online"))
    print("max_players:", players.get("max"))
    sample = players.get("sample", [])
    if sample:
        print("players_list:", [p.get("name") for p in sample])

if __name__ == "__main__":
    main()
