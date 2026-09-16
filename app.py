import os
import time
from flask import Flask, render_template, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

def run_playwright_submission(falcon_id, request_type, extra_detail=""):
    form_url = (
        "https://docs.google.com/forms/d/e/1FAIpQLSfONIExs2g6a97p9SA0Hb5ef3EHk4ETO5ZiKW6ikoYGSpI_Pg/viewform?"
        f"entry.2078962628=BTR+DELIVERY&entry.141705210={falcon_id}"
    )
    print(f"DEBUG: Starting submission for Falcon ID: {falcon_id}, Type: {request_type}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()

        try:
            print("DEBUG: Navigating to form URL...")
            page.goto(form_url, timeout=60000, wait_until="domcontentloaded")
            time.sleep(2)

            # Handle draft prompts if they appear
            draft_buttons = page.locator(
                'div[role="button"]:has-text("Keep previous"), '
                'div[role="button"]:has-text("Discard draft")'
            )
            if draft_buttons.count() > 0 and draft_buttons.first.is_visible():
                print("DEBUG: Clearing draft prompt...")
                draft_buttons.first.click(force=True)
                time.sleep(1)

            # Select first dropdown/request type (Reactivate, etc.)
            dropdowns = page.locator('div[role="listbox"]')
            if dropdowns.count() > 0 and dropdowns.first.is_visible():
                print("DEBUG: Clicking request type dropdown...")
                dropdowns.first.click(force=True)
                time.sleep(0.5)
                option = page.locator(f'div[role="option"]:has-text("{request_type}")').first
                if option.is_visible():
                    option.click(force=True)
                    print(f"DEBUG: Selected request type -> {request_type}")

            time.sleep(1.5)

            # Page navigation loop to step through all pages up to Submit
            max_pages = 10
            page_count = 0

            while page_count < max_pages:
                if page.is_closed():
                    print("DEBUG: Page closed unexpectedly.")
                    break
                page_count += 1
                print(f"DEBUG: Processing form page loop count: {page_count}")

                # Handle secondary dropdowns if present on later pages
                sec_dropdown = page.locator('div[role="listbox"]').first
                if sec_dropdown.is_visible():
                    sec_text = sec_dropdown.inner_text()
                    if ("Choose" in sec_text or "Select" in sec_text) and extra_detail:
                        print("DEBUG: Handling secondary dropdown...")
                        sec_dropdown.click(force=True)
                        time.sleep(0.5)
                        target_opt = page.locator(f'div[role="option"]:has-text("{extra_detail}")').first
                        if target_opt.is_visible():
                            target_opt.click(force=True)
                            print(f"DEBUG: Selected extra detail -> {extra_detail}")
                            time.sleep(1)

                # Fill extra text inputs if needed on current page
                if extra_detail:
                    text_inputs = page.locator('input[type="text"], textarea')
                    for i in range(text_inputs.count()):
                        inp = text_inputs.nth(i)
                        if inp.is_visible() and inp.input_value() != str(falcon_id) and not inp.input_value():
                            inp.fill(str(extra_detail))
                            print(f"DEBUG: Filled text input with -> {extra_detail}")
                            time.sleep(0.5)
                            break

                # Check if final Submit button is visible
                submit_btn = page.locator('div[role="button"]:has-text("Submit")').first
                if submit_btn.is_visible():
                    print("DEBUG: Submit button found! Clicking submit...")
                    submit_btn.click(force=True)
                    time.sleep(4)
                    print("DEBUG: Form submission completed successfully.")
                    return True

                # Otherwise look for the Next button and click it
                next_btn = page.locator('div[role="button"]:has-text("Next")').first
                if next_btn.is_visible():
                    print("DEBUG: Next button found. Clicking Next to proceed...")
                    next_btn.click(force=True)
                    time.sleep(2)
                else:
                    print("DEBUG: No Submit or Next button found on this page.")
                    break

            return True
        except Exception as err:
            print(f"CRITICAL ERROR in Playwright script: {err}")
            raise err
        finally:
            browser.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    try:
        run_playwright_submission(
            falcon_id=data.get("falcon_id"),
            request_type=data.get("request_type"),
            extra_detail=data.get("extra_detail", "")
        )
        return jsonify({"status": "success", "message": "Ticket submitted successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
