# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1 {#alert-1}

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn bình thường để nhận câu trả lời từ LLM
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở dashboard Latency panel, xác nhận P95 > 3000ms và kiểm tra TTFT P95 có tăng không.
  2. **Logs**: Lọc `data/logs.jsonl` trong khoảng thời gian alert, lấy một `correlation_id` có `latency_ms` cao. Kiểm tra `tool_success` và `error_type` xem retrieval có fail không.
  3. **Traces**: Mở Langfuse, tìm trace với `correlation_id` đó. Trong cây trace, so sánh thời gian của `retrieval` span vs `generation` span để xác định bottleneck.
- Mitigation tạm thời:
  - Kiểm tra `incidents.py` - nếu `rag_slow=True`, tắt practice scenario
  - Nếu generation chậm, rollback prompt version về version ổn định
  - Kiểm tra `mock_llm.py` - nếu `cost_spike=True`, tắt incident
- Owner: `student-2A202602608`

## Alert 2 {#alert-2}

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `3m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: tỉ lệ `request_failed` / `request_received`
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` trong 3 phút
- Ảnh hưởng tới người dùng: người dùng nhận error response thay vì câu trả lời, trải nghiệm bị gián đoạn hoàn toàn
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở dashboard Error Rate panel, xác nhận error_rate_pct > 2% và retrieval success rate giảm.
  2. **Logs**: Lọc `data/logs.jsonl` với `event == "request_failed"`, kiểm tra `error_type` và `error_message` phổ biến. Kiểm tra xem có pattern nào không (ví dụ: retrieval timeout).
  3. **Traces**: Mở Langfuse, tìm traces có error. Kiểm tra `retrieval` span có exception không (`Vector store timeout`).
- Mitigation tạm thời:
  - Kiểm tra `incidents.py` - nếu `tool_fail=True`, tắt ngay lập tức
  - Restart API server để reset state
  - Nếu vector store bị timeout, kiểm tra network connectivity và RAG service health
- Owner: `student-2A202602608`

## Alert 3 {#alert-3}

- Tên: `LowQualityScore`
- Severity: `warning`
- Duration: `10m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: trung bình `quality_score` của `response_sent`
- Điều kiện và thời gian duy trì: `avg(quality_score) < 0.75` trong 10 phút
- Ảnh hưởng tới người dùng: câu trả lời từ LLM có chất lượng kém - thiếu context, ngắn quá, hoặc chứa PII bị redact
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở dashboard Quality panel, xác nhận `avg(quality_score) < 0.75`. Kiểm tra retrieval success rate có thấp không.
  2. **Logs**: Lọc `data/logs.jsonl` với `event == "response_sent"`, kiểm tra các request có `quality_score` thấp. Kiểm tra `doc_count` và xem retrieval có trả về empty docs không.
  3. **Traces**: Mở Langfuse, tìm traces với low quality. Kiểm tra `retrieval` span xem có match đúng documents không, và `generation` span xem prompt có đúng không.
- Mitigation tạm thời:
  - Promote lại prompt version ổn định nếu vừa thay đổi
  - Kiểm tra corpus trong `mock_rag.py` - đảm bảo keywords đúng
  - Nếu quality do PII redaction, kiểm tra `pii.py` có hoạt động đúng không
- Owner: `student-2A202602608`
