# Hướng dẫn sinh viên chuẩn bị Buổi 6 — Thực hành tích hợp dịch vụ

**Học phần:** FIT4110 — Dịch vụ kết nối và Công nghệ nền tảng  
**Case study:** Smart Campus Operations Platform  
**Nội dung buổi 6:** Các nhóm chạy service của mình và kiểm tra khả năng gọi được service của nhóm khác qua cùng một mạng nội bộ.

> Các nhóm đọc kỹ tài liệu này trước khi đến lớp. Buổi 6 là buổi thực hành tích hợp, thời gian sửa lỗi trên lớp rất ít. Nhóm nào chuẩn bị tốt ở nhà thì đến lớp chỉ cần bật hotspot, lấy IP, cập nhật `.env` và chạy kiểm tra kết nối.

---

## 1. Mục tiêu của Buổi 6

Buổi 6 không tập trung vào slide trình bày. Trọng tâm là kiểm tra xem service của từng nhóm có thật sự chạy được và gọi được service của nhóm khác hay không.

Một nhóm được xem là chuẩn bị tốt khi chứng minh được các điểm sau:

- Service của nhóm chạy ổn định trên một máy demo.
- Endpoint `/health` trả về kết quả thành công.
- Các endpoint chính khớp với OpenAPI đã thống nhất.
- Nhóm khác có thể gọi service của nhóm mình qua IP và port đã công bố.
- Nhóm mình có thể gọi được service của nhóm đối tác.
- Có ảnh chụp, log, kết quả test và request/response mẫu.
- Khi service nhóm khác lỗi hoặc timeout, service của nhóm mình xử lý được, không treo vô hạn.

Nói ngắn gọn: **Buổi 6 kiểm tra khả năng bắt tay thật giữa các service.**

---

## 2. Cần phân biệt rõ hai loại mạng

### 2.1. Mạng Docker trong một máy

Trên máy demo của từng nhóm, các container trong cùng một `docker-compose.yml` gọi nhau bằng tên service.

Ví dụ:

```text
api gọi db bằng db:5432
api gọi ai-service bằng ai-service:9000
api gọi rabbitmq bằng rabbitmq:5672
```

Cách gọi này chỉ có tác dụng **trong cùng một Docker host**, tức là trong cùng một laptop/máy demo.

Nếu `api`, `db`, `ai-service` đều chạy trên cùng một máy bằng Docker Compose, thì dùng tên service là đúng.

### 2.2. Mạng giữa nhiều laptop trong Buổi 6

Trong Buổi 6, mỗi nhóm chạy stack của mình trên một laptop riêng. Khi nhóm A muốn gọi nhóm B, hai nhóm đang ở hai máy khác nhau. Lúc này **không dùng tên service Docker** để gọi sang máy khác.

Cách gọi đúng là:

```text
http://<IP-máy-demo-nhóm-B>:<port>
```

Ví dụ:

```bash
curl http://192.168.43.56:8000/health
```

### 2.3. Lưu ý quan trọng

Docker network như `team-internal` hoặc `class-net` chỉ hoạt động trong phạm vi một Docker host. Nếu các nhóm chạy trên nhiều laptop khác nhau, Docker service name không còn dùng để gọi chéo giữa các nhóm.

Bảng tóm tắt:

| Trường hợp | Cách gọi đúng | Ví dụ |
|---|---|---|
| Container trong cùng một máy | Gọi bằng tên service trong Compose | `http://ai-service:9000` |
| Laptop nhóm A gọi laptop nhóm B | Gọi bằng IP máy demo trên hotspot | `http://192.168.43.56:8000` |

---

## 3. Mô hình mạng dùng trong Buổi 6

Mỗi Product dùng một hotspot riêng. Các nhóm trong cùng Product phải kết nối vào cùng một hotspot.

Ví dụ:

- Product A: 7 máy demo cùng bắt hotspot `productA-net`.
- Product B: 7 máy demo cùng bắt hotspot `productB-net`.

Product A và Product B không cần gọi nhau nên dùng hai hotspot riêng là đúng.

### Lưu ý khi dùng hotspot điện thoại

