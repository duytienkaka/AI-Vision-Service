const form = document.getElementById("detect-form");
const previewImage = document.getElementById("preview-image");
const overlayCanvas = document.getElementById("overlay-canvas");
const previewEmpty = document.getElementById("preview-empty");
const statusBadge = document.getElementById("status-badge");
const submitButton = document.getElementById("submit-button");

const fields = {
  modelName: document.getElementById("model-name"),
  detectionId: document.getElementById("detection-id"),
  riskLevel: document.getElementById("risk-level"),
  confidence: document.getElementById("confidence"),
  alertHint: document.getElementById("alert-hint"),
  objectCount: document.getElementById("object-count"),
  summary: document.getElementById("summary-text"),
  objects: document.getElementById("objects-list"),
  error: document.getElementById("error-text"),
  insightStatus: document.getElementById("insight-status"),
  insightRisk: document.getElementById("insight-risk"),
  insightAlert: document.getElementById("insight-alert"),
};

let latestObjects = [];
let activeObjectIndex = null;

async function loadModelInfo() {
  try {
    const response = await fetch("/vision/models/info", {
      headers: { Authorization: "Bearer demo-token" },
    });
    const data = await response.json();
    fields.modelName.textContent = data.modelVersion || data.modelName;
  } catch {
    fields.modelName.textContent = "Unavailable";
  }
}

function renderObjects(items) {
  if (!items.length) {
    fields.objects.innerHTML = '<p class="empty-line">No objects detected.</p>';
    return;
  }

  fields.objects.innerHTML = items
    .map(
      (item, index) => `
        <div class="object-row" data-index="${index}">
          <div>
            <span class="result-label">Object</span>
            <strong>${item.label || item.objectType}</strong>
          </div>
          <div>
            <span class="result-label">Confidence</span>
            <strong>${(item.confidence * 100).toFixed(1)}%</strong>
          </div>
          <div>
            <span class="result-label">Bounding Box</span>
            <strong>${item.boundingBox.x.toFixed(2)}, ${item.boundingBox.y.toFixed(2)}, ${item.boundingBox.width.toFixed(2)}, ${item.boundingBox.height.toFixed(2)}</strong>
          </div>
        </div>
      `,
    )
    .join("");

  bindObjectHover();
}

function objectColor(objectType) {
  return objectType === "PERSON" ? "#25b36a" : "#b88a28";
}

function clearOverlay() {
  const context = overlayCanvas.getContext("2d");
  context.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  overlayCanvas.hidden = true;
}

function drawOverlay(items) {
  if (!previewImage.complete || !items.length) {
    clearOverlay();
    return;
  }

  const frameRect = previewImage.getBoundingClientRect();
  const naturalWidth = previewImage.naturalWidth || 1;
  const naturalHeight = previewImage.naturalHeight || 1;
  const scale = Math.min(frameRect.width / naturalWidth, frameRect.height / naturalHeight);
  const renderedWidth = naturalWidth * scale;
  const renderedHeight = naturalHeight * scale;
  const offsetX = (frameRect.width - renderedWidth) / 2;
  const offsetY = (frameRect.height - renderedHeight) / 2;

  overlayCanvas.width = frameRect.width;
  overlayCanvas.height = frameRect.height;
  overlayCanvas.hidden = false;

  const context = overlayCanvas.getContext("2d");
  context.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  context.lineWidth = 3;
  context.font = "600 14px Aptos, Segoe UI, sans-serif";
  context.textBaseline = "top";

  items.forEach((item, index) => {
    const isActive = activeObjectIndex === index;
    const color = objectColor(item.objectType);
    const x = offsetX + item.boundingBox.x * renderedWidth;
    const y = offsetY + item.boundingBox.y * renderedHeight;
    const width = item.boundingBox.width * renderedWidth;
    const height = item.boundingBox.height * renderedHeight;
    const label = `${item.label || item.objectType} ${(item.confidence * 100).toFixed(0)}%`;

    context.strokeStyle = color;
    context.fillStyle = isActive ? `${color}55` : `${color}22`;
    context.lineWidth = isActive ? 5 : 3;
    context.strokeRect(x, y, width, height);
    context.fillRect(x, y, width, height);

    const textWidth = context.measureText(label).width;
    context.fillStyle = color;
    context.fillRect(x, Math.max(0, y - 24), textWidth + 18, 22);
    context.fillStyle = "#ffffff";
    context.fillText(label, x + 9, Math.max(0, y - 22));
  });
}

function setPreviewFromFile(file) {
  const blobUrl = URL.createObjectURL(file);
  previewImage.src = blobUrl;
  previewImage.hidden = false;
  previewEmpty.hidden = true;
  latestObjects = [];
  activeObjectIndex = null;
  clearOverlay();
}

function bindObjectHover() {
  const rows = document.querySelectorAll(".object-row");
  rows.forEach((row) => {
    row.addEventListener("mouseenter", () => {
      activeObjectIndex = Number(row.dataset.index);
      rows.forEach((item) => item.classList.remove("active"));
      row.classList.add("active");
      drawOverlay(latestObjects);
    });

    row.addEventListener("mouseleave", () => {
      activeObjectIndex = null;
      row.classList.remove("active");
      drawOverlay(latestObjects);
    });
  });
}

form.image.addEventListener("change", (event) => {
  const [file] = event.target.files;
  if (file) {
    setPreviewFromFile(file);
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = form.image.files[0];
  if (!file) {
    statusBadge.textContent = "Choose image";
    return;
  }

  const formData = new FormData(form);
  submitButton.disabled = true;
  submitButton.textContent = "Detecting...";
  statusBadge.textContent = "Processing";

  try {
    const response = await fetch("/demo/api/detect", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Detection request failed");
    }

    fields.detectionId.textContent = data.detectionId;
    fields.riskLevel.textContent = data.result.riskLevel || "-";
    fields.confidence.textContent =
      data.result.confidence != null
        ? `${(data.result.confidence * 100).toFixed(1)}%`
        : "-";
    fields.alertHint.textContent = data.result.alertHint || "-";
    fields.objectCount.textContent = `${data.result.objects?.length || 0}`;
    fields.summary.textContent = data.result.summary || "No summary.";
    fields.error.textContent = data.result.errorDetail || "No errors.";
    fields.insightStatus.textContent = `Status: ${data.result.status}`;
    fields.insightRisk.textContent = `Risk level: ${data.result.riskLevel || "-"}`;
    fields.insightAlert.textContent = `Recommended action: ${data.result.alertHint || "-"}`;
    renderObjects(data.result.objects || []);
    latestObjects = data.result.objects || [];
    activeObjectIndex = null;
    previewImage.src = data.imageUrl;
    previewImage.hidden = false;
    previewEmpty.hidden = true;
    statusBadge.textContent = data.result.status;
  } catch (error) {
    fields.error.textContent = error.message;
    fields.insightStatus.textContent = "Status: failed to complete the request.";
    fields.insightRisk.textContent = "Risk level: unavailable.";
    fields.insightAlert.textContent = "Recommended action: review the error.";
    activeObjectIndex = null;
    statusBadge.textContent = "Failed";
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Run Detection";
  }
});

previewImage.addEventListener("load", () => {
  drawOverlay(latestObjects);
});

window.addEventListener("resize", () => {
  drawOverlay(latestObjects);
});

loadModelInfo();
