# AI Vision Service 🔥

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1-6BA539?logo=openapiinitiative&logoColor=white)](./openapi.yaml)
[![License](https://img.shields.io/badge/License-Not%20specified-lightgrey)](#bản-quyền-và-giấy-phép)

AI Vision Service là dịch vụ nhận diện đối tượng dành cho nền tảng Smart Campus. Dịch vụ nhận ảnh từ Camera, chạy YOLO, lưu kết quả vào PostgreSQL và có thể gửi sự kiện nhận diện sang Core Service.

Dự án cung cấp REST API, tài liệu OpenAPI và giao diện web để demo trực tiếp bằng ảnh tải lên.

## Điều kiện tiên quyết

Cách chạy khuyến nghị là Docker:

- Git
- Docker Desktop có Docker Compose
- Kết nối Internet trong lần build và lần đầu tải model `yolov8n.pt`
- Tối thiểu khoảng 4 GB dung lượng trống cho image, dependency và model

Nếu chạy trực tiếp không qua Docker, máy cần thêm:

- Python 3.12 64-bit
- PostgreSQL 16

## Cài đặt

### Chạy bằng Docker

1. Clone dự án:

   ```bash
   git clone https://github.com/duytienkaka/AI-Vision-Service.git
   cd AI-Vision-Service
   ```

2. Tạo file cấu hình môi trường:

   ```powershell
   Copy-Item .env.example .env
   ```

   Trên Linux hoặc macOS:

   ```bash
   cp .env.example .env
   ```

3. Build và khởi động API cùng PostgreSQL:

   ```bash
   docker compose up --build -d
   ```

4. Kiểm tra trạng thái:

   ```bash
   docker compose ps
   curl http://localhost:8000/health
   ```

5. Dừng hệ thống khi không sử dụng:

   ```bash
   docker compose down
   ```

   Thêm `-v` nếu muốn xóa cả dữ liệu PostgreSQL:

   ```bash
   docker compose down -v
   ```

### Chạy trực tiếp bằng Python

1. Tạo virtual environment:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Cài dependency:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements-dev.txt
   ```

3. Tạo `.env` và đổi hostname PostgreSQL từ `db` thành `localhost`:

   ```env
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_vision
   ```

4. Khởi động API:

   ```powershell
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

## Cách sử dụng

Sau khi khởi động, các địa chỉ chính là:

| Chức năng | Địa chỉ |
| --- | --- |
| Kiểm tra service | <http://localhost:8000/health> |
| Swagger UI | <http://localhost:8000/docs> |
| Giao diện demo | <http://localhost:8000/demo> |
| OpenAPI contract | [openapi.yaml](./openapi.yaml) |

### Demo nhận diện ảnh 🖼️

1. Mở <http://localhost:8000/demo>.
2. Chọn một ảnh trong [`demo_assets/images`](./demo_assets/images).
3. Nhấn nút nhận diện.
4. Xem bounding box, nhãn đối tượng, confidence và mức độ rủi ro.

Các kịch bản trình diễn có sẵn tại [demo-scenarios.md](./demo_assets/demo-scenarios.md).

### Camera gửi ảnh sang Vision

Các endpoint tích hợp yêu cầu header:

```text
Authorization: Bearer demo-token
```

Ví dụ gửi ảnh qua `IMAGE_URL`:

```bash
curl -X POST http://localhost:8000/vision/detect \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "REQ-CAM-20260625-0001",
    "cameraId": "CAM-ER-01",
    "capturedAt": "2026-06-25T08:00:00Z",
    "traceId": "TRACE-20260625-0001",
    "zoneId": "ER-ENTRANCE",
    "motionLevel": 0.91,
    "imageSource": {
      "sourceType": "IMAGE_URL",
      "url": "http://host.docker.internal:8000/demo-assets/images/bus.jpg"
    }
  }'
```

Payload mẫu đầy đủ nằm trong [`demo_assets/requests`](./demo_assets/requests).

### Lấy lại kết quả nhận diện

```bash
curl http://localhost:8000/vision/detections/DET-20260625-0001 \
  -H "Authorization: Bearer demo-token"
```

Thay `DET-20260625-0001` bằng `detectionId` trả về từ `POST /vision/detect`.

### Tích hợp Vision với Core

Đặt URL Core trong `.env`:

```env
CORE_SERVICE_URL=http://core-service:8010
```

Sau khi xử lý ảnh, Vision gửi:

```text
POST {CORE_SERVICE_URL}/api/v1/vision-events
```

Payload sử dụng schema `CoreDetectionNotification`, gồm trạng thái nhận diện, camera, người được phát hiện, identity match và danh sách đối tượng. Contract chi tiết được khai báo tại phần `webhooks` trong [openapi.yaml](./openapi.yaml).

Nếu `CORE_SERVICE_URL` để trống, quá trình nhận diện vẫn hoạt động nhưng bước gửi sang Core sẽ được bỏ qua.

### Nhận diện danh tính

Các API hiện có:

- `POST /vision/identify`: đối chiếu người trong ảnh với danh tính đã đăng ký.
- `POST /vision/identities/register`: đăng ký hoặc bổ sung ảnh tham chiếu.
- `GET /vision/identities`: lấy danh sách danh tính.
- `DELETE /vision/identities/{personCode}`: xóa danh tính.

Chi tiết request và response được hiển thị trong Swagger UI.

### Chạy kiểm thử

```bash
docker compose exec api pip install -r requirements-dev.txt
docker compose exec api python -m pytest -q
```

Nếu đang chạy bằng virtual environment:

```powershell
python -m pytest -q
```

### Xem log

```bash
docker compose logs -f api
docker compose logs -f db
```

## Cấu hình

Các biến môi trường quan trọng:

| Biến | Ý nghĩa | Mặc định |
| --- | --- | --- |
| `DATABASE_URL` | Chuỗi kết nối PostgreSQL | PostgreSQL service `db` |
| `CORE_SERVICE_URL` | Base URL của Core Service | Để trống |
| `CORE_SERVICE_TIMEOUT_SECONDS` | Timeout khi gửi sự kiện sang Core | `5.0` |
| `YOLO_MODEL_NAME` | Model Ultralytics YOLO | `yolov8n.pt` |
| `IMAGE_FETCH_TIMEOUT_SECONDS` | Timeout tải ảnh từ URL | `15.0` |
| `MAX_IMAGE_SIZE_BYTES` | Kích thước ảnh tối đa | `5242880` |
| `IDENTITY_MATCH_THRESHOLD` | Ngưỡng khớp danh tính | `0.92` |
| `UPLOADS_DIR` | Nơi lưu ảnh upload demo | `storage/uploads` |
| `OBJECT_STORAGE_ROOT` | Object storage mô phỏng | `storage/object_store` |
| `IDENTITY_GALLERY_DIR` | Nơi lưu ảnh tham chiếu | `storage/identity_gallery` |

Xem toàn bộ cấu hình tại [.env.example](./.env.example).

## Cấu trúc dự án

```text
AI-Vision-Service/
├── app/
│   ├── api/                  # REST API routes
│   ├── core/                 # Cấu hình, auth và logging
│   ├── integrations/         # Tích hợp outbound với Core
│   ├── services/             # YOLO và identity processing
│   ├── web/                  # Giao diện demo
│   └── main.py               # FastAPI entrypoint
├── demo_assets/              # Ảnh, request và kịch bản demo
├── tests/                    # Automated tests
├── openapi.yaml              # Contract Camera, Vision và Core
├── Dockerfile
└── docker-compose.yml
```

## Làm thế nào để đóng góp

1. Fork repository.
2. Tạo branch từ `main`:

   ```bash
   git checkout -b feature/ten-tinh-nang
   ```

3. Cài dependency phát triển và chạy test trước khi sửa.
4. Thực hiện thay đổi nhỏ, rõ mục tiêu và bổ sung test tương ứng.
5. Chạy:

   ```bash
   python -m pytest -q
   ```

6. Commit với nội dung mô tả rõ thay đổi:

   ```bash
   git commit -m "Add: mô tả ngắn tính năng"
   ```

7. Push branch và tạo pull request về `main`.

Không commit `.env`, database, model tải về, cache hoặc dữ liệu trong thư mục `storage/`.

## Tác giả và contributors

- **duytienkaka** — phát triển và duy trì dự án
  GitHub: [@duytienkaka](https://github.com/duytienkaka)


## Nguồn và lời cảm ơn

Dự án sử dụng các công nghệ và tài nguyên mã nguồn mở:

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) cho nhận diện đối tượng.
- [PyTorch](https://pytorch.org/) làm nền tảng suy luận machine learning.
- [FastAPI](https://fastapi.tiangolo.com/) cho REST API.
- [SQLAlchemy](https://www.sqlalchemy.org/) và [PostgreSQL](https://www.postgresql.org/) cho tầng lưu trữ.
- Ảnh demo `bus.jpg` và `zidane.jpg` được phân phối cùng hệ sinh thái ví dụ của Ultralytics.
- Badges được tạo bởi [Shields.io](https://shields.io/).

Việc sử dụng lại các dependency và tài nguyên phải tuân theo giấy phép riêng của từng dự án nguồn.

## Thông tin liên lạc

- GitHub: <https://github.com/duytienkaka>
- Email: <duytienkaka123az@gmail.com>
- Issues: <https://github.com/duytienkaka/AI-Vision-Service/issues>

Vui lòng dùng GitHub Issues cho báo lỗi, đề xuất tính năng hoặc thảo luận kỹ thuật để thông tin có thể được theo dõi công khai.

## Bản quyền và giấy phép

Repository hiện chưa có file `LICENSE`, vì vậy chưa có giấy phép nguồn mở nào được công bố. Theo mặc định, tác giả giữ toàn bộ quyền đối với mã nguồn.

