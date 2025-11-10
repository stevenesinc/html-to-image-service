from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import tempfile
import os
import time
import io
from playwright.sync_api import sync_playwright
from PIL import Image

app = Flask(__name__)
CORS(app)

# Set Playwright browser path for Render.com
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/ms-playwright'

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "HTML to Image Converter",
        "version": "1.0.0",
        "status": "running"
    })

@app.route("/ping", methods=["POST"])
def ping():
    data = request.get_json(force=True, silent=True) or {}
    return jsonify({
        "success": True,
        "message": "Hello from Python (Playwright)!",
        "echo": data,
        "timestamp": time.time()
    })

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "html-to-image",
        "timestamp": time.time()
    })

def html_to_image(html_content, quality=100):
    temp_html_path = None
    try:
        # Write HTML to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(html_content)
            temp_html_path = f.name
        
        file_url = f"file:///{temp_html_path.replace(os.sep, '/')}"
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = browser.new_page()
            page.goto(file_url)
            page.wait_for_load_state("networkidle")
            
            # Capture full page as PNG
            screenshot_bytes = page.screenshot(full_page=True, type='png')
            browser.close()
        
        # Return PNG directly (no conversion to JPEG)
        return {
            "success": True,
            "base64_image": base64.b64encode(screenshot_bytes).decode("utf-8"),
            "file_size": len(screenshot_bytes)
        }
    
    except Exception as e:
        import traceback
        print("❌ PLAYWRIGHT ERROR:", traceback.format_exc())
        return {"success": False, "error": str(e)}
    
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.unlink(temp_html_path)

@app.route("/convert", methods=["POST"])
def convert_html_to_image():
    data = request.get_json()
    if not data or "html" not in data:
        return jsonify({"success": False, "error": "HTML content is required"}), 400
    
    result = html_to_image(
        html_content=data["html"],
        quality=data.get("quality", 100)
    )
    
    if result["success"]:
        return jsonify({
            "success": True,
            "data": result["base64_image"],
            "file_size": result["file_size"],
            "mime_type": "image/png"
        })
    else:
        return jsonify({"success": False, "error": result["error"]}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting HTML → Image Service on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
