```python
import os
import time

from flask import Flask, render_template, request, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

FORM_BASE_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSfONIExs2g6a97p9SA0Hb5ef3EHk4ETO5ZiKW6ikoYGSpI_Pg"
    "/viewform"
)

COMPANY_NAME = "BTR DELIVERY"
EMAIL_ADDRESS = "btrdeliverytickets@gmail.com"

DEBUG_DIR = "debug_screenshots"

os.makedirs(DEBUG_DIR, exist_ok=True)


# ============================================================
# SAVE DEBUG SCREENSHOT
# ============================================================

def save_debug_screenshot(page, name):
    try:
        filename = os.path.join(
            DEBUG_DIR,
            "{}_{}.png".format(int(time.time()), name)
        )

        page.screenshot(
            path=filename,
            full_page=True
        )

        print("DEBUG: Screenshot saved -> {}".format(filename))

    except Exception as e:
        print("DEBUG: Could not save screenshot: {}".format(e))


# ============================================================
# BUILD GOOGLE FORM URL
# ============================================================

def build_form_url(falcon_id):
    company = COMPANY_NAME.replace(" ", "+")
    falcon = str(falcon_id).strip()

    return (
        "{}?entry.2078962628={}&entry.141705210={}"
        .format(FORM_BASE_URL, company, falcon)
    )


# ============================================================
# VERIFY GOOGLE FORMS SUBMISSION
# ============================================================

def verify_submission(page):

    print("DEBUG: Verifying Google Forms submission...")

    try:
        page.wait_for_load_state(
            "domcontentloaded",
            timeout=15000
        )
    except Exception:
        pass

    time.sleep(3)

    current_url = page.url

    print("DEBUG: URL after submit: {}".format(current_url))

    confirmation_texts = [
        "Your response has been recorded",
        "Response recorded",
        "Thanks for filling out",
        "Thank you for completing"
    ]

    for text in confirmation_texts:

        try:

            locator = page.get_by_text(
                text,
                exact=False
            )

            count = locator.count()

            if count > 0:

                for i in range(count):

                    try:

                        if locator.nth(i).is_visible():

                            print(
                                "SUCCESS: Google Forms confirmation found: {}".format(
                                    text
                                )
                            )

                            save_debug_screenshot(
                                page,
                                "submission_success"
                            )

                            return True

                    except Exception:
                        pass

        except Exception:
            pass

    if "formResponse" in current_url:

        print(
            "SUCCESS: formResponse URL detected."
        )

        save_debug_screenshot(
            page,
            "submission_success_url"
        )

        return True

    print(
        "ERROR: Google Forms confirmation was NOT detected."
    )

    save_debug_screenshot(
        page,
        "submission_not_confirmed"
    )

    return False


# ============================================================
# MAIN PLAYWRIGHT SUBMISSION
# ============================================================

def run_playwright_submission(
    falcon_id,
    request_type,
    extra_detail=""
):

    if not falcon_id:
        raise Exception(
            "Falcon/Rider ID is required."
        )

    if not request_type:
        raise Exception(
            "Request Type is required."
        )

    print("=" * 70)
    print("STARTING GOOGLE FORMS SUBMISSION")
    print("=" * 70)

    print("DEBUG: Falcon ID = {}".format(falcon_id))
    print("DEBUG: Request Type = {}".format(request_type))
    print("DEBUG: Extra Detail = {}".format(extra_detail))

    form_url = build_form_url(falcon_id)

    print("DEBUG: Form URL = {}".format(form_url))

    browser = None

    with sync_playwright() as p:

        try:

            # ==================================================
            # START CHROMIUM
            # ==================================================

            print("DEBUG: Starting Chromium...")

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage"
                ]
            )

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
                    "AppleWebKit/605.1.15 "
                    "(KHTML, like Gecko) "
                    "Version/17.4.1 Mobile/15E148 Safari/604.1"
                ),
                viewport={
                    "width": 390,
                    "height": 844
                }
            )

            page = context.new_page()

            # ==================================================
            # OPEN GOOGLE FORM
            # ==================================================

            print("DEBUG: Opening Google Form...")

            page.goto(
                form_url,
                timeout=60000,
                wait_until="domcontentloaded"
            )

            time.sleep(3)

            print("DEBUG: Page URL = {}".format(page.url))

            if "docs.google.com/forms" not in page.url:

                save_debug_screenshot(
                    page,
                    "wrong_page"
                )

                raise Exception(
                    "Google Form did not load correctly."
                )

            # ==================================================
            # HANDLE DRAFT MESSAGE
            # ==================================================

            try:

                draft_buttons = page.locator(
                    'div[role="button"]'
                ).filter(
                    has_text="Keep previous"
                )

                if (
                    draft_buttons.count() > 0
                    and draft_buttons.first.is_visible()
                ):

                    print(
                        "DEBUG: Draft message detected."
                    )

                    draft_buttons.first.click(
                        force=True
                    )

                    time.sleep(2)

            except Exception as e:

                print(
                    "DEBUG: Draft handling skipped: {}".format(e)
                )

            # ==================================================
            # EMAIL
            # ==================================================

            print("DEBUG: Checking email field...")

            try:

                email_input = page.locator(
                    'input[type="email"]'
                ).first

                if email_input.count() > 0:

                    if email_input.is_visible():

                        email_input.fill(
                            EMAIL_ADDRESS
                        )

                        email_input.dispatch_event(
                            "input"
                        )

                        email_input.dispatch_event(
                            "change"
                        )

                        print(
                            "DEBUG: Email filled successfully."
                        )

            except Exception as e:

                print(
                    "DEBUG: Email field unavailable: {}".format(e)
                )

            # ==================================================
            # SEND ME A COPY
            # ==================================================

            try:

                copy_label = page.get_by_text(
                    "Send me a copy of my responses",
                    exact=False
                ).first

                if copy_label.count() > 0:

                    if copy_label.is_visible():

                        copy_label.scroll_into_view_if_needed()

                        time.sleep(0.5)

                        copy_label.click(
                            force=True
                        )

                        print(
                            "DEBUG: Send-me-a-copy clicked."
                        )

            except Exception as e:

                print(
                    "DEBUG: Copy option unavailable: {}".format(e)
                )

            # ==================================================
            # REQUEST TYPE
            # ==================================================

            print(
                "DEBUG: Looking for Request Type dropdown..."
            )

            dropdowns = page.locator(
                'div[role="listbox"]'
            )

            print(
                "DEBUG: Dropdown count = {}".format(
                    dropdowns.count()
                )
            )

            request_selected = False

            for i in range(dropdowns.count()):

                try:

                    dropdown = dropdowns.nth(i)

                    if not dropdown.is_visible():
                        continue

                    print(
                        "DEBUG: Checking dropdown {}".format(i)
                    )

                    dropdown.scroll_into_view_if_needed()

                    dropdown.click(
                        force=True
                    )

                    time.sleep(1)

                    option = page.get_by_role(
                        "option",
                        name=request_type,
                        exact=True
                    )

                    if option.count() == 0:

                        option = page.locator(
                            'div[role="option"]'
                        ).filter(
                            has_text=request_type
                        ).first

                    if (
                        option.count() > 0
                        and option.is_visible()
                    ):

                        option.click(
                            force=True
                        )

                        request_selected = True

                        print(
                            "SUCCESS: Request Type selected -> {}".format(
                                request_type
                            )
                        )

                        break

                except Exception as e:

                    print(
                        "DEBUG: Dropdown {} failed: {}".format(
                            i,
                            e
                        )
                    )

            if not request_selected:

                print(
                    "WARNING: Request Type was not selected."
                )

                save_debug_screenshot(
                    page,
                    "request_type_not_selected"
                )

            time.sleep(2)

            # ==================================================
            # FORM PAGE LOOP
            # ==================================================

            max_pages = 10
            page_count = 0

            while page_count < max_pages:

                page_count += 1

                print("=" * 50)
                print(
                    "DEBUG: FORM STEP {}".format(page_count)
                )
                print("=" * 50)

                # ==================================================
                # EXTRA DETAIL
                # ==================================================

                if extra_detail:

                    dropdowns = page.locator(
                        'div[role="listbox"]'
                    )

                    for i in range(dropdowns.count()):

                        try:

                            dropdown = dropdowns.nth(i)

                            if not dropdown.is_visible():
                                continue

                            dropdown_text = dropdown.inner_text()

                            if (
                                "Choose" in dropdown_text
                                or "Select" in dropdown_text
                            ):

                                print(
                                    "DEBUG: Secondary dropdown found."
                                )

                                dropdown.click(
                                    force=True
                                )

                                time.sleep(0.7)

                                option = page.locator(
                                    'div[role="option"]'
                                ).filter(
                                    has_text=extra_detail
                                ).first

                                if (
                                    option.count() > 0
                                    and option.is_visible()
                                ):

                                    option.click(
                                        force=True
                                    )

                                    print(
                                        "DEBUG: Extra detail selected."
                                    )

                                    time.sleep(1)

                                    break

                        except Exception as e:

                            print(
                                "DEBUG: Secondary dropdown error: {}".format(
                                    e
                                )
                            )

                    # ==================================================
                    # TEXT INPUT
                    # ==================================================

                    text_inputs = page.locator(
                        'input[type="text"], textarea'
                    )

                    for i in range(text_inputs.count()):

                        try:

                            inp = text_inputs.nth(i)

                            if not inp.is_visible():
                                continue

                            value = inp.input_value()

                            if not value:

                                inp.fill(
                                    str(extra_detail)
                                )

                                print(
                                    "DEBUG: Extra detail entered."
                                )

                                break

                        except Exception:
                            continue

                # ==================================================
                # FIND SUBMIT
                # ==================================================

                print(
                    "DEBUG: Checking for Submit button..."
                )

                submit_buttons = page.get_by_role(
                    "button",
                    name="Submit",
                    exact=True
                )

                if submit_buttons.count() == 0:

                    submit_buttons = page.locator(
                        'div[role="button"]'
                    ).filter(
                        has_text="Submit"
                    )

                submit_found = False

                for i in range(submit_buttons.count()):

                    try:

                        submit_btn = submit_buttons.nth(i)

                        if submit_btn.is_visible():

                            submit_found = True

                            print(
                                "SUCCESS: Submit button found."
                            )

                            submit_btn.scroll_into_view_if_needed()

                            time.sleep(1)

                            print(
                                "DEBUG: Clicking Submit..."
                            )

                            submit_btn.click(
                                force=True,
                                timeout=15000
                            )

                            print(
                                "DEBUG: Submit clicked."
                            )

                            time.sleep(3)

                            confirmed = verify_submission(
                                page
                            )

                            if confirmed:

                                print("=" * 70)
                                print(
                                    "SUCCESS: GOOGLE FORM SUBMISSION CONFIRMED"
                                )
                                print("=" * 70)

                                return True

                            raise Exception(
                                "Submit was clicked, but Google Forms "
                                "did not show the confirmation page."
                            )

                    except Exception as e:

                        print(
                            "DEBUG: Submit attempt failed: {}".format(
                                e
                            )
                        )

                        if submit_found:
                            raise

                # ==================================================
                # FIND NEXT
                # ==================================================

                print(
                    "DEBUG: Submit not found. Looking for Next..."
                )

                next_buttons = page.get_by_role(
                    "button",
                    name="Next",
                    exact=True
                )

                if next_buttons.count() == 0:

                    next_buttons = page.locator(
                        'div[role="button"]'
                    ).filter(
                        has_text="Next"
                    )

                next_found = False

                for i in range(next_buttons.count()):

                    try:

                        next_btn = next_buttons.nth(i)

                        if next_btn.is_visible():

                            next_found = True

                            print(
                                "DEBUG: Next button found."
                            )

                            next_btn.scroll_into_view_if_needed()

                            time.sleep(0.5)

                            next_btn.click(
                                force=True,
                                timeout=15000
                            )

                            print(
                                "DEBUG: Next clicked."
                            )

                            time.sleep(2)

                            break

                    except Exception as e:

                        print(
                            "DEBUG: Next failed: {}".format(e)
                        )

                if next_found:
                    continue

                # ==================================================
                # NOTHING FOUND
                # ==================================================

                save_debug_screenshot(
                    page,
                    "stuck_step_{}".format(page_count)
                )

                raise Exception(
                    "Could not find Submit or Next button "
                    "on form step {}.".format(page_count)
                )

            raise Exception(
                "Maximum number of form pages exceeded."
            )

        except PlaywrightTimeoutError as e:

            print(
                "TIMEOUT ERROR: {}".format(e)
            )

            try:

                save_debug_screenshot(
                    page,
                    "timeout_error"
                )

            except Exception:
                pass

            raise Exception(
                "Google Forms automation timed out: {}".format(e)
            )

        except Exception as e:

            print(
                "CRITICAL ERROR: {}".format(e)
            )

            try:

                save_debug_screenshot(
                    page,
                    "critical_error"
                )

            except Exception:
                pass

            raise

        finally:

            if browser:

                try:
                    browser.close()

                except Exception:
                    pass


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# SUBMIT API
# ============================================================

@app.route(
    "/submit",
    methods=["POST"]
)
def submit():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "status": "error",
            "message": "No JSON data received."
        }), 400

    falcon_id = str(
        data.get("falcon_id", "")
    ).strip()

    request_type = str(
        data.get("request_type", "")
    ).strip()

    extra_detail = str(
        data.get("extra_detail", "")
    ).strip()

    print("=" * 70)
    print("NEW REQUEST RECEIVED")
    print("=" * 70)

    print(
        "Falcon ID: {}".format(falcon_id)
    )

    print(
        "Request Type: {}".format(request_type)
    )

    print(
        "Extra Detail: {}".format(extra_detail)
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    if not falcon_id:

        return jsonify({
            "status": "error",
            "message": "Falcon/Rider ID is required."
        }), 400

    if not request_type:

        return jsonify({
            "status": "error",
            "message": "Request Type is required."
        }), 400

    # ========================================================
    # SUBMIT
    # ========================================================

    try:

        submitted = run_playwright_submission(
            falcon_id=falcon_id,
            request_type=request_type,
            extra_detail=extra_detail
        )

        if submitted is True:

            return jsonify({
                "status": "success",
                "message": (
                    "Ticket submitted successfully "
                    "and Google Forms confirmation was detected."
                )
            }), 200

        return jsonify({
            "status": "error",
            "message": (
                "Google Forms did not confirm the submission."
            )
        }), 500

    except Exception as e:

        print(
            "SUBMISSION FAILED: {}".format(e)
        )

        return jsonify({
            "status": "error",
            "message": (
                "Ticket was NOT submitted. Reason: {}".format(e)
            )
        }), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5001
        )
    )

    print("=" * 70)
    print("BTR DELIVERY FORM AUTOMATION")
    print("Server starting on port {}".format(port))
    print("=" * 70)

    app.run(
        host="0.0.0.0",
        port=port
    )
```

### Important: Render deployment

Your `requirements.txt` should be:

```text
Flask
gunicorn
playwright
```

And your Render **Start Command** should remain:

```text
gunicorn app:app
```

For Render, you also need Chromium installed during the build. If your current **Build Command** is only:

```text
pip install -r requirements.txt
```

change it to:

```text
pip install -r requirements.txt && playwright install chromium
```

Then push the changes to GitHub and redeploy.

**Do not put anything from the explanation into `app.py`—only the code inside the code block above.**
