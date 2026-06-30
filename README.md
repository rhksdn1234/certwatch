# CertWatch
 
쿠버네티스 기반 SSL 인증서 만료 감시 서비스. 등록한 도메인의 SSL 인증서 만료일을 주기적으로 체크하고, 만료가 임박하면 슬랙으로 알림을 보낸다.
 
SSL 인증서 만료를 깜빡해서 사이트가 "보안 경고"로 마비되는 사고를 미리 막기 위한 도구다. 직접 구축한(kubeadm) 멀티노드 클러스터 위에 DB·API·배치·알림을 모두 올린 풀스택 프로젝트다.
 
## 기능
 
- 웹 화면에서 도메인 등록 / 목록 조회 (남은 일수를 색상으로 표시)
- CronJob이 주기적으로 각 도메인의 실제 SSL 인증서를 읽어 만료일 갱신
- 만료 임박(기본 30일 이내) 도메인을 슬랙으로 자동 알림
- 데이터는 PVC(영구 볼륨)에 저장되어 Pod 재시작에도 유지
## 아키텍처
 
```
[사용자] → 웹 화면(Frontend) → API 서버(Flask) → DB(PostgreSQL + PVC)
                                                      ↑
                              CronJob(SSL 체커) ──────┘ 만료일 갱신
                                     │
                              Notifier(슬랙 알림) ── 만료 임박 시 발송
```
 
| 구성요소 | 역할 | 쿠버네티스 리소스 |
|---------|------|-----------------|
| Frontend | 도메인 등록 / 목록 UI | (API 서버가 함께 서빙) |
| API 서버 | 등록·조회 처리 | Deployment + Service |
| DB | 도메인·만료일 저장 | Deployment + PVC + Service |
| SSL 체커 | 만료일 주기적 갱신 | CronJob |
| Notifier | 만료 임박 슬랙 알림 | CronJob |
| 민감정보 | DB 비번 / 슬랙 URL | Secret |
 
## 기술 스택
 
- 오케스트레이션: Kubernetes (kubeadm, 3-node)
- 백엔드: Python (Flask)
- DB: PostgreSQL 16 (PVC 영구 저장)
- 알림: Slack Incoming Webhook
- 저장소: local-path-provisioner (StorageClass)
## 사전 준비
 
1. 쿠버네티스 클러스터와 기본 StorageClass
```bash
   # local-path-provisioner 설치 (기본 StorageClass 없을 때)
   kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.30/deploy/local-path-storage.yaml
   kubectl patch storageclass local-path -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```
 
2. 슬랙 Incoming Webhook URL (알림용, 선택)
   - https://api.slack.com/apps → Create New App → Incoming Webhooks 활성화 → Webhook URL 발급
## 배포
 
```bash
# 환경변수로 비밀번호와 슬랙 URL 전달 (Secret으로 저장됨)
DB_PASSWORD='your-strong-password' \
SLACK_WEBHOOK='https://hooks.slack.com/services/...' \
./setup.sh
```
 
`setup.sh`가 Secret → ConfigMap → DB → API → CronJob 순으로 배포한다.
 
배포 후 접속 포트 확인:
 
```bash
kubectl get svc api    # PORT(S)의 5000:3xxxx 에서 3xxxx 가 접속 포트
```
 
브라우저에서 `http://<노드IP>:<3xxxx>` 로 접속.
 
## 사용법
 
1. 웹 화면에서 도메인 등록 (예: `google.com`)
2. SSL 체크 수동 실행 (또는 매시간 자동):
```bash
   kubectl create job --from=cronjob/ssl-checker manual-check-1
```
 
3. 화면 새로고침 → 만료일과 남은 일수 확인
4. 만료 임박 도메인은 슬랙으로 알림 발송 (매시 30분 자동, 또는 수동 실행)
## 보안
 
- DB 비밀번호와 슬랙 Webhook URL은 **Secret**으로 관리하며 저장소에 커밋하지 않는다 (`.gitignore`로 차단).
- Webhook URL이 노출되면 누구나 해당 슬랙 채널로 메시지를 보낼 수 있으므로 주의.
## 트러블슈팅 메모
 
실제 구축 중 만난 문제와 해결법.
 
| 증상 | 원인 | 해결 |
|------|------|------|
| API Pod가 `Error`/재시작 반복, 로그에 `could not translate host name "postgres"` | postgres용 Service 미생성 | `postgres-svc.yaml` 적용 (Service 이름이 곧 DNS 주소) |
| 코드 수정했는데 웹 화면에 반영 안 됨 | ConfigMap 갱신 후 Pod 재시작 안 함 | ConfigMap 갱신은 기존 Pod에 자동 반영되지 않음. `kubectl rollout restart deployment <name>` 필요 |
| ConfigMap 갱신이 일부만 반영됨 | `--dry-run \| apply` 방식의 캐시/부분갱신 | `kubectl delete configmap` 후 `create`로 확실히 재생성 |
| PVC가 계속 `Pending` | StorageClass의 `WaitForFirstConsumer` | 정상. Pod가 PVC를 사용할 때 PV가 생성되며 `Bound`로 전환됨 |
 
## 향후 계획
 
- 개인 클라우드(EKS/GKE)로 이전 + 도메인/HTTPS 적용해 외부 서비스화
- 무료/유료 플랜 분리 (도메인 개수 제한, 알림 채널 다양화)
- Prometheus/Grafana로 서비스 자체 모니터링 연동
