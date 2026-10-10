#!/usr/bin/env python3
"""
Alibaba Cloud DNS DDNS Updater
自动检测公网 IP 变化并更新 DNS A 记录
路径: /opt/ddns/update_dns.py
依赖: Python 3 stdlib only (无需 pip install)
"""
import hashlib, hmac, base64, json, os, sys, time, uuid
from datetime import datetime, timezone
from urllib import parse, request

CONFIG_PATH = "/opt/ddns/config.json"
LOG_PATH = "/opt/ddns/ddns.log"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

def load_config():
    if not os.path.exists(CONFIG_PATH):
        log(f"ERROR: 配置文件不存在: {CONFIG_PATH}")
        log("请创建格式: {\"AccessKeyId\":\"...\", \"AccessKeySecret\":\"...\", \"Domain\":\"mc.furina.fun\", \"RR\":\"mc\"}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha1).digest()

def aliyun_api(action, params, key_id, key_secret):
    """调用阿里云 DNS API (Signature V1)"""
    base_params = {
        "Format": "JSON",
        "Version": "2015-01-09",
        "AccessKeyId": key_id,
        "SignatureMethod": "HMAC-SHA1",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "SignatureVersion": "1.0",
        "SignatureNonce": str(uuid.uuid4()),
        "Action": action,
    }
    base_params.update(params)

    # 按 key 排序
    sorted_keys = sorted(base_params.keys())
    # 构造 CanonicalizedQueryString
    qs_parts = []
    for k in sorted_keys:
        v = base_params[k]
        qs_parts.append(f"{parse.quote(k, safe='')}={parse.quote(str(v), safe='')}")
    canonicalized_qs = "&".join(qs_parts)

    # 构造签名字符串
    string_to_sign = "GET&%2F&" + parse.quote(canonicalized_qs, safe="")

    # HMAC-SHA1 签名
    signature = base64.b64encode(sign(f"{key_secret}&".encode("utf-8"), string_to_sign)).decode("utf-8")

    # 构造最终 URL
    url = f"https://alidns.aliyuncs.com/?{canonicalized_qs}&Signature={parse.quote(signature, safe='')}"

    try:
        req = request.Request(url)
        with request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data
    except Exception as e:
        log(f"  API 调用失败: {e}")
        return None

def get_record_id(key_id, key_secret, domain, rr):
    """获取 DNS A 记录的 RecordId"""
    result = aliyun_api("DescribeDomainRecords", {
        "DomainName": domain,
        "RRKeyWord": rr,
        "Type": "A",
    }, key_id, key_secret)
    if result is None:
        return None
    records = result.get("DomainRecords", {}).get("Record", [])
    if not records:
        log(f"  未找到 {rr}.{domain} 的 A 记录")
        return None
    return records[0]["RecordId"]

def update_record(key_id, key_secret, record_id, rr, ip):
    """更新 DNS A 记录"""
    result = aliyun_api("UpdateDomainRecord", {
        "RecordId": record_id,
        "RR": rr,
        "Type": "A",
        "Value": ip,
    }, key_id, key_secret)
    return result

def get_public_ip():
    """获取当前公网 IP"""
    services = [
        "https://ifconfig.me",
        "https://api.ipify.org",
        "https://icanhazip.com",
        "https://checkip.amazonaws.com",
    ]
    for svc in services:
        try:
            req = request.Request(svc, headers={"User-Agent": "curl/7.0"})
            with request.urlopen(req, timeout=10) as resp:
                ip = resp.read().decode("utf-8").strip()
                if ip and "." in ip:
                    return ip
        except:
            continue
    log("ERROR: 所有公网 IP 检测服务均不可用")
    return None

def get_dns_ip(domain, rr):
    """获取当前 DNS 解析的 IP"""
    import socket
    try:
        fqdn = f"{rr}.{domain}" if rr != "@" else domain
        return socket.gethostbyname(fqdn)
    except:
        return None

def main():
    log("=" * 50)
    log("DDNS Updater 启动")
    log("=" * 50)

    config = load_config()
    key_id = config["AccessKeyId"]
    key_secret = config["AccessKeySecret"]
    domain = config.get("Domain", "mc.furina.fun")
    rr = config.get("RR", "mc")  # 主机记录，mc 表示 mc.furina.fun

    # 1. 获取当前公网 IP
    current_ip = get_public_ip()
    if not current_ip:
        log("无法获取公网 IP，退出")
        sys.exit(1)
    log(f"当前公网 IP: {current_ip}")

    # 2. 获取 DNS 当前解析 IP
    dns_ip = get_dns_ip(domain, rr)
    log(f"DNS 解析 IP:  {dns_ip}")

    # 3. 如果相同，不需要更新
    if current_ip == dns_ip:
        log("IP 未变化，无需更新 ✓")
        return

    log(f"IP 已变化: {dns_ip} → {current_ip}，开始更新 DNS...")

    # 4. 获取 RecordId
    record_id = get_record_id(key_id, key_secret, domain, rr)
    if not record_id:
        log("ERROR: 无法获取 DNS 记录 ID")
        sys.exit(1)
    log(f"RecordId: {record_id}")

    # 5. 更新记录
    result = update_record(key_id, key_secret, record_id, rr, current_ip)
    if result is None:
        log("ERROR: DNS 更新失败")
        sys.exit(1)

    if "Code" in result:
        log(f"ERROR: API 返回错误: {result}")
        sys.exit(1)

    log(f"✓ DNS 更新成功: {rr}.{domain} → {current_ip}")

    # 等待 DNS 传播
    log("等待 DNS 生效验证...")
    time.sleep(10)

    new_dns = get_dns_ip(domain, rr)
    if new_dns == current_ip:
        log(f"✓ DNS 已生效: {new_dns}")
    else:
        log(f"DNS 可能还在传播中，当前解析: {new_dns}")


if __name__ == "__main__":
    main()
