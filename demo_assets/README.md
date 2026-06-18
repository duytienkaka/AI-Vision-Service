# Demo Assets

These assets help the Vision team demo the service without depending on third-party image links.

## Included images

- `images/bus.jpg`: multiple people and one bus
- `images/zidane.jpg`: two people and a sports scene
- `images/person-walk.jpg`: a walking person scene for quick demos

## Suggested usage

- Demo UI upload: open `/demo`, then upload any file from `demo_assets/images/`
- Camera contract demo: host these images from the camera team service and send the image URL through `POST /vision/detect`

## Sample request pattern for Camera

```json
{
  "requestId": "REQ-CAM-20260616-0003",
  "cameraId": "CAM-ER-01",
  "capturedAt": "2026-06-16T13:30:00Z",
  "traceId": "TRACE-20260616-0003",
  "zoneId": "ER-ENTRANCE",
  "motionLevel": 0.91,
  "notes": "Camera team sends an image URL from its gallery service",
  "imageSource": {
    "sourceType": "IMAGE_URL",
    "url": "http://<CAMERA-HOST>:8000/images/bus.jpg"
  }
}
```
