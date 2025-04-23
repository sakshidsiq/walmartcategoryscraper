from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import json
import time

def extract_pills_module_data():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        # context = new_context(

        # )

        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/Los_Angeles",
            bypass_csp=True,
            viewport={"width": 1280, "height": 800}
        )
        stealth_sync(page)

        print("Navigating to Walmart page...")
        page.goto(
            "https://www.walmart.com/shop/clothing-and-accessories/new-arrivals",
            # timeout=60000,
            wait_until="networkidle"
        )

        time.sleep(5)

        if "application error" in page.content().lower():
            print("Application error detected. Exiting.")
            page.screenshot(path="error_screenshot.png")
            browser.close()
            return

        print("🔍 Extracting __NEXT_DATA__ JSON...")
        next_data = page.evaluate("window.__NEXT_DATA__")
        if not next_data:
            print("Could not find __NEXT_DATA__.")
            browser.close()
            return

        modules = (
            next_data.get("props", {})
            .get("pageProps", {})
            .get("initialTempoData", {})
            .get("contentLayout", {})
            .get("modules", [])
        )

        pills_data = []
        for module in modules:
            if module.get("type") == "PillsModule":
                for pill in module.get("configs", {}).get("pillsV2", []):
                    pills_data.append({
                        "title": pill.get("title"),
                        "url": pill.get("url"),
                        "image": pill.get("image", {}).get("src")
                    })

        print(f"Extracted {len(pills_data)} pills")
        print(json.dumps(pills_data, indent=2))

        with open("walmart_pills_categories.json", "w", encoding="utf-8") as f:
            json.dump(pills_data, f, indent=2, ensure_ascii=False)

        browser.close()


if __name__ == "__main__":
    extract_pills_module_data()
