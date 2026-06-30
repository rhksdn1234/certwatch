import os
import ssl
import socket
from datetime import datetime
import psycopg2

DB_CONFIG = {
    "host": "postgres",
    "dbname": os.environ.get("POSTGRES_DB", "certwatch"),
    "user": os.environ.get("POSTGRES_USER", "certwatch"),
    "password": os.environ.get("POSTGRES_PASSWORD", ""),
}

def get_ssl_expiry(domain):
    """도메인의 SSL 인증서 만료일을 가져온다"""
    ctx = ssl.create_default_context()
    with socket.create_connection((domain, 443), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
            cert = ssock.getpeercert()
            expire_str = cert["notAfter"]
            return datetime.strptime(expire_str, "%b %d %H:%M:%S %Y %Z")

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT id, domain FROM domains")
    domains = cur.fetchall()

    for domain_id, domain in domains:
        try:
            expiry = get_ssl_expiry(domain)
            days_left = (expiry - datetime.now()).days
            cur.execute(
                "UPDATE domains SET expires_at = %s, last_checked = NOW() WHERE id = %s",
                (expiry, domain_id),
            )
            print(f"[OK] {domain}: 만료 {expiry.date()} ({days_left}일 남음)")
        except Exception as e:
            print(f"[FAIL] {domain}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print("체크 완료")

if __name__ == "__main__":
    main()

