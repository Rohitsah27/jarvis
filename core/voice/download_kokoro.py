"""
Automated downloader for Kokoro ONNX model and voices.
Downloads model files to core/voice/models/
"""
import os
import sys
import urllib.request

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
# fp32 model (~310MB). Deliberately NOT the "faster" int8 quantized model
# (~88MB): measured on real hardware, int8 was ~4x SLOWER (RTF ~2.1 vs ~0.5)
# because this onnxruntime build lacks fused int8 kernels for Kokoro's ops.
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"

def download_file(url, dest_path):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        print(f"[Kokoro] File already exists: {os.path.basename(dest_path)} ({os.path.getsize(dest_path)/(1024*1024):.1f} MB)")
        return True

    print(f"[Kokoro] Downloading {os.path.basename(dest_path)} from {url}...")
    tmp_path = dest_path + ".tmp"
    
    def report_progress(block_num, block_size, total_size):
        if total_size > 0:
            percent = (block_num * block_size / total_size) * 100
            downloaded_mb = (block_num * block_size) / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\rDownloading {os.path.basename(dest_path)}: {percent:.1f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)")
            sys.stdout.flush()

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp, open(tmp_path, "wb") as out_file:
            total_size = int(resp.headers.get("Content-Length", 0))
            block_num = 0
            block_size = 1024 * 128  # 128 KB
            while True:
                chunk = resp.read(block_size)
                if not chunk:
                    break
                out_file.write(chunk)
                block_num += 1
                report_progress(block_num, block_size, total_size)
        print()
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(tmp_path, dest_path)
        print(f"[Kokoro] Successfully downloaded: {os.path.basename(dest_path)}")
        return True
    except Exception as e:
        print(f"\n[Kokoro] Error downloading {url}: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False

def ensure_kokoro_models():
    os.makedirs(MODELS_DIR, exist_ok=True)
    voices_path = os.path.join(MODELS_DIR, "voices-v1.0.bin")
    model_path = os.path.join(MODELS_DIR, "kokoro-v1.0.onnx")

    ok1 = download_file(VOICES_URL, voices_path)
    ok2 = download_file(MODEL_URL, model_path)
    return ok1 and ok2

if __name__ == "__main__":
    success = ensure_kokoro_models()
    print(f"[Kokoro] Download complete. Success = {success}")
