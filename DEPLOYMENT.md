# DEPLOYMENT — Day 12 (History Tutor Agent)

File này ghi lại cách chạy local + cách deploy (Railway/Render) và URL public sau khi deploy.

---

## Local (Docker Compose)

```powershell
cd .\06-lab-complete
docker compose up -d --build
```

Test:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health"
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/ready"

$apiKey = "dev-key-change-me"
$body = @{ question = "Tóm tắt Cách mạng tháng Tám 1945"; student_id="hs01" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/ask" `
  -Headers @{ "X-API-Key" = $apiKey } `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

---

## Deploy — Railway (CLI)

### Prerequisites
- Node.js (để có `npm`)
- Railway CLI: `npm i -g @railway/cli`

### Steps

```powershell
cd .\06-lab-complete
railway login
railway init

# Required env vars
railway variables set PORT=8000
railway variables set REDIS_URL="<railway-redis-url>"
railway variables set AGENT_API_KEY="<your-secret-api-key>"
railway variables set MONTHLY_BUDGET_USD=10
railway variables set RATE_LIMIT_PER_MINUTE=10

railway up
railway domain
```

### Public URL
- **URL**: `https://<paste-your-domain-here>`

### Smoke test (PowerShell)

```powershell
$base = "https://<paste-your-domain-here>"
$apiKey = "<your-secret-api-key>"

Invoke-RestMethod -Method Get -Uri "$base/health"
Invoke-RestMethod -Method Get -Uri "$base/ready"

$body = @{ question = "Kể ngắn gọn về triều Lý"; student_id="hs01" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$base/ask" `
  -Headers @{ "X-API-Key" = $apiKey } `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

## Platform
- Railway / Render / Cloud Run: **(chọn 1 và ghi vào đây)**

## Environment Variables Set (chụp lại dashboard để điền)
- PORT=8000
- REDIS_URL=...
- AGENT_API_KEY=...
- RATE_LIMIT_PER_MINUTE=10
- MONTHLY_BUDGET_USD=10
- LOG_LEVEL=INFO (nếu bạn set)

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)

---

## Deploy — Render

1) Push repo lên GitHub  
2) Render Dashboard → New → Blueprint  
3) Connect repo → chọn `06-lab-complete/render.yaml`  
4) Set env vars tương tự Railway (`REDIS_URL`, `AGENT_API_KEY`, ...)  
5) Deploy → lấy URL

---

## Notes
- Không commit `.env` / `.env.local`. Chỉ commit `.env.example`.
- Nếu PowerShell hiển thị tiếng Việt lỗi font/encoding:

```powershell
chcp 65001
[Console]::InputEncoding  = [Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
```

