name: Keep Streamlit App Awake

on:
  schedule:
    # Every 6 hours (UTC) — comfortably inside Streamlit's 12-hour sleep window.
    - cron: "0 */6 * * *"
  workflow_dispatch: {}   # manual trigger from the Actions tab

jobs:
  ping:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      - name: Install Playwright
        run: |
          pip install playwright
          playwright install --with-deps chromium

      - name: Visit the app and wake it if asleep
        env:
          APP_URL: "https://value-based-lab-score.streamlit.app/"
        run: |
          python - << 'PYEOF'
          import os
          from playwright.sync_api import sync_playwright

          APP_URL = os.environ["APP_URL"]
          WAKE_BUTTON_TEXT = "get this app back up"

          with sync_playwright() as p:
              browser = p.chromium.launch()
              page = browser.new_page()
              print(f"Visiting {APP_URL}")
              page.goto(APP_URL, timeout=60_000)
              page.wait_for_timeout(4_000)
              wake = page.get_by_text(WAKE_BUTTON_TEXT, exact=False)
              if wake.count() > 0:
                  print("App is asleep - clicking the wake-up button")
                  wake.first.click()
                  page.wait_for_timeout(15_000)
                  print("Wake click sent.")
              else:
                  print("App already awake - visit resets its idle timer.")
              browser.close()
          PYEOF
