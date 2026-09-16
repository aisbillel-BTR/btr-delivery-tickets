import os
import time
from flask import Flask, render_template, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# Check if we are running on Render or local environment
IS_RENDER = os.environ.get("RENDER", "false").lower() == "true"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    falcon_id = data.get("falcon_id")
    request_type = data.get("request_type")

    if not falcon_id or not request_type:
        return jsonify({"success": False, "error": "Missing required fields."}), 400

    try:
        with sync_playwright() as p:
            # On Render, we MUST run headless=True. Locally, you can set it to False to watch.
            headless_mode = True if IS_RENDER else False

            # Launch persistent context to preserve your Google login session
            context = p.chromium.launch_persistent_context(
                user_data_dir="playwright_profile",
                headless=headless_mode,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--single-process",
                    "--disable-gpu"
                ]
            )

            page = context.new_page()
            
            # Your Google Form URL
            form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfONIExs2g6a97p9SA0Hb5ef3EHk4ETO5ZiKW6ikoYGSpI_Pg/viewform?pli=1"
            page.goto(form_url)
            page.wait_for_load_state("networkidle")

            # --- GOOGLE LOGIN CHECK ---
            if "accounts.google.com" in page.url or "signin" in page.url:
                if headless_mode:
                    return jsonify({
                        "success": False, 
                        "error": "Google Login required, but browser is running in headless mode! Please log in locally first to save cookies."
                    }), 400
                else:
                    print("\n" + "="*50)
                    print("GOOGLE LOGIN REQUIRED:")
                    print("Please log in manually in the browser window.")
                    print("="*50 + "\n")
                    
                    while "accounts.google.com" in page.url or "signin" in page.url:
                        if page.is_closed():
                            return jsonify({"success": False, "error": "Browser closed during login."}), 500
                        time.sleep(1)
                    time.sleep(2)

            # --- FORM FILLING AUTOMATION ---
            # Filling Falcon ID into the first text input field found on the form
            page.locator('input[type="text"]').first.fill(str(falcon_id))
            
            # Add your remaining form interactions here if needed
            
            context.close()
            return jsonify({"success": True, "message": "Ticket submitted successfully!"})

    except Exception as e:
        error_msg = str(e)
        print(f"CRITICAL ERROR in Playwright script: {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
