# MISSION_ANSWERS — Day 12 (AICB-P1 · VinUni 2026)

File này tổng hợp câu trả lời / ghi chú cho các bài trong `CODE_LAB.md`.

> Lưu ý: một số bài yêu cầu “quan sát/so sánh” (phụ thuộc việc bạn chạy thành công trên máy). Hãy bổ sung URL/log/screenshot cho các phần deploy nếu cần.

---

## Part 1 — Localhost vs Production

### Exercise 1.1 — Anti-patterns trong `01-localhost-vs-production/develop/app.py`
- Hardcode API key / DB URL trong code (leak nếu push lên Git).
- Log “secret” ra stdout.
- Debug/reload bật mặc định.
- Port hardcode 8000 (không đọc `PORT` env).
- Bind `host="localhost"` (không chạy được trong container/cloud).
- Thiếu `/health` endpoint.

### Exercise 1.3 — So sánh develop vs production
- **Config**: develop hardcode; production dùng env vars + `.env`.
- **Health**: production có `/health`.
- **Logging**: production structured hơn (tùy file).
- **Shutdown**: production có graceful shutdown (lifespan/signal).

---

## Part 2 — Docker

### Exercise 2.1 — Dockerfile basic (`02-docker/develop/Dockerfile`)
1) **Base image**: `python:3.11`
2) **WORKDIR**: `/app`
3) **Vì sao COPY requirements trước**: tận dụng Docker layer cache, đổi code không phải cài lại deps.
4) **CMD vs ENTRYPOINT**:
   - `CMD`: default command (có thể override khi `docker run ... <cmd>`)
   - `ENTRYPOINT`: “main executable” của container (ít bị override hơn)

### Exercise 2.3 — Multi-stage build (`02-docker/production/Dockerfile`)
- **Stage 1 (builder)**: cài build tools + pip install deps.
- **Stage 2 (runtime)**: copy site-packages cần thiết + code chạy → image nhỏ hơn, sạch hơn.

---

## Part 3 — Cloud Deployment

### Exercise 3.1 — Railway
- Public URL: **(điền URL của bạn ở đây)**
- `PORT`, `REDIS_URL`, `AGENT_API_KEY`, ... đã set: **(ghi lại hoặc dán screenshot link)**

### Exercise 3.2 — Render
- Khác nhau `render.yaml` vs `railway.toml`: đều mô tả build/run + env vars, nhưng cấu trúc & field khác theo platform.

---

## Part 4 — API Security

### Exercise 4.1 — API key auth (develop)
- API key check ở middleware/dependency đọc `X-API-Key`.
- Sai key → `401`.
- Rotate key → đổi env var (không sửa code), redeploy.

---

## Part 5 — Scaling & Reliability

### Exercise 5.3 — Stateless
- Lưu state (session/history) trong Redis thay vì memory.
- Chứng minh: scale nhiều instance vẫn giữ history.

### Exercise 5.4 — Load balancing
- Nginx reverse proxy, upstream trỏ `agent:8000` (round-robin các replica).

### Exercise 5.5 — Test stateless
- Output `python 05-scaling-reliability/production/test_stateless.py`:

```text
============================================================
Stateless Scaling Demo
============================================================

Session ID: f8d81830-078d-4922-b58f-cb3108dd54ad

Request 1: [instance-d801d1]
  Q: What is Docker?
  A: Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!...

Request 2: [instance-892f54]
  Q: Why do we need containers?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....

Request 3: [instance-6d7576]
  Q: What is Kubernetes?
  A: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận....

Request 4: [instance-d801d1]
  Q: How does load balancing work?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....

Request 5: [instance-892f54]
  Q: What is Redis used for?
  A: Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ O...

------------------------------------------------------------
Total requests: 5
Instances used: {'instance-6d7576', 'instance-d801d1', 'instance-892f54'}
✅ All requests served despite different instances!

--- Conversation History ---
Total messages: 10
  [user]: What is Docker?...
  [assistant]: Container là cách đóng gói app để chạy ở mọi nơi. Build once...
  [user]: Why do we need containers?...
  [assistant]: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đ...
  [user]: What is Kubernetes?...
  [assistant]: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã đư...
  [user]: How does load balancing work?...
  [assistant]: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đ...
  [user]: What is Redis used for?...
  [assistant]: Đây là câu trả lời từ AI agent (mock). Trong production, đây...

✅ Session history preserved across all instances via Redis!
```

---

## Part 6 — Final Project (History Tutor)

Project: `06-lab-complete/` — AI tutor lịch sử (mock) + production-ready checklist.

- `/ask`: trả lời lịch sử + lưu conversation history (Redis).
- Auth: `X-API-Key`.
- Rate limit: Redis sliding window.
- Cost guard: budget theo tháng/user (Redis).

