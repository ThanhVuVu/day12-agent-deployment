# Lab 12 — Complete Production Agent (History Tutor)

Kết hợp TẤT CẢ những gì đã học trong 1 project hoàn chỉnh.

## Checklist Deliverable

- [x] Dockerfile (multi-stage, < 500 MB)
- [x] docker-compose.yml (agent + redis)
- [x] .dockerignore
- [x] Health check endpoint (`GET /health`)
- [x] Readiness endpoint (`GET /ready`)
- [x] API Key authentication
- [x] Rate limiting
- [x] Cost guard
- [x] Config từ environment variables
- [x] Structured logging
- [x] Graceful shutdown
- [x] Public URL ready (Railway / Render config)

---

## Cấu Trúc

```
06-lab-complete/
├── app/
│   ├── main.py         # Entry point — kết hợp tất cả
│   ├── config.py       # 12-factor config
│   ├── auth.py         # API Key + JWT
│   ├── rate_limiter.py # Rate limiting
│   └── cost_guard.py   # Budget protection
├── Dockerfile          # Multi-stage, production-ready
├── docker-compose.yml  # Full stack
├── railway.toml        # Deploy Railway
├── render.yaml         # Deploy Render
├── .env.example        # Template
├── .dockerignore
└── requirements.txt
```

---

## Chạy Local (PowerShell-friendly)

```powershell
# 1) Start full stack (agent + redis)
docker compose up -d --build

# 2) Health / readiness
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health"
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/ready"

# 3) Ask history tutor (requires API key)
$apiKey = "dev-key-change-me"
$body = @{ question = "Tóm tắt Cách mạng tháng Tám 1945"; student_id = "hs01" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/ask" `
  -Headers @{ "X-API-Key" = $apiKey } `
  -ContentType "application/json; charset=utf-8" `
  -Body $body

# 4) View stored conversation history (Redis-backed)
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/me/history" `
  -Headers @{ "X-API-Key" = $apiKey }
```

---

## Deploy Railway (< 5 phút)

```bash
# Cài Railway CLI
npm i -g @railway/cli

# Login và deploy
railway login
railway init
railway variables set OPENAI_API_KEY=<your-openai-key>
railway variables set AGENT_API_KEY=your-secret-key
railway up

# Nhận public URL!
railway domain
```

---

## Deploy Render

1. Push repo lên GitHub
2. Render Dashboard → New → Blueprint
3. Connect repo → Render đọc `render.yaml`
4. Set secrets: `OPENAI_API_KEY`, `AGENT_API_KEY`
5. Deploy → Nhận URL!

---

## Kiểm Tra Production Readiness

```bash
python check_production_ready.py
```

Script này kiểm tra tất cả items trong checklist và báo cáo những gì còn thiếu.

## Theme: History Tutor
- Endpoint `POST /ask` trả lời theo phong cách gia sư lịch sử (mock).
- Lưu **conversation history** theo `student_id` (hoặc theo API key) trong Redis để đảm bảo **stateless** khi scale.