- Cả 7 máy demo trong cùng Product phải bắt **cùng một hotspot**.
- Nên dùng điện thoại Android làm máy phát vì thường hỗ trợ nhiều thiết bị hơn.
- Điện thoại phát hotspot phải cắm sạc liên tục.
- Trước buổi học cần kiểm tra hotspot có cho đủ số máy kết nối hay không.
- Nếu chỉ gọi IP nội bộ giữa các máy trong cùng hotspot thì gần như không tiêu tốn dữ liệu Internet. Tuy nhiên, một số điện thoại vẫn yêu cầu bật dữ liệu di động để duy trì hotspot, nên cần test trước.

---

## 4. Mỗi nhóm chọn một máy demo

Mỗi nhóm có thể có nhiều laptop, nhưng khi demo chỉ chạy stack trên **một máy duy nhất**.

Lý do: các container của nhóm cần nằm trên cùng một Docker host để gọi nhau bằng Docker service name. Nếu tách `api` ở máy này, `db` ở máy khác thì Compose network không còn đúng.

### Tiêu chí chọn máy demo

| Tiêu chí | Yêu cầu gợi ý | Lý do |
|---|---|---|
| RAM | Tối thiểu 8GB, ưu tiên 16GB | Chạy nhiều container cùng lúc |
| Ổ trống | Tối thiểu 30GB | Chứa image, volume, log |
| Docker | Đã cài và đã test | Không cài mới trên lớp |
| Kết nối hotspot | Bắt hotspot ổn định | Phục vụ gọi chéo giữa các nhóm |
| Pin/sạc | Có sạc đi kèm | Tránh sập máy giữa buổi |
| Repo | Đã clone và chạy thử | Giảm lỗi phát sinh trên lớp |

Nhóm phụ trách xử lý ảnh hoặc service nặng nên ưu tiên máy có cấu hình tốt hơn.

---

## 5. Việc phải làm ở nhà trước Buổi 6

Người giữ máy demo cần chạy thử toàn bộ quy trình trước khi đến lớp.

```bash
git clone <repo-nhom>
cd <repo-nhom>
cp .env.example .env
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health
```

Yêu cầu:

- Các container cần thiết phải chạy được.
- Endpoint `/health` trả về 200 hoặc JSON báo trạng thái thành công.
- Các endpoint chính test được bằng Postman/Newman hoặc `curl`.
- Có ảnh chụp màn hình và log lưu vào thư mục `reports/`.

Nếu ở nhà chưa chạy được thì đến lớp rất khó kịp sửa.

---

## 6. Ba điều bắt buộc để nhóm khác gọi được service của mình

### 6.1. Publish port ra host

Trong `docker-compose.yml`, service nào cần cho nhóm khác gọi thì phải map port ra host.

```yaml
services:
  api:
    ports:
      - "8000:8000"
```

Nếu thiếu phần `ports`, service chỉ chạy bên trong Docker, máy khác sẽ không gọi được.

### 6.2. Service phải bind `0.0.0.0`

Service phải lắng nghe trên mọi network interface, không chỉ trên `127.0.0.1`.

FastAPI/Uvicorn:

```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```

Express/Fastify:

```javascript
app.listen({ port: 8000, host: "0.0.0.0" })
```

Nếu bind `127.0.0.1`, máy khác trong cùng hotspot sẽ không gọi được.

### 6.3. Mở firewall cho port demo

Nếu máy khác gọi bị timeout hoặc connection refused, cần kiểm tra firewall.

Gợi ý:

- Windows: mở Inbound Rule cho TCP port `8000`.
- macOS: cho phép ứng dụng nhận kết nối hoặc tạm tắt firewall trong thời gian demo.
- Linux dùng `ufw`: `sudo ufw allow 8000/tcp`.

---

## 7. Lấy IP máy demo và cập nhật `.env`

### 7.1. Lấy IP máy đang kết nối hotspot

Windows:

```bash
ipconfig
```

Tìm adapter Wi-Fi đang kết nối hotspot, lấy dòng `IPv4 Address`.

macOS:

```bash
ipconfig getifaddr en0
```

Linux:

