# AI Vision Service

AI Vision Service là service nhận diện đối tượng cho nền tảng Smart Campus. Service này nhận đầu vào ảnh từ nhóm Camera, chạy YOLO để suy luận, lưu kết quả vào PostgreSQL, và có thể gửi tiếp dữ liệu đã xử lý sang service Core nếu được cấu hình.

## Service Này Dùng Để Làm Gì

- Nhận yêu cầu nhận diện từ service Camera
- Lấy ảnh từ `IMAGE_URL` và chạy phát hiện đối tượng
- Lưu metadata và danh sách đối tượng phát hiện được vào PostgreSQL
- Cung cấp API để nhóm Camera và Core lấy kết quả
- Cung cấp giao diện demo để thuyết trình và kiểm thử nhanh

## Công Nghệ Sử Dụng

- `FastAPI`
- `PostgreSQL`
- `SQLAlchemy`
- `Ultralytics YOLO`
- `Docker Compose`

## Luồng Tích Hợp Chính

### Camera -> Vision

1. Nhóm Camera gọi `POST /vision/detect`
2. Camera gửi metadata và nguồn ảnh
3. Vision lấy ảnh từ `IMAGE_URL`
4. Vision chạy YOLO để phát hiện đối tượng
5. Vision lưu kết quả vào PostgreSQL
6. Vision trả về `detectionId`
7. Camera hoặc Core có thể gọi `GET /vision/detections/{detectionId}` để lấy lại kết quả

### Vision -> Core

Nếu có cấu hình `CORE_SERVICE_URL`, Vision sẽ gửi kết quả đã xử lý tới:

```text
POST <CORE_SERVICE_URL>/api/v1/detections
```

Trong môi trường Docker Compose của dự án này, đã có sẵn `mock-core` để mô phỏng service Core, giúp demo được luôn luồng Vision gọi sang Core ngay cả khi nhóm Core chưa kết nối trực tiếp.

### Luồng Demo

1. Mở `http://localhost:8000/demo`
2. Tải ảnh trực tiếp từ máy lên
3. Vision chạy YOLO để nhận diện
4. Giao diện sẽ hiển thị:
   - ảnh xem trước
   - bounding box
   - danh sách đối tượng
   - hiệu ứng highlight từng đối tượng khi rê chuột
   - summary, confidence và alert hint

### Nguồn Ảnh Được Hỗ Trợ

Service hiện hỗ trợ 2 cách đưa ảnh vào API chính:

- `IMAGE_URL`: nhóm Camera truyền vào một URL ảnh mà máy chạy Vision truy cập được
- `OBJECT_STORAGE_REF`: nhóm Camera truyền `bucket`, `objectKey`, `expiresAt`; Vision sẽ đọc ảnh từ thư mục object storage đã cấu hình

API upload ảnh trực tiếp chỉ dùng cho demo giao diện web, không phải contract chính giữa các nhóm.

## Danh Sách API Hiện Có

### `GET /health`

API kiểm tra trạng thái service.

- Xác thực: không cần
- Mục đích: kiểm tra service còn hoạt động hay không

Ví dụ response:

```json
{
  "status": "ok",
  "service": "ai-vision",
  "time": "2026-06-16T14:19:51.893140Z"
}
```

### `POST /vision/detect`

API chính để nhóm Camera tích hợp.

- Xác thực: bắt buộc
- Header: `Authorization: Bearer <token>`
- Content-Type: `application/json`
- Kiểu nguồn ảnh khuyến nghị: `IMAGE_URL`
- Ngoài ra cũng hỗ trợ `OBJECT_STORAGE_REF`

Ví dụ request:

```json
{
  "requestId": "REQ-CAM-20260616-9101",
  "cameraId": "CAM-ER-01",
  "capturedAt": "2026-06-16T14:20:00Z",
  "traceId": "TRACE-20260616-9101",
  "zoneId": "ER-ENTRANCE",
  "motionLevel": 0.91,
  "notes": "Camera integration request",
  "imageSource": {
    "sourceType": "IMAGE_URL",
    "url": "http://<CAMERA-HOST>:8000/images/zidane.jpg"
  }
}
```

Ví dụ response:

```json
{
  "detectionId": "DET-20260616-2697",
  "requestId": "REQ-CAM-20260616-9101",
  "traceId": "TRACE-20260616-9101",
  "status": "PROCESSING",
  "acceptedAt": "2026-06-16T14:20:09.244167Z",
  "preliminaryResult": {
    "status": "COMPLETED",
    "confidence": 0.8055675029754639,
    "riskLevel": "HIGH",
    "modelVersion": "yolov8n.pt",
    "summary": "Detected 3 object(s); top labels: person, person, tie",
    "alertHint": "REVIEW_SECURITY",
    "completedAt": "2026-06-16T14:20:09.318032Z",
    "thumbnailUrl": "http://<CAMERA-HOST>:8000/images/zidane.jpg",
    "objects": [
      {
        "objectType": "PERSON",
        "label": "person",
        "confidence": 0.8055675029754639,
        "trackId": "TRACK-1",
        "boundingBox": {
          "x": 0.0964,
          "y": 0.2739,
          "width": 0.7712,
          "height": 0.713
        }
      }
    ]
  }
}
```

