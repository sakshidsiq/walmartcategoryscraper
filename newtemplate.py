from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import json
import random
import time

def human_delay(min_time=2.5, max_time=4.0):
    time.sleep(random.uniform(min_time, max_time))

def scrape_walmart_shop_by_category_data():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        page = context.new_page()
        stealth_sync(page)

        print("Navigating...")
        page.goto(
            'https://www.walmart.com/cp/vision-centers/1078944?povid=GlobalNav_rWeb_PharmacyHealthWellness_VisionCenter_VisionCenter',
            timeout=60000,
            wait_until="domcontentloaded"
        )

        page.wait_for_load_state("domcontentloaded")
        human_delay(3, 5)

        if "application error" in page.content().lower():
            print("Detected client-side application error. Retrying after 5 seconds...")
            time.sleep(5)
            page.reload()
            page.wait_for_load_state("domcontentloaded")
            human_delay(3, 5)

        if "verify" in page.title().lower():
            print("Bot detection triggered. Exiting.")
            browser.close()
            return

        next_data = page.evaluate("window.__NEXT_DATA__")
        if not next_data:
            print("__NEXT_DATA__ not found.")
            return
        
        initial_data = next_data.get("props", {}).get("pageProps", {}).get("initialTempoData", {})
        modules_1 = initial_data.get("contentLayout", {}).get("modules", [])
        modules_2 = initial_data.get("data", {}).get("contentLayout", {}).get("modules", [])
        modules_5 = []
        vision_center_module = next_data.get("props", {}).get("pageProps", {}).get("initialData",{}).get("data", {}).get("contentLayout", {}).get("modules", [])
        if isinstance(vision_center_module, dict):
            modules_5.append(vision_center_module)

        modules = modules_1 + modules_2 + modules_5

        has_shop_by_category = any(
            m.get("configs", {}).get("headingText", "").strip().lower() == "shop by category"
            for m in modules
        )
        has_rows6 = any(isinstance(m.get("configs", {}).get("rows6"), list) for m in modules)

        if has_rows6 or has_shop_by_category:
            template_type = "template_4"
        else :
            template_type = "unknown"

        print(f"Detected layout: {template_type}")
        current_parent_category = "Vision Centre"
        all_categories = []

        for module in modules:
            configs = module.get("configs", {})
            heading = configs.get("headingText", "").strip().lower()

            if heading in [ "shop by category", "shop frames by price", "shop frames by shape"]:
                rows6 = configs.get("rows6")  
                if isinstance(rows6, list):
                    for row in rows6:
                        for category in row.get("categories", []):
                            name = category.get("name")
                            alt_name = category.get("image", {}).get("alt")
                            url = category.get("image", {}).get("clickThrough", {}).get("value")
                            if name and url:
                                all_categories.append({
                                    "source": "shop_by_category",
                                    "name": name,
                                    "url": url,
                                    "alt_name": alt_name,
                                    "parent_category_name": current_parent_category
                                })

            with open('shop_by_category_data.json', 'w', encoding='utf-8') as f:
                json.dump(all_categories, f, ensure_ascii=False, indent=2)

            print(f"Saved {len(all_categories)} items to 'shop_by_category_data.json'.")

            browser.close()

if __name__ == "__main__":
    scrape_walmart_shop_by_category_data()
