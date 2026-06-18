from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from app import schemas


def _fake_result(detection_id: str, request_id: str, trace_id: str, thumbnail_url: str | None) -> schemas.DetectionResult:
    return schemas.DetectionResult(
        detectionId=detection_id,
        requestId=request_id,
        traceId=trace_id,
        status="COMPLETED",
        confidence=0.97,
        riskLevel="HIGH",
        modelVersion="yolov8n.pt",
        summary="Detected 1 object(s); top labels: person",
        alertHint="REVIEW_SECURITY",
        processedAt=datetime.now(timezone.utc),
        completedAt=datetime.now(timezone.utc),
        thumbnailUrl=thumbnail_url,
        objects=[
            schemas.DetectedObject(
                objectType="PERSON",
                label="person",
                confidence=0.97,
                trackId="TRACK-1",
                boundingBox=schemas.BoundingBox(x=0.1, y=0.1, width=0.4, height=0.7),
            )
        ],
        errorDetail=None,
    )


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "ai-vision"


def test_vision_detect_requires_bearer_auth(client):
    payload = {
        "requestId": "REQ-CAM-20260616-0001",
        "cameraId": "CAM-ER-01",
        "capturedAt": "2026-06-16T13:00:00Z",
        "traceId": "TRACE-20260616-0001",
        "imageSource": {
            "sourceType": "IMAGE_URL",
            "url": "http://camera.example/frame.jpg",
        },
    }

    response = client.post("/vision/detect", json=payload)
    assert response.status_code == 401