Lưu ý:

- Đây là contract chính khuyến nghị cho nhóm Camera.
- `requestId` phải là duy nhất. Nếu gửi trùng sẽ nhận `409 Conflict`.
- `OBJECT_STORAGE_REF` đã được hỗ trợ cho luồng object storage nội bộ.

### `GET /vision/detections/{detectionId}`

API lấy lại kết quả nhận diện đã được lưu.

- Xác thực: bắt buộc
- Header: `Authorization: Bearer <token>`

Ví dụ response:

```json
{
  "detectionId": "DET-20260616-2697",
  "requestId": "REQ-CAM-20260616-9101",
  "traceId": "TRACE-20260616-9101",
  "status": "COMPLETED",
  "confidence": 0.8055675029754639,
  "riskLevel": "HIGH",
  "modelVersion": "yolov8n.pt",
  "summary": "Detected 3 object(s); top labels: person, person, tie",
  "alertHint": "REVIEW_SECURITY",
  "processedAt": "2026-06-16T14:20:09.318032Z",
  "completedAt": "2026-06-16T14:20:09.318032Z",
  "thumbnailUrl": "http://<CAMERA-HOST>:8000/images/zidane.jpg",
  "objects": [
    {
      "objectType": "PERSON",
      "label": "person",
      "confidence": 0.8055675029754639,
      "trackId": "TRACK-1",
      "boundingBox": {
        "x": 0.0964,
        "y": 0.2739,
        "width": 0.7712,
        "height": 0.713
      }
    }
  ],
  "errorDetail": null
}
```

### `GET /vision/models/info`

API trả về thông tin model đang dùng.

- Xác thực: bắt buộc
- Header: `Authorization: Bearer <token>`

Thông tin trả về gồm:

- phiên bản model YOLO đang chạy
- các loại đối tượng được hỗ trợ
- các loại nguồn ảnh được hỗ trợ
- kích thước ảnh tối đa

### `POST /demo/api/detect`

API chỉ dùng cho phần demo giao diện web.

- Xác thực: không cần
- Content-Type: `multipart/form-data`

Các field chính:

- `image`
- `cameraId`
- `zoneId`
- `motionLevel`
- `notes`

Kết quả trả về:

- `detectionId`
- `requestId`
- `traceId`
- `imageUrl`
- `result`

### `GET /demo`

Giao diện demo để test thủ công và trình bày.

- Xác thực: không cần

### `GET /demo-assets/...`

API phục vụ ảnh và dữ liệu demo tĩnh.

- Xác thực: không cần

API này hữu ích để mô phỏng `IMAGE_URL` khi test tích hợp Camera -> Vision.

## Cơ Chế Xác Thực

Các API cần Bearer token hiện tại gồm:

- `POST /vision/detect`
- `GET /vision/detections/{detectionId}`
- `GET /vision/models/info`

Ví dụ header:

```text
Authorization: Bearer demo-token
```

## Cách Chạy Service

### Chạy Bằng Docker

1. Sao chép `.env.example` thành `.env`
2. Khởi động toàn bộ stack:

```bash
docker compose up --build
```

Sau đó mở:

- API root: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Demo UI: `http://localhost:8000/demo`
- Demo assets: `http://localhost:8000/demo-assets/`
- Mock Core health: `http://localhost:8010/health`
- Mock Core latest detection: `http://localhost:8010/api/v1/detections/latest`

### Chạy Local Với Python

```bash
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Biến Môi Trường

Các biến chính trong `.env`:

- `DATABASE_URL`: chuỗi kết nối PostgreSQL
- `CORE_SERVICE_URL`: địa chỉ base URL của service Core
- `CORE_SERVICE_TIMEOUT_SECONDS`: thời gian chờ khi Vision gọi sang Core
- `YOLO_MODEL_NAME`: model YOLO đang dùng, ví dụ `yolov8n.pt`
- `IMAGE_FETCH_TIMEOUT_SECONDS`: thời gian chờ khi tải ảnh từ `IMAGE_URL`
- `MAX_IMAGE_SIZE_BYTES`: kích thước ảnh tối đa được chấp nhận
- `YOLO_CONFIG_DIR`: thư mục cache và cấu hình của Ultralytics
- `TORCH_HOME`: thư mục cache của Torch
- `UPLOADS_DIR`: thư mục lưu ảnh upload từ giao diện demo
- `OBJECT_STORAGE_ROOT`: thư mục gốc mô phỏng object storage cho `OBJECT_STORAGE_REF`
- `DEMO_TITLE`: tiêu đề hiển thị trên trang demo

## Ví Dụ Sử Dụng Nhanh

### Kiểm Tra Health

```bash
curl http://localhost:8000/health
```

### Camera Gọi Sang Vision

```bash
curl -X POST http://localhost:8000/vision/detect ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer demo-token" ^
  -d "{\"requestId\":\"REQ-CAM-001\",\"cameraId\":\"CAM-01\",\"capturedAt\":\"2026-06-16T14:20:00Z\",\"traceId\":\"TRACE-001\",\"zoneId\":\"ER-01\",\"motionLevel\":0.9,\"notes\":\"demo\",\"imageSource\":{\"sourceType\":\"IMAGE_URL\",\"url\":\"http://host.docker.internal:8000/demo-assets/images/bus.jpg\"}}"
