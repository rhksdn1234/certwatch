import os
import json
import urllib.request
from datetime import datetime
import psycopg2

DB_CONFIG = {
    "host": "postgres",
    "dbname": os.environ.get("POSTGRES_DB", "certwatch"),
    "user": os.environ.get("POSTGRES_USER", "certwatch"),
    "password": os.environ.get("POSTGRES_PASSWORD", ""),
}

# 며칠 이하로 남으면 경고할지 (기준값)
WARN_DAYS = int(os.environ.get("WARN_DAYS", "30"))

SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "")

def send_slack(message):
    """슬랙으로 메시지 발송"""
    if not SLACK_WEBHOOK:
        print("(슬랙 URL 미설정 - 발송 생략)")
        return
    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK, data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print("(슬랙 발송 완료)")
    except Exception as e:
        print(f"(슬랙 발송 실패: {e})")

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    # 만료일이 채워진 도메인만 가져옴
    cur.execute("SELECT domain, expires_at FROM domains WHERE expires_at IS NOT NULL")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    alerts = []
    for domain, expires_at in rows:
        days_left = (expires_at - datetime.now()).days
        if days_left <= WARN_DAYS:
            alerts.append((domain, days_left))

    if not alerts:
        print(f"[안전] {WARN_DAYS}일 이내 만료되는 도메인 없음")
        return

    print(f"=== ⚠️ 만료 임박 경고 ({WARN_DAYS}일 이내) ===")
    for domain, days_left in alerts:
        msg = f"⚠️ [CertWatch 경고] {domain}: SSL 인증서가 {days_left}일 후 만료됩니다!"
        print(msg)
        send_slack(msg)
        
        # 2단계에서 여기에 슬랙/메일 발송 코드가 들어감
        # send_to_slack(msg)

    print(f"총 {len(alerts)}개 도메인 경고")

if __name__ == "__main__":
    main()