```bash
hostname -I | awk '{print $1}'
```

Dải IP thường gặp:

```text
Android hotspot: 192.168.43.x
IPhone hotspot: 172.20.10.x
```

### 7.2. Công bố IP cho các nhóm trong cùng Product

Sau khi lấy IP, mỗi nhóm ghi IP của mình vào bảng chung.

Ví dụ:

| Nhóm | Service | IP máy demo | Port | URL |
|---|---|---|---|---|
| team-iot | IoT Ingestion | `192.168.43.__` | 8000 | `http://192.168.43.__:8000` |
| team-camera | Camera Stream | `192.168.43.__` | 8000 | `http://192.168.43.__:8000` |
| team-gate | Access Gate | `192.168.43.__` | 8000 | `http://192.168.43.__:8000` |
| team-vision | Vision Service | `192.168.43.__` | 8000 | `http://192.168.43.__:8000` |
| team-analytics | Analytics | `192.168.43.__` | 8000 | `http://192.168.43.__:8000` |
| team-core | Core Business | `192.168.43.__` | 8000 | `http://192.168.43.__:8000` |
| team-notify | Notification | `192.168.43.__` | 8000 | `http://192.168.43.__:8000` |

Làm một bảng riêng cho từng Product.

### 7.3. Cập nhật `.env` khi gọi nhóm khác

Không hard-code IP trong source code. Đưa URL nhóm đối tác vào `.env`.

Ví dụ:

```bash
CORE_SERVICE_URL=http://192.168.43.56:8000
NOTIFICATION_URL=http://192.168.43.57:8000
VISION_SERVICE_URL=http://192.168.43.54:8000
```

Trong code, đọc từ biến môi trường:

```python
import os
CORE_URL = os.getenv("CORE_SERVICE_URL")
```

Không viết cứng IP trong code:

```python
# Không làm như sau
CORE_URL = "http://192.168.43.56:8000"
```

Lưu ý: IP có thể thay đổi mỗi lần bật lại hotspot. Vì vậy đầu Buổi 6 cần lấy IP lại và cập nhật `.env`.

---

## 8. Quy ước URL và endpoint bắt buộc

Mỗi nhóm expose API chính ra port `8000`, trừ khi giảng viên cho phép dùng port khác.

URL để nhóm khác gọi:

```text
http://<IP-máy-demo>:8000
```

Endpoint bắt buộc:

```text
GET /health
```

Endpoint tích hợp chính do từng cặp nhóm thống nhất theo OpenAPI đã chốt từ trước.

---

## 9. Endpoint mẫu theo các cặp tích hợp

Bảng dưới đây là gợi ý để các nhóm thống nhất nhanh. Nếu OpenAPI của nhóm đã có endpoint khác thì dùng theo file đã chốt, nhưng phải ghi rõ trong phiếu hẹn tích hợp.

| Luồng | Consumer | Provider | Endpoint gợi ý | Ý nghĩa |
|---|---|---|---|---|
| IoT → Core | team-iot | team-core | `POST /api/v1/sensor-events` | Gửi dữ liệu cảm biến sang Core |
| Camera → Vision | team-camera | team-vision | `POST /api/v1/detect` | Gửi frame hoặc ảnh sang service xử lý hình ảnh |
| Vision → Core | team-vision | team-core | `POST /api/v1/detections` | Gửi kết quả phát hiện sang Core |
| Gate → Core | team-gate | team-core | `POST /api/v1/access-events` | Gửi sự kiện quẹt thẻ hoặc ra/vào |
| Core → Notify | team-core | team-notify | `POST /api/v1/notifications` | Gửi thông báo cần phát đi |
| Core → Analytics | team-core | team-analytics | `POST /api/v1/events` | Gửi event để thống kê |
| IoT → Analytics | team-iot | team-analytics | `POST /api/v1/metrics/raw` | Gửi dữ liệu thô phục vụ tổng hợp |

Mỗi cặp cần thống nhất tối thiểu:

- URL đầy đủ.
- Method và path.
- Request mẫu.
- Response mong đợi.
- Cách xử lý khi provider lỗi.

---