def test_vision_detect_image_url_flow(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.send_detection_to_core", lambda result: None)
    monkeypatch.setattr(
        "app.api.routes.process_detection_request",
        lambda detection_id, payload: _fake_result(
            detection_id,
            payload.requestId,
            payload.traceId,
            str(payload.imageSource.url),
        ),
    )

    payload = {
        "requestId": "REQ-CAM-20260616-0002",
        "cameraId": "CAM-ER-01",
        "capturedAt": "2026-06-16T13:00:00Z",
        "traceId": "TRACE-20260616-0002",
        "zoneId": "ER-ENTRANCE",
        "motionLevel": 0.88,
        "notes": "Camera integration test",
        "imageSource": {
            "sourceType": "IMAGE_URL",
            "url": "http://camera.example/frame.jpg",
        },
    }

    response = client.post(
        "/vision/detect",
        json=payload,
        headers={"Authorization": "Bearer demo-token"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["requestId"] == payload["requestId"]
    assert body["preliminaryResult"]["status"] == "COMPLETED"
    assert body["preliminaryResult"]["objects"][0]["objectType"] == "PERSON"

    detection_id = body["detectionId"]
    result_response = client.get(
        f"/vision/detections/{detection_id}",
        headers={"Authorization": "Bearer demo-token"},
    )
    assert result_response.status_code == 200
    result_body = result_response.json()
    assert result_body["status"] == "COMPLETED"
    assert result_body["thumbnailUrl"] == "http://camera.example/frame.jpg"


def test_vision_detect_duplicate_request_id_returns_409(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.send_detection_to_core", lambda result: None)
    monkeypatch.setattr(
        "app.api.routes.process_detection_request",
        lambda detection_id, payload: _fake_result(
            detection_id,
            payload.requestId,
            payload.traceId,
            str(payload.imageSource.url),
        ),
    )

    payload = {
        "requestId": "REQ-CAM-20260616-0003",
        "cameraId": "CAM-ER-01",
        "capturedAt": "2026-06-16T13:00:00Z",
        "traceId": "TRACE-20260616-0003",
        "imageSource": {
            "sourceType": "IMAGE_URL",
            "url": "http://camera.example/frame.jpg",
        },
    }

    first = client.post(
        "/vision/detect",
        json=payload,
        headers={"Authorization": "Bearer demo-token"},
    )
    assert first.status_code == 202

    second = client.post(
        "/vision/detect",
        json=payload,
        headers={"Authorization": "Bearer demo-token"},
    )
    assert second.status_code == 409
    assert second.headers["content-type"].startswith("application/problem+json")


def test_get_detection_not_found_returns_404(client):
    response = client.get(
        "/vision/detections/DET-20260616-9999",
        headers={"Authorization": "Bearer demo-token"},
    )
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


def test_vision_detect_validation_error_returns_problem_json(client):
    payload = {
        "requestId": "INVALID-ID",
        "cameraId": "CAM-ER-01",
        "capturedAt": "2026-06-16T13:00:00Z",
        "traceId": "TRACE-20260616-0004",
        "imageSource": {
            "sourceType": "IMAGE_URL",
            "url": "not-a-url",
        },
    }

    response = client.post(
        "/vision/detect",
        json=payload,
        headers={"Authorization": "Bearer demo-token"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["title"] == "Invalid request body"
    assert body["errors"]


def test_vision_identify_requires_bearer_auth(client):
    payload = {
        "requestId": "REQ-CAM-20260616-0100",
        "cameraId": "CAM-ER-01",
        "capturedAt": "2026-06-16T13:00:00Z",
        "traceId": "TRACE-20260616-0100",
        "imageSource": {
            "sourceType": "IMAGE_URL",
            "url": "http://camera.example/frame.jpg",
        },
    }

    response = client.post("/vision/identify", json=payload)
    assert response.status_code == 401


def test_vision_identify_flow_returns_recognized_people(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.process_identity_request",
        lambda db, payload: schemas.IdentityCheckResponse(
            requestId=payload.requestId,
            traceId=payload.traceId,
            status="COMPLETED",
            modelVersion="yolov8n.pt",
            summary="Detected 1 object(s); recognized person: Zidane",
            processedAt=datetime.now(timezone.utc),
            personCount=1,
            recognizedPersons=[
                schemas.RecognizedPerson(
                    trackId="TRACK-1",
                    displayName="Zidane",
                    matchConfidence=0.96,
                    detectionConfidence=0.97,
                    boundingBox=schemas.BoundingBox(x=0.1, y=0.1, width=0.4, height=0.7),
                    objectLabel="person",
                )
            ],
            errorDetail=None,
        ),
    )

    payload = {
        "requestId": "REQ-CAM-20260616-0101",
        "cameraId": "CAM-ER-01",
        "capturedAt": "2026-06-16T13:00:00Z",
        "traceId": "TRACE-20260616-0101",
        "imageSource": {
            "sourceType": "IMAGE_URL",
            "url": "http://camera.example/frame.jpg",
        },
    }

    response = client.post(
        "/vision/identify",
        json=payload,
        headers={"Authorization": "Bearer demo-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["personCount"] == 1
    assert body["recognizedPersons"][0]["displayName"] == "Zidane"


def test_register_identity_and_list_identities(client):
    image = Image.new("RGB", (320, 480), color=(120, 90, 150))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    register_response = client.post(
        "/vision/identities/register",
        headers={"Authorization": "Bearer demo-token"},
        files={"image": ("identity.jpg", buffer.getvalue(), "image/jpeg")},
        data={
            "personCode": "ID-LECTURER-01",
            "displayName": "Lecturer One",
            "notes": "Front-facing reference image",
        },
    )
    assert register_response.status_code == 200
    register_body = register_response.json()
    assert register_body["status"] == "CREATED"
    assert register_body["identity"]["personCode"] == "ID-LECTURER-01"

    list_response = client.get(
        "/vision/identities",
        headers={"Authorization": "Bearer demo-token"},
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert len(list_body) == 1
    assert list_body[0]["displayName"] == "Lecturer One"
    assert list_body[0]["sampleCount"] == 1
    assert len(list_body[0]["referenceImageUrls"]) == 1


def test_register_identity_supports_multiple_samples_for_same_person(client):
    first = Image.new("RGB", (320, 480), color=(120, 90, 150))
    first_buffer = BytesIO()
    first.save(first_buffer, format="JPEG")
    first_buffer.seek(0)

    second = Image.new("RGB", (320, 480), color=(80, 120, 160))
    second_buffer = BytesIO()
    second.save(second_buffer, format="JPEG")
    second_buffer.seek(0)

    first_response = client.post(
        "/vision/identities/register",
        headers={"Authorization": "Bearer demo-token"},
        files={"image": ("first.jpg", first_buffer.getvalue(), "image/jpeg")},
        data={
            "personCode": "ID-LECTURER-02",
            "displayName": "Lecturer Two",
            "notes": "Sample one",
        },
    )
    assert first_response.status_code == 200
    assert first_response.json()["status"] == "CREATED"

    second_response = client.post(
        "/vision/identities/register",
        headers={"Authorization": "Bearer demo-token"},
        files={"image": ("second.jpg", second_buffer.getvalue(), "image/jpeg")},
        data={
            "personCode": "ID-LECTURER-02",
            "displayName": "Lecturer Two",
            "notes": "Sample two",
        },
    )
    assert second_response.status_code == 200
    assert second_response.json()["status"] == "UPDATED"

    list_response = client.get(
        "/vision/identities",
        headers={"Authorization": "Bearer demo-token"},
    )
    body = list_response.json()
    assert len(body) == 1
    assert body[0]["sampleCount"] == 2
    assert len(body[0]["referenceImageUrls"]) == 2


def test_delete_identity_removes_person_and_samples(client):
    image = Image.new("RGB", (320, 480), color=(120, 90, 150))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    client.post(
        "/vision/identities/register",
        headers={"Authorization": "Bearer demo-token"},
        files={"image": ("identity.jpg", buffer.getvalue(), "image/jpeg")},
        data={
            "personCode": "ID-LECTURER-03",
            "displayName": "Lecturer Three",
            "notes": "Delete me",
        },
    )

    delete_response = client.delete(
        "/vision/identities/ID-LECTURER-03",
        headers={"Authorization": "Bearer demo-token"},
    )
    assert delete_response.status_code == 200
    delete_body = delete_response.json()
    assert delete_body["status"] == "DELETED"
    assert delete_body["deletedSampleCount"] == 1

    list_response = client.get(
        "/vision/identities",
        headers={"Authorization": "Bearer demo-token"},
    )
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_vision_detect_timeout_returns_failed_result(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.send_detection_to_core", lambda result: None)

    def raise_timeout(detection_id, payload):
        return schemas.DetectionResult(
            detectionId=detection_id,
            requestId=payload.requestId,
            traceId=payload.traceId,
            status="FAILED",
            confidence=0,
            riskLevel="LOW",
            modelVersion="yolov8n.pt",
            summary="Detection failed while processing the input image",
            alertHint="NONE",
            processedAt=datetime.now(timezone.utc),
            completedAt=datetime.now(timezone.utc),
            thumbnailUrl=None,
            objects=[],
            errorDetail="timed out",
        )

    monkeypatch.setattr("app.api.routes.process_detection_request", raise_timeout)

    payload = {
        "requestId": "REQ-CAM-20260616-0005",
        "cameraId": "CAM-ER-01",
        "capturedAt": "2026-06-16T13:00:00Z",
        "traceId": "TRACE-20260616-0005",
        "imageSource": {
            "sourceType": "IMAGE_URL",
            "url": "http://camera.example/frame.jpg",
        },
    }

    response = client.post(
        "/vision/detect",
        json=payload,
        headers={"Authorization": "Bearer demo-token"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["preliminaryResult"]["status"] == "FAILED"
    assert body["preliminaryResult"]["objects"] == []


def test_vision_detect_object_storage_flow(client, monkeypatch, tmp_path):
    monkeypatch.setattr("app.api.routes.send_detection_to_core", lambda result: None)
    image = Image.new("RGB", (320, 240), color=(80, 160, 220))
    bucket_path = tmp_path / "object_store" / "camera-stream-cache" / "ICU-02" / "2026" / "05" / "12"
    bucket_path.mkdir(parents=True, exist_ok=True)
    file_path = bucket_path / "frame-1002.jpg"
    image.save(file_path, format="JPEG")

    import app.main as main_module
    import app.services.detection_service as detection_module

    main_module.settings.object_storage_root = str(tmp_path / "object_store")
    detection_module.settings.object_storage_root = str(tmp_path / "object_store")

    monkeypatch.setattr(
        "app.services.detection_service._load_model",
        lambda: type(
            "FakeModel",
            (),
            {
                "predict": lambda self, image, verbose=False: [
                    type(
                        "FakePrediction",
                        (),
                        {
                            "boxes": [],
                            "orig_shape": (240, 320),
                            "names": {},
                        },
                    )()
                ]
            },
        )(),
    )

    payload = {
        "requestId": "REQ-CAM-20260616-0006",
        "cameraId": "CAM-ICU-02",
        "capturedAt": "2026-06-16T13:00:00Z",
        "traceId": "TRACE-20260616-0006",
        "imageSource": {
            "sourceType": "OBJECT_STORAGE_REF",
            "bucket": "camera-stream-cache",
            "objectKey": "ICU-02/2026/05/12/frame-1002.jpg",
            "expiresAt": "2099-06-16T13:10:00Z",
        },
    }

    response = client.post(
        "/vision/detect",
        json=payload,
        headers={"Authorization": "Bearer demo-token"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["preliminaryResult"]["status"] == "COMPLETED"
    assert body["preliminaryResult"]["thumbnailUrl"] is None


def test_demo_upload_flow(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.send_detection_to_core", lambda result: None)
    monkeypatch.setattr(
        "app.api.routes.process_uploaded_image",
        lambda **kwargs: _fake_result(
            kwargs["detection_id"],
            kwargs["request_id"],
            kwargs["trace_id"],
            kwargs["thumbnail_url"],
        ),
    )

    image = Image.new("RGB", (320, 240), color=(240, 120, 80))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    response = client.post(
        "/demo/api/detect",
        files={"image": ("demo.jpg", buffer.getvalue(), "image/jpeg")},
        data={
            "cameraId": "CAM-DEMO-01",
            "zoneId": "DEMO-ZONE",
            "motionLevel": "0.75",
            "notes": "UI upload test",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["imageUrl"].startswith("/media/")
    assert body["result"]["status"] == "COMPLETED"
    assert body["result"]["objects"][0]["label"] == "person"
