const els = {
  imageInput: document.getElementById("imageInput"),
  cameraInput: document.getElementById("cameraInput"),
  cameraButton: document.getElementById("cameraButton"),
  ocrButton: document.getElementById("ocrButton"),
  preview: document.getElementById("preview"),
  output: document.getElementById("output"),
  progress: document.getElementById("progress"),
  progressFill: document.getElementById("progressFill"),
  progressPercent: document.getElementById("progressPercent"),
  progressEta: document.getElementById("progressEta"),
  cameraModal: document.getElementById("cameraModal"),
  cameraVideo: document.getElementById("cameraVideo"),
  captureButton: document.getElementById("captureButton"),
  closeCameraButton: document.getElementById("closeCameraButton"),
};

let selectedFile = null;
let cameraStream = null;
let progressTimer = null;
let progressStart = 0;

const OCR_TIME_KEY = "ocr_avg_ms";
const OCR_DEFAULT_MS = 30000;

function getEstimatedMs() {
  const saved = Number(localStorage.getItem(OCR_TIME_KEY));
  return Number.isFinite(saved) && saved > 0 ? saved : OCR_DEFAULT_MS;
}

function rememberDuration(ms) {
  const current = getEstimatedMs();
  const next = Math.round(current * 0.7 + ms * 0.3);
  localStorage.setItem(OCR_TIME_KEY, String(next));
}

function formatEta(ms) {
  const sec = Math.max(0, Math.ceil(ms / 1000));
  const min = Math.floor(sec / 60);
  const rem = sec % 60;
  return min > 0 ? `${min}m ${rem}s` : `${rem}s`;
}

function startProgress() {
  const estimate = getEstimatedMs();
  progressStart = performance.now();

  els.progress.classList.add("active");
  els.progressFill.style.width = "0%";
  els.progressPercent.textContent = "0%";
  els.progressEta.textContent = `ETA ${formatEta(estimate)}`;

  if (progressTimer) clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    const elapsed = performance.now() - progressStart;
    const pct = Math.min(95, (elapsed / estimate) * 100);
    const remaining = Math.max(0, estimate - elapsed);
    els.progressFill.style.width = `${pct.toFixed(0)}%`;
    els.progressPercent.textContent = `${pct.toFixed(0)}%`;
    els.progressEta.textContent = `ETA ${formatEta(remaining)}`;
  }, 250);
}

function stopProgress(ok) {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }

  if (ok) {
    els.progressFill.style.width = "100%";
    els.progressPercent.textContent = "100%";
    els.progressEta.textContent = "Completed";
    setTimeout(() => els.progress.classList.remove("active"), 700);
  } else {
    els.progress.classList.remove("active");
  }
}

function applySelectedFile(file) {
  selectedFile = file;
  if (!selectedFile) return;

  els.preview.src = URL.createObjectURL(selectedFile);
  els.preview.style.display = "block";

  els.output.classList.remove("error");
  els.output.textContent = "Image loaded. Click 'Start OCR' to continue.";
  els.ocrButton.disabled = false;
}

function stopCameraStream() {
  if (!cameraStream) return;
  cameraStream.getTracks().forEach((t) => t.stop());
  cameraStream = null;
}

function closeCameraModal() {
  els.cameraModal.classList.remove("active");
  els.cameraVideo.srcObject = null;
  stopCameraStream();
}

async function openCamera() {
  const canUseCamera =
    window.isSecureContext &&
    navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function";

  if (!canUseCamera) {
    els.cameraInput.click();
    return;
  }

  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    });
    els.cameraVideo.srcObject = cameraStream;
    els.cameraModal.classList.add("active");
  } catch {
    els.cameraInput.click();
  }
}

function captureFromVideo() {
  const video = els.cameraVideo;
  if (!video.videoWidth || !video.videoHeight) return;

  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob((blob) => {
    if (!blob) return;
    const file = new File([blob], `camera_${Date.now()}.jpg`, { type: "image/jpeg" });
    applySelectedFile(file);
    closeCameraModal();
  }, "image/jpeg", 0.92);
}

async function runOcr() {
  if (!selectedFile) return;

  els.output.classList.remove("error");
  els.output.textContent = "Processing with Typhoon OCR...\nPlease wait...";
  startProgress();
  const startedAt = performance.now();

  const formData = new FormData();
  formData.append("image", selectedFile);

  try {
    const res = await fetch("/ocr", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok || data.error) {
      stopProgress(false);
      els.output.classList.add("error");
      const msg = data.error || "OCR request failed";
      const details = data.details ? `\nDetails: ${data.details}` : "";
      els.output.textContent = `Error: ${msg}${details}`;
      return;
    }

    const text = data.formatted_text || data.raw_text || data.results?.[0]?.message?.choices?.[0]?.message?.content;
    els.output.textContent = text || "No text was detected in this image.";
    rememberDuration(performance.now() - startedAt);
    stopProgress(true);
  } catch (err) {
    stopProgress(false);
    els.output.classList.add("error");
    els.output.textContent = `Error: ${err.message}`;
  }
}

els.imageInput.addEventListener("change", (e) => applySelectedFile(e.target.files[0]));
els.cameraInput.addEventListener("change", (e) => applySelectedFile(e.target.files[0]));
els.cameraButton.addEventListener("click", openCamera);
els.captureButton.addEventListener("click", captureFromVideo);
els.closeCameraButton.addEventListener("click", closeCameraModal);
els.ocrButton.addEventListener("click", runOcr);

window.addEventListener("beforeunload", stopCameraStream);
