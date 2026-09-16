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
            # On Render, we MUST run headless=True. Locally, you can set it to False if you want to watch it.
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
            
            # Navigate to your Google Form target URL
            # Replace this URL with your actual Google Form link
            form_url = "YOUR_GOOGLE_FORM_URL_HERE"
            page.goto(form_url)
            page.wait_for_load_state("networkidle")

            # --- GOOGLE LOGIN CHECK ---
            if "accounts.google.com" in page.url or "signin" in page.url:
                if headless_mode:
                    return jsonify({
                        "success": False, 
                        "error": "Google Login required, but browser is running in headless mode on the cloud! Please log in locally first and save your session cookies."
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
            # Example field selectors - update these based on your form structure
            # Filling Falcon ID
            page.locator('input[type="text"]').first.fill(str(falcon_id))
            
            # Handling Request Type Dropdown or radio buttons if applicable
            # (Adjust selectors as per your specific form layout)
            
            # Submit the form
            # page.locator('div[role="button"][jsname="M2UYVd"]').click()
            # time.sleep(3)

            context.close()
            return jsonify({"success": True, "message": "Ticket submitted successfully!"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
