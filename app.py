import os
import psycopg2
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# DB 접속 정보 (Secret에서 환경변수로 주입됨)
DB_CONFIG = {
    "host": "postgres",
    "dbname": os.environ.get("POSTGRES_DB", "certwatch"),
    "user": os.environ.get("POSTGRES_USER", "certwatch"),
    "password": os.environ.get("POSTGRES_PASSWORD", ""),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

# 서버 시작 시 테이블 자동 생성
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS domains (
            id SERIAL PRIMARY KEY,
            domain TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# 상태 확인용
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# 도메인 등록
@app.route("/domains", methods=["POST"])
def add_domain():
    data = request.get_json()
    domain = data.get("domain")
    if not domain:
        return jsonify({"error": "domain is required"}), 400
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO domains (domain) VALUES (%s) RETURNING id", (domain,))
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": new_id, "domain": domain}), 201

# 등록된 도메인 목록
@app.route("/domains", methods=["GET"])
def list_domains():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, domain, expires_at FROM domains ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = [{"id": r[0], "domain": r[1], "expires_at": str(r[2]) if r[2] else None} for r in rows]
    return jsonify(result)

# 웹 화면
HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>CertWatch - SSL 인증서 만료 감시</title>
  <style>
    body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }
    h1 { color: #2c3e50; }
    .form { display: flex; gap: 8px; margin: 20px 0; }
    input { flex: 1; padding: 10px; font-size: 16px; }
    button { padding: 10px 20px; font-size: 16px; cursor: pointer; background: #3498db; color: white; border: none; border-radius: 4px; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background: #f8f9fa; }
    .danger { color: #e74c3c; font-weight: bold; }
    .warn { color: #f39c12; font-weight: bold; }
    .safe { color: #27ae60; }
  </style>
</head>
<body>
  <h1>🔒 CertWatch</h1>
  <p>SSL 인증서 만료일을 감시합니다.</p>
  <div class="form">
    <input id="domain" placeholder="example.com" />
    <button onclick="addDomain()">등록</button>
  </div>
  <table>
    <thead>
      <tr><th>도메인</th><th>만료일</th><th>남은 일수</th></tr>
    </thead>
    <tbody id="list"></tbody>
  </table>
  <script>
    async function load() {
      const res = await fetch('/domains');
      const data = await res.json();
      const tbody = document.getElementById('list');
      tbody.innerHTML = '';
      data.forEach(d => {
        let days = '-', cls = '';
        if (d.expires_at) {
          const diff = Math.floor((new Date(d.expires_at) - new Date()) / 86400000);
          days = diff + '일';
          cls = diff <= 7 ? 'danger' : diff <= 30 ? 'warn' : 'safe';
        }
        tbody.innerHTML += `<tr><td>${d.domain}</td><td>${d.expires_at || '체크 대기중'}</td><td class="${cls}">${days}</td></tr>`;
      });
    }
    async function addDomain() {
      const domain = document.getElementById('domain').value;
      if (!domain) return;
      await fetch('/domains', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({domain})
      });
      document.getElementById('domain').value = '';
      load();
    }
    load();
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