```

### Lấy Kết Quả Nhận Diện

```bash
curl http://localhost:8000/vision/detections/DET-20260616-2697 ^
  -H "Authorization: Bearer demo-token"
```

## Ghi Chú Tích Hợp Cho Nhóm Camera

Cách làm khuyến nghị cho nhóm Camera:

- dùng `POST /vision/detect`
- gửi `imageSource.sourceType = IMAGE_URL`
- cung cấp ảnh qua một URL HTTP có thể truy cập được
- đảm bảo máy chạy Vision có thể truy cập URL đó qua mạng

Nếu nhóm Camera muốn mô phỏng object storage thay vì URL, có thể dùng:

- `imageSource.sourceType = OBJECT_STORAGE_REF`
- `bucket`
- `objectKey`
- `expiresAt`

Ví dụ URL ảnh:

```text
http://<camera-host>:8000/images/bus.jpg
```

Các payload mẫu đã chuẩn bị:

- [camera-detect-bus.json](/d:/AI_Vision_Service/demo_assets/requests/camera-detect-bus.json:1)
- [camera-detect-zidane.json](/d:/AI_Vision_Service/demo_assets/requests/camera-detect-zidane.json:1)
- [camera-detect-object-storage.json](/d:/AI_Vision_Service/demo_assets/requests/camera-detect-object-storage.json:1)

## Ghi Chú Tích Hợp Cho Nhóm Core

Nếu có cấu hình `CORE_SERVICE_URL`, Vision sẽ gửi kết quả nhận diện tới:

```text
POST <CORE_SERVICE_URL>/api/v1/detections
```

Nhóm Core cần có endpoint nhận payload kết quả do Vision gửi sang.

Trong Docker Compose hiện tại, service `mock-core` đã đóng vai trò endpoint mẫu để:

- xác minh Vision gọi outbound thành công
- kiểm tra payload Vision gửi sang Core
- demo tích hợp ngay cả khi chưa nối sang Core thật

## Tài Nguyên Demo

Các ảnh mẫu đã chuẩn bị:

- [bus.jpg](/d:/AI_Vision_Service/demo_assets/images/bus.jpg)
- [zidane.jpg](/d:/AI_Vision_Service/demo_assets/images/zidane.jpg)
- [person-crop.jpg](/d:/AI_Vision_Service/demo_assets/images/person-crop.jpg)

Kịch bản demo gợi ý:

- [demo-scenarios.md](/d:/AI_Vision_Service/demo_assets/demo-scenarios.md:1)

## Kiểm Thử

### Chạy Test Tự Động

```bash
.venv\Scripts\python -m pytest -q
```

Phạm vi test cơ bản hiện có:

- `GET /health`
- kiểm tra auth cho `POST /vision/detect`
- luồng nhận diện bằng `IMAGE_URL`
- luồng nhận diện bằng `OBJECT_STORAGE_REF`
- lỗi trùng `requestId`
- lỗi `404` và lỗi validation schema
- luồng upload ảnh cho giao diện demo

### Kiểm Thử Thủ Công

1. Mở `http://localhost:8000/demo`
2. Tải lên `bus.jpg` hoặc `zidane.jpg`
3. Kiểm tra bounding box trên ảnh
4. Rê chuột vào từng object trong danh sách để xem highlight
5. Gọi `POST /vision/detect` bằng payload mẫu của Camera
6. Gọi `GET /vision/detections/{detectionId}`

Checklist kiểm thử:

- [basic-verification.md](/d:/AI_Vision_Service/reports/basic-verification.md:1)

## Giới Hạn Hiện Tại

- Luồng tích hợp chính vẫn ưu tiên `IMAGE_URL` vì dễ tích hợp nhất với nhóm Camera
- `OBJECT_STORAGE_REF` hiện đang dùng thư mục object storage mô phỏng cục bộ; nếu triển khai thật cần nối sang MinIO, S3 hoặc storage dùng chung
- Luồng Vision -> Core cần URL thật của Core để test end-to-end hoàn chỉnh

## Trạng Thái Hiện Tại

Service hiện đang chạy được với:

- FastAPI server
- PostgreSQL
- Docker
- YOLO inference thật
- giao diện demo có bounding box
- highlight object khi hover
- test tự động cơ bản
#   A I - V i s i o n  
 