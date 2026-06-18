# Demo Scenarios

Use these assets for slides, smoke tests, and live demos.

## 1. `images/bus.jpg`

- Best for: upload demo in `/demo`
- Expected signal:
  - multiple `PERSON`
  - one large `bus`
  - `riskLevel` should be `HIGH`
- Talking point:
  - Vision detects multiple people from a single frame and stores the result for downstream services

## 2. `images/zidane.jpg`

- Best for: contract demo with `POST /vision/detect`
- Expected signal:
  - two `PERSON`
  - one `UNKNOWN` object such as `tie`
  - `riskLevel` should be `HIGH`
- Talking point:
  - Camera team can send an `IMAGE_URL`, and Vision fetches the image itself before running YOLO

## 3. `images/person-crop.jpg`

- Best for: simple slide screenshot focused on one subject
- Expected signal:
  - at least one `PERSON`
- Talking point:
  - good for showing a clean bounding-box result in presentation slides

## Suggested slide flow

1. Show `/health` and mention service readiness
2. Show `/demo` upload with `bus.jpg`
3. Show `POST /vision/detect` with `zidane.jpg` as `IMAGE_URL`
4. Show `GET /vision/detections/{detectionId}`
5. Mention that Vision can push the result to Core through `CORE_SERVICE_URL`
