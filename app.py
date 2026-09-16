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
# DEBUG SCREENSHOT
# ============================================================

def save_debug_screenshot(page, name):
    try:
        filename = os.path.join(
            DEBUG_DIR,
            f"{int(time.time())}_{name}.png"
        )

        page.screenshot(
            path=filename,
            full_page=True
        )

        print(f"DEBUG: Screenshot saved -> {filename}")

    except Exception as e:
        print(f"DEBUG: Could not save screenshot: {e}")


# ============================================================
# GET FORM URL
# ============================================================

def build_form_url(falcon_id):
    return (
        f"{FORM_BASE_URL}?"
        f"entry.2078962628={COMPANY_NAME.replace(' ', '+')}"
        f"&entry.141705210={falcon_id}"
    )


# ============================================================
# CHECK IF PAGE HAS GOOGLE FORM CONFIRMATION
# ============================================================

def verify_submission(page):

    print("DEBUG: Verifying Google Forms submission...")

    # Give Google Forms time to load the confirmation page
    try:
        page.wait_for_load_state(
            "domcontentloaded",
            timeout=15000
        )
    except Exception:
        pass

    time.sleep(2)

    current_url = page.url

    print(f"DEBUG: Current URL after submit: {current_url}")

    # Google Forms confirmation pages normally contain
    # "Your response has been recorded."
    confirmation_texts = [
        "Your response has been recorded",
        "Response recorded",
        "Thanks for filling out",
        "Thank you for completing",
    ]

    for text in confirmation_texts:

        try:
            locator = page.get_by_text(
                text,
                exact=False
            )

            if locator.count() > 0:

                for i in range(locator.count()):

                    try:
                        if locator.nth(i).is_visible():

                            print(
                                f"SUCCESS: Google Forms confirmation found: {text}"
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

    # Additional URL check
    if "formResponse" in current_url:

        print(
            "SUCCESS: Google Forms formResponse URL detected."
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
# PLAYWRIGHT SUBMISSION
# ============================================================

def run_playwright_submission(
    falcon_id,
    request_type,
    extra_detail=""
):

    if not falcon_id:
        raise Exception("Falcon/Rider ID is required.")

    if not request_type:
        raise Exception("Request Type is required.")

    print("=" * 70)
    print("STARTING GOOGLE FORMS SUBMISSION")
    print("=" * 70)

    print(f"DEBUG: Falcon ID    = {falcon_id}")
    print(f"DEBUG: Request Type = {request_type}")
    print(f"DEBUG: Extra Detail = {extra_detail}")

    form_url = build_form_url(falcon_id)

    print(f"DEBUG: Form URL = {form_url}")

    with sync_playwright() as p:

        browser = None

        try:

            # ------------------------------------------------
            # LAUNCH BROWSER
            # ------------------------------------------------

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
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

            # ------------------------------------------------
            # NAVIGATE TO GOOGLE FORM
            # ------------------------------------------------

            print("DEBUG: Opening Google Form...")

            page.goto(
                form_url,
                timeout=60000,
                wait_until="domcontentloaded"
            )

            time.sleep(3)

            print(f"DEBUG: Page loaded: {page.url}")

            # ------------------------------------------------
            # CHECK THAT GOOGLE FORM LOADED
            # ------------------------------------------------

            if "docs.google.com/forms" not in page.url:

                save_debug_screenshot(
                    page,
                    "wrong_page"
                )

                raise Exception(
                    "Google Form did not load correctly."
                )

            # ------------------------------------------------
            # HANDLE GOOGLE FORMS DRAFT
            # ------------------------------------------------

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
                        "DEBUG: Google Forms draft detected."
                    )

                    draft_buttons.first.click(
                        force=True
                    )

                    time.sleep(2)

            except Exception as e:

                print(
                    f"DEBUG: Draft handling skipped: {e}"
                )

            # ------------------------------------------------
            # COMPANY NAME
            # ------------------------------------------------

            print("DEBUG: Checking Company Name...")

            try:

                company_inputs = page.locator(
                    'input[type="text"]'
                )

                for i in range(company_inputs.count()):

                    inp = company_inputs.nth(i)

                    if not inp.is_visible():
                        continue

                    try:
                        value = inp.input_value()

                        if value == COMPANY_NAME:
                            print(
                                "DEBUG: Company name already filled."
                            )
                            break

                    except Exception:
                        pass

            except Exception as e:

                print(
                    f"DEBUG: Company field check: {e}"
                )

            # ------------------------------------------------
            # EMAIL
            # ------------------------------------------------

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
                    f"DEBUG: Email field not available: {e}"
                )

            # ------------------------------------------------
            # SEND ME A COPY
            # ------------------------------------------------

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
                            "DEBUG: Send-me-a-copy option clicked."
                        )

            except Exception as e:

                print(
                    f"DEBUG: Copy checkbox not available: {e}"
                )

            # ------------------------------------------------
            # REQUEST TYPE
            # ------------------------------------------------

            print(
                "DEBUG: Looking for Request Type dropdown..."
            )

            dropdowns = page.locator(
                'div[role="listbox"]'
            )

            print(
                f"DEBUG: Dropdown count = {dropdowns.count()}"
            )

            request_selected = False

            for i in range(dropdowns.count()):

                dropdown = dropdowns.nth(i)

                try:

                    if not dropdown.is_visible():
                        continue

                    print(
                        f"DEBUG: Checking dropdown {i}"
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
                            f"SUCCESS: Request Type selected -> {request_type}"
                        )

                        break

                except Exception as e:

                    print(
                        f"DEBUG: Dropdown {i} failed: {e}"
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

            # ------------------------------------------------
            # MULTI-PAGE FORM
            # ------------------------------------------------

            max_pages = 10
            page_count = 0

            while page_count < max_pages:

                page_count += 1

                print("=" * 50)
                print(
                    f"DEBUG: FORM PAGE / STEP {page_count}"
                )
                print("=" * 50)

                # --------------------------------------------
                # EXTRA DETAIL
                # --------------------------------------------

                if extra_detail:

                    # First try dropdowns
                    dropdowns = page.locator(
                        'div[role="listbox"]'
                    )

                    for i in range(dropdowns.count()):

                        try:

                            dropdown = dropdowns.nth(i)

                            if not dropdown.is_visible():
                                continue

                            text = dropdown.inner_text()

                            if (
                                "Choose" in text
                                or "Select" in text
                            ):

                                print(
                                    "DEBUG: Found secondary dropdown."
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
                                f"DEBUG: Secondary dropdown error: {e}"
                            )

                    # ----------------------------------------
                    # TEXT INPUTS
                    # ----------------------------------------

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

                # --------------------------------------------
                # LOOK FOR SUBMIT
                # --------------------------------------------

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
                                "SUCCESS: Real Submit button found."
                            )

                            submit_btn.scroll_into_view_if_needed()

                            time.sleep(1)

                            # --------------------------------
                            # CLICK SUBMIT
                            # --------------------------------

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

                            # --------------------------------
                            # VERIFY SUBMISSION
                            # --------------------------------

                            if verify_submission(page):

                                print(
                                    "================================================"
                                )
                                print(
                                    "SUCCESS: FORM ACTUALLY SUBMITTED"
                                )
                                print(
                                    "================================================"
                                )

                                return True

                            else:

                                raise Exception(
                                    "Submit button was clicked, "
                                    "but Google Forms did not show "
                                    "the confirmation page. "
                                    "The response was NOT confirmed."
                                )

                    except Exception as e:

                        print(
                            f"DEBUG: Submit attempt failed: {e}"
                        )

                        if submit_found:
                            raise

                # --------------------------------------------
                # NEXT BUTTON
                # --------------------------------------------

                print(
                    "DEBUG: No Submit button found."
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
                            f"DEBUG: Next button failed: {e}"
                        )

                if next_found:
                    continue

                # --------------------------------------------
                # NOTHING FOUND
                # --------------------------------------------

                save_debug_screenshot(
                    page,
                    f"stuck_step_{page_count}"
                )

                raise Exception(
                    "Could not find either Submit or Next "
                    f"button on form step {page_count}."
                )

            raise Exception(
                "Maximum number of form pages exceeded."
            )

        except PlaywrightTimeoutError as e:

            print(
                f"TIMEOUT ERROR: {e}"
            )

            try:
                save_debug_screenshot(
                    page,
                    "timeout_error"
                )
            except Exception:
                pass

            raise Exception(
                f"Google Forms automation timed out: {e}"
            )

        except Exception as e:

            print(
                f"CRITICAL ERROR: {e}"
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
# SUBMIT ENDPOINT
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

    print(f"Falcon ID: {falcon_id}")
    print(f"Request Type: {request_type}")
    print(f"Extra Detail: {extra_detail}")

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # ACTUAL SUBMISSION
    # --------------------------------------------------------

    try:

        submitted = run_playwright_submission(
            falcon_id=falcon_id,
            request_type=request_type,
            extra_detail=extra_detail
        )

        # VERY IMPORTANT:
        # Never return success unless the function
        # explicitly confirms the Google Forms page.

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
                "The ticket was not confirmed by Google Forms."
            )
        }), 500

    except Exception as e:

        print(
            f"SUBMISSION FAILED: {e}"
        )

        return jsonify({
            "status": "error",
            "message": (
                "Ticket was NOT submitted. "
                f"Reason: {str(e)}"
            )
        }), 500