## 10. Test kết nối giữa hai nhóm

Trước khi demo, từng cặp nhóm phải test thông mạng.

Từ máy nhóm A, gọi sang máy nhóm B:

```bash
curl http://192.168.43.56:8000/health
```

Nếu trả 200 hoặc JSON trạng thái thành công, kết nối mạng cơ bản đã ổn.

Nếu lỗi, xử lý theo bảng sau:

| Lỗi | Nguyên nhân thường gặp | Cách kiểm tra |
|---|---|---|
| Connection refused | Service chưa chạy, chưa publish port, bind sai | Kiểm tra `docker compose ps`, `ports`, `0.0.0.0` |
| Timeout | Sai IP, khác hotspot, firewall chặn | Kiểm tra IP, hotspot, firewall |
| 404 | Gọi sai path | Kiểm tra lại endpoint |
| 500 | Service lỗi bên trong | Xem `docker compose logs` |
| Không phân giải hostname | Dùng nhầm service name Docker để gọi máy khác | Đổi sang IP hotspot |

---

## 11. Phiếu hẹn tích hợp trước Buổi 6

Các nhóm không đợi đến lớp mới bàn endpoint. Mỗi cặp cần thống nhất trước qua Teams hoặc nhóm chat.

```text
PHIẾU HẸN TÍCH HỢP — BUỔI 6

Nhóm gọi (consumer): __________________________
Nhóm được gọi (provider): ______________________

URL provider:
http://_________________________________________

Endpoint sẽ gọi:
METHOD: ________
PATH:   _______________________________________

Request mẫu:
{
  _____________________________________________
}

Response mong đợi:
{
  _____________________________________________
}

Nếu provider lỗi hoặc timeout, nhóm consumer sẽ xử lý như sau:
________________________________________________

Đã test /health qua hotspot: [ ] Rồi   [ ] Chưa
```

---

## 12. Xử lý khi service nhóm khác lỗi

Trong demo, service nhóm khác có thể chưa chạy, sai endpoint hoặc timeout. Nhóm consumer không được để request treo vô hạn.

Cần chuẩn bị:

- Timeout hợp lý, khoảng 3–5 giây.
- Thông báo lỗi rõ ràng.
- Trả mã lỗi phù hợp, ví dụ 503 khi service phụ thuộc không sẵn sàng.
- Có thể retry nhẹ 1–2 lần nếu cần.
- Ghi log để biết lỗi xảy ra ở đâu.

Ví dụ Python:

```python
import httpx

try:
    response = httpx.post(
        CORE_URL + "/api/v1/detections",
        json=payload,
        timeout=5.0,
    )
    response.raise_for_status()
except httpx.TimeoutException:
    return {"error": "service phụ thuộc timeout", "status": 503}
except httpx.HTTPStatusError as e:
    return {"error": "service phụ thuộc trả lỗi", "status": e.response.status_code}
except httpx.RequestError:
    return {"error": "không kết nối được service phụ thuộc", "status": 503}
```

---

## 13. Timeline đầu Buổi 6

| Thời gian | Việc cần làm |
|---|---|
| 0–10 phút | Bật hotspot của từng Product, các máy demo kết nối vào đúng hotspot |
| 10–20 phút | Mỗi nhóm lấy IP máy demo và điền vào bảng IP chung |
| 20–30 phút | Cập nhật `.env` với URL nhóm đối tác |
| 30–40 phút | Chạy `git pull`, `docker compose up -d --build`, kiểm tra `docker compose ps` |
| 40–50 phút | Test `/health` nội bộ và test `/health` của nhóm đối tác |
| 50–60 phút | Chốt nhóm nào đã sẵn sàng, nhóm nào còn lỗi mạng/firewall |
| Sau 60 phút | Bắt đầu demo và kiểm tra tích hợp theo cặp |

Nhóm nào chưa chạy thử ở nhà sẽ rất khó kịp trong 60 phút đầu.

---

## 14. Phương án dự phòng nếu hotspot lỗi

Nếu hotspot không đủ thiết bị hoặc các máy không nhìn thấy nhau, xử lý theo thứ tự:

