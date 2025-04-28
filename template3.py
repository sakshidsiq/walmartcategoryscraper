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
            'https://www.walmart.com/browse/health/pain-relievers/976760_6972993?povid=GlobalNav_rWeb_PharmacyHealthWellness_HealthCare_PainManagement',
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

        script_tag = page.query_selector('script#__NEXT_DATA__')
        if script_tag:
            page_data = json.loads(script_tag.inner_text())

            pills_data = page_data['props']['pageProps']['initialData']['moduleDataByZone']['pillsTopZone']['configs']['pillsV2']

            all_pills = []
            for pill in pills_data:
                pill_info = {
                    "title": pill['title'],
                    "url": pill['url']
                }
                all_pills.append(pill_info)

            with open('pills_data.json', 'w', encoding='utf-8') as f:
                json.dump(all_pills, f, ensure_ascii=False, indent=2)

            print(f"Saved {len(all_pills)} items to 'pills_data.json'.")
        else:
            print("Unable to find __NEXT_DATA__ script tag.")

        browser.close()

if __name__ == "__main__":
    scrape_walmart_pills_data()