# ============================================================
# RUN SERVER
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
    print(f"Server starting on port {port}")
    print("=" * 70)

    app.run(
        host="0.0.0.0",
        port=port
    )
```

### What changed

The most important change is this:

**Before:**

```text
Click Submit
↓
wait 4 seconds
↓
SUCCESS
```

**Now:**

```text
Click Submit
↓
wait for Google Forms
↓
check confirmation page
↓
confirmation found?
   ├── YES → SUCCESS
   └── NO  → ERROR
```

So your webpage **cannot say "Ticket submitted successfully" simply because the Submit button was clicked.**

I also removed the dangerous behavior where this situation:

```text
No Submit
No Next
↓
return True
```

was being interpreted as success.

### One thing I need you to check

Your Google Form may have **conditional sections** depending on `request_type`. In that case, the `extra_detail` handling in the current script may still need to be adjusted to your exact questions.

If this updated version still doesn't submit, **don't change anything else**. Send me the new terminal/Render log beginning with:

```text
NEW REQUEST RECEIVED
```

and especially the lines around:

```text
DEBUG: FORM PAGE / STEP
DEBUG: Checking for Submit button
```

The new version also creates a `debug_screenshots` folder. The screenshot generated when it gets stuck will show us **exactly what Google Forms displayed to Playwright**.
