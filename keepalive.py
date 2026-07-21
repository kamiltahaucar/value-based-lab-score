"""
Visits a Streamlit Community Cloud app with a real (headless) browser so the
visit counts as traffic. If the app is asleep, it clicks the
"Yes, get this app back up!" button to wake it.
"""

import os
import sys

from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL", "https://value-based-lab-score.streamlit.app/")
WAKE_BUTTON_TEXT = "get this app back up"   # substring match, case-insensitive


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        print(f"Visiting {APP_URL}")
        page.goto(APP_URL, timeout=60_000)
        page.wait_for_timeout(4_000)  # let the page settle

        wake_button = page.get_by_text(WAKE_BUTTON_TEXT, exact=False)
        if wake_button.count() > 0:
            print("App is asleep — clicking the wake-up button")
            wake_button.first.click()
            page.wait_for_timeout(15_000)  # give it time to boot
            print("Wake click sent.")
        else:
            print("App was already awake — visit alone resets its idle timer.")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
