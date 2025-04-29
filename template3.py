from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import json
import random
import time

def human_delay(min_time=2.5, max_time=4.0):
    time.sleep(random.uniform(min_time, max_time))

def scrape_walmart_pills_data():
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
            'https://www.walmart.com/shop/deals/wellness-and-personal-care/Vitamins-and-supplements?povid=wellness_multivitamins_vitamindeals_rweb',
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
        modules_3 = []
        pills_top_zone = next_data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("moduleDataByZone", {}).get("pillsTopZone")
        if isinstance(pills_top_zone, dict):
            modules_3.append(pills_top_zone)
        modules_4 = []
        chip_module = next_data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("contentLayout", {}).get("modules", [])[2]
        if isinstance(chip_module, dict):
            modules_4.append(chip_module)

        modules = modules_1 + modules_2 + modules_3 + modules_4

        has_pillsV2 = any(isinstance(m.get("configs", {}).get("pillsV2"), list) for m in modules)

        if has_pillsV2:
            template_type = "template_3"
        else :
            template_type = "unknown"

        print(f"Detected layout: {template_type}")
        all_pills = []

        for module in modules:
            configs = module.get("configs", {})
            pillsV2 = configs.get("pillsV2")
            if isinstance(pillsV2, list): 
                for pill in pillsV2:
                    pill_info = {
                        "name": pill['title'],
                        "url": pill['url'],
                        "source": "shop_by_category",
                        "parent_category_name": "vitamin deals"
                    }
                    all_pills.append(pill_info)

        with open('pills_data.json', 'w', encoding='utf-8') as f:
            json.dump(all_pills, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(all_pills)} items to 'pills_data.json'.")

        browser.close()

if __name__ == "__main__":
    scrape_walmart_pills_data()