1. Chuyển sang điện thoại Android khác có giới hạn thiết bị cao hơn.
2. Giảm số thiết bị kết nối không cần thiết, chỉ giữ lại các máy demo.
3. Dùng router Wi-Fi mini hoặc thiết bị phát Wi-Fi riêng nếu có.
4. Gộp tạm một số service mock trên cùng một máy để demo luồng chính.
5. Nếu vẫn lỗi, nhóm phải ghi lại minh chứng lỗi: IP, hotspot đang dùng, lệnh `curl`, firewall, `docker compose ps`, log service.

Không chuyển sang Wi-Fi công cộng nếu mạng đó có chế độ cách ly thiết bị, vì các máy có thể không gọi được nhau.

---

## 15. Checklist trước khi demo

Mỗi nhóm tự kiểm tra trước khi báo đã sẵn sàng.

- [ ] Máy demo đã kết nối đúng hotspot của Product.
- [ ] Đã lấy IP máy demo và công bố cho Product.
- [ ] Đã cập nhật `.env` với URL nhóm đối tác.
- [ ] `docker compose ps` hiển thị các container cần thiết đang chạy.
- [ ] `GET /health` của nhóm mình trả thành công.
- [ ] Nhóm khác gọi được `GET /health` của nhóm mình.
- [ ] Mình gọi được `GET /health` của nhóm đối tác.
- [ ] Endpoint tích hợp chính đã test bằng request mẫu.
- [ ] Có log, screenshot, request/response mẫu.
- [ ] Có phương án xử lý timeout hoặc service phụ thuộc lỗi.

---

## 16. Minh chứng cần nộp

Mỗi nhóm cần lưu vào thư mục `reports/` hoặc thư mục minh chứng tương đương:

```text
reports/
├── docker-compose-ps.png
├── health-local.png
├── health-partner.png
├── integration-request-response.png
├── logs-compose.txt
├── newman-report.html hoặc newman-report.xml
└── readiness-checklist.md
```

Nếu dùng video ngắn, đặt tên rõ:

```text
reports/demo-integration-team-iot-to-team-core.mp4
```

---

## 17. Rubric gợi ý Buổi 6

| Tiêu chí | Điểm |
|---|---:|
| Service chạy ổn định trên máy demo, `/health` thành công | 2.0 |
| Nhóm khác gọi được service qua hotspot/IP | 2.0 |
| Endpoint tích hợp đúng OpenAPI đã chốt | 1.5 |
| Có xử lý timeout hoặc lỗi từ service phụ thuộc | 1.5 |
| Có minh chứng: log, ảnh, Newman report, request/response | 1.5 |
| Trình bày demo rõ ràng, đúng luồng tích hợp | 1.5 |
| **Tổng** | **10.0** |

Điểm nhấn của Buổi 6 là khả năng tích hợp thật, không phải trình bày slide dài.

---

## 18. Quy trình tóm tắt đầu Buổi 6

1. Bật hotspot của từng Product.
2. Tất cả máy demo kết nối vào đúng hotspot.
3. Mỗi nhóm lấy IP máy demo.
4. Ghi IP vào bảng chung.
5. Cập nhật `.env` với IP nhóm đối tác.
6. Chạy `docker compose up -d --build`.
7. Kiểm tra `/health` của nhóm mình.
8. Test `/health` của nhóm đối tác.
9. Chạy request tích hợp mẫu.
10. Lưu minh chứng và sẵn sàng demo.

---

## 19. Nhắc cuối

Buổi 6 không phải buổi để bắt đầu cài Docker, sửa lại toàn bộ repo hoặc thiết kế lại API.

Trước khi đến lớp, mỗi nhóm cần chắc chắn:

- Repo chạy được trên máy demo.
- File `.env.example` rõ ràng.
- Docker Compose chạy được.
- Endpoint `/health` hoạt động.
- Đã biết nhóm mình gọi ai và ai gọi nhóm mình.
- Đã có request mẫu để test nhanh.

Khi lên lớp, nhóm chỉ cần kết nối hotspot, lấy IP, cập nhật `.env`, chạy stack và kiểm tra tích hợp.

