import os
import time
import shutil
from flask import Flask, render_template, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

def run_playwright_submission(falcon_id, request_type, extra_detail=""):
    form_url = (
        "https://docs.google.com/forms/d/e/1FAIpQLSfONIExs2g6a97p9SA0Hb5ef3EHk4ETO5ZiKW6ikoYGSpI_Pg/viewform?"
        f"entry.2078962628=BTR+DELIVERY&entry.141705210={falcon_id}"
    )
    print(f"DEBUG: Starting submission for Falcon ID: {falcon_id}, Type: {request_type}, Detail: {extra_detail}")

    user_data_dir = os.path.join(os.getcwd(), "playwright_profile")

    lock_file = os.path.join(user_data_dir, "SingletonLock")
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
        except Exception:
            pass

    # FIXED: Properly evaluate to a strict Python boolean (True/False)
    render_env = os.environ.get("RENDER", "False")
    is_headless = str(render_env).lower() in ["true", "1", "yes"] or os.environ.get("HEADLESS", "False").lower() == "true"

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=is_headless,
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-dev-shm-usage"
                ],
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        except Exception:
            if os.path.exists(user_data_dir):
                shutil.rmtree(user_data_dir, ignore_errors=True)
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=is_headless,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
            )
        
        page = context.new_page()

        try:
            print("DEBUG: Navigating to form URL...")
            try:
                page.goto(form_url, timeout=90000, wait_until="commit")
            except Exception as nav_err:
                print(f"DEBUG: Initial navigation commit note (continuing anyway): {nav_err}")
            
            time.sleep(4)

            # --- LOGIN CHECK ---
            if "accounts.google.com" in page.url or "signin" in page.url:
                if is_headless:
                    raise Exception("Google Login required, but browser is running in headless mode on the cloud! Please log in locally first and save your session cookies.")
                
                print("\n" + "="*50)
                print("GOOGLE LOGIN REQUIRED:")
                print("Please log in manually in the popup browser window.")
                print("="*50 + "\n")
                
                while "accounts.google.com" in page.url or "signin" in page.url:
                    if page.is_closed():
                        return False
                    time.sleep(1)
                print("DEBUG: Login successful! Proceeding with form automation...")
                time.sleep(2)

            # --- HANDLE DRAFT / RESTORE POPUP IF PRESENT ---
            try:
                print("DEBUG: Checking for draft popup...")
                time.sleep(1.5)
                draft_btn = page.locator(
                    'div[role="button"]:has-text("Continue"), '
                    'div[role="button"]:has-text("Keep previous"), '
                    'div[role="button"]:has-text("Discard draft"), '
                    'div[role="button"]:has-text("Start over")'
                ).first
                if draft_btn.is_visible():
                    draft_btn.click(force=True)
                    print("DEBUG: Dismissed draft popup successfully.")
                    time.sleep(1)
            except Exception as e:
                print(f"DEBUG: No draft popup found or handled: {e}")

            # --- FORCE CHECK THE EMAIL RECORDING BOX ---
            try:
                print("DEBUG: Looking for email recording checkbox...")
                checkbox = page.locator('div[role="checkbox"]').first
                if checkbox.is_visible():
                    if checkbox.get_attribute("aria-checked") != "true":
                        checkbox.click(force=True)
                        time.sleep(1.5)
                        print("DEBUG: Clicked email recording checkbox.")
            except Exception as e:
                print(f"DEBUG: Checkbox handling note: {e}")

            # Page navigation loop to handle multi-page forms
            max_pages = 15
            page_count = 0

            while page_count < max_pages:
                if page.is_closed():
                    break
                page_count += 1
                print(f"DEBUG: Processing page loop count: {page_count}")
                time.sleep(1.5)

                # 1. Fill text inputs and textareas intelligently
                text_inputs = page.locator('input[type="text"], textarea')
                for i in range(text_inputs.count()):
                    inp = text_inputs.nth(i)
                    if inp.is_visible() and not inp.input_value():
                        aria_label = (inp.get_attribute("aria-label") or "").lower()
                        
                        container_text = ""
                        try:
                            parent = inp.locator("xpath=ancestor::div[contains(@class, 'Qr7Oae') or contains(@role, 'listitem')]").first
                            container_text = parent.inner_text().lower()
                        except Exception:
                            pass
                        
                        combined_text = aria_label + " " + container_text

                        is_phone_field = any(k in combined_text for k in ["phone", "mobile", "number"])
                        is_detail_field = any(k in combined_text for k in ["detail", "reason", "note", "explanation", "issue", "description"])

                        if is_phone_field:
                            if extra_detail:
                                inp.fill(str(extra_detail))
                                print(f"DEBUG: Filled Mobile/Phone field strictly with extra_detail -> {extra_detail}")
                            else:
                                print(f"DEBUG: WARNING: Phone field found, but extra_detail is empty!")
                        elif is_detail_field and extra_detail:
                            inp.fill(str(extra_detail))
                            print(f"DEBUG: Filled Detail/Explanation field with extra_detail -> {extra_detail}")
                        else:
                            inp.fill(str(falcon_id))
                            print(f"DEBUG: Filled standard text field with Falcon ID -> {falcon_id}")
                        time.sleep(0.5)

                # 2. Specifically handle dropdowns (Request type, zone selection, etc.)
                dropdowns = page.locator('div[role="listbox"]')
                for d_idx in range(dropdowns.count()):
                    dd = dropdowns.nth(d_idx)
                    if dd.is_visible():
                        dd_text = dd.inner_text().strip()
                        if "Choose" in dd_text or "Select" in dd_text or not dd_text:
                            print(f"DEBUG: Found unselected dropdown ('{dd_text}'). Clicking...")
                            dd.scroll_into_view_if_needed()
                            dd.click(force=True)
                            time.sleep(1.5)
                            
                            options = page.locator('div[role="option"]')
                            if options.count() > 0:
                                target_opt = options.first
                                
                                search_keyword = request_type.strip().lower() if page_count == 1 and request_type else extra_detail.strip().lower()
                                
                                if search_keyword:
                                    found_match = False
                                    for opt_i in range(options.count()):
                                        opt_element = options.nth(opt_i)
                                        opt_inner = opt_element.inner_text().strip().lower()
                                        if search_keyword in opt_inner or opt_inner in search_keyword:
                                            target_opt = opt_element
                                            found_match = True
                                            print(f"DEBUG: Found matching dropdown option for '{search_keyword}': '{opt_inner}'")
                                            break
                                    if not found_match:
                                        print(f"DEBUG: Warning: No match found for '{search_keyword}', falling back to default option.")
                                else:
                                    if options.count() > 1 and ("choose" in options.first.inner_text().lower() or "select" in options.first.inner_text().lower()):
                                        target_opt = options.nth(1)
                                
                                try:
                                    target_opt.scroll_into_view_if_needed()
                                    target_opt.click(force=True)
                                except Exception:
                                    page.evaluate("(el) => el.click()", target_opt.element_handle())

                                print(f"DEBUG: Selected option from dropdown successfully.")
                                time.sleep(1.5)

                # 3. Check if final Submit button is visible
                submit_btn = page.locator('div[role="button"]:has-text("Submit")').first
                if submit_btn.is_visible():
                    print("DEBUG: Submit button found! Looking for 'Send me a copy' toggle...")
                    
                    try:
                        copy_toggle = page.locator('div:has-text("Send me a copy of my responses")').locator('div[role="checkbox"], div[role="switch"], div.export-toggle, input[type="checkbox"]').first
                        if copy_toggle.is_visible():
                            copy_toggle.click(force=True)
                            print("DEBUG: Clicked 'Send me a copy' toggle.")
                            time.sleep(1)
                        else:
                            text_label = page.locator('text="Send me a copy of my responses"').first
                            if text_label.is_visible():
                                text_label.click(force=True)
                                print("DEBUG: Clicked 'Send me a copy' text label fallback.")
                                time.sleep(1)
                    except Exception as e:
                        print(f"DEBUG: Toggle click note: {e}")

                    print("DEBUG: Clicking submit...")
                    submit_btn.click(force=True)
                    time.sleep(4)
                    
                    print("DEBUG: Form submission completed successfully.")
                    return True

                # 4. Otherwise look for the Next button and click it
                next_btn = page.locator('div[role="button"]:has-text("Next")').first
                if next_btn.is_visible():
                    print("DEBUG: Next button found. Clicking Next...")
                    next_btn.click(force=True)
                    time.sleep(2)
                else:
                    time.sleep(1)

            return True
        except Exception as err:
            print(f"CRITICAL ERROR in Playwright script: {err}")
            raise err
        finally:
            context.close()

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
