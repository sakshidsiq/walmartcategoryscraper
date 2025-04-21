from playwright.sync_api import sync_playwright
import json
import random
import time

def human_delay(min_time=2.5, max_time=4.0):
    time.sleep(random.uniform(min_time, max_time))

def scroll_page_like_human(page, steps=5):
    for _ in range(steps):
        page.mouse.wheel(0, random.randint(200, 400))
        human_delay(0.3, 0.6)

def extract_all_categories():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            geolocation={"longitude": -121.4944, "latitude": 38.5816},
            permissions=["geolocation"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        page = context.new_page()
        print("Loading page...")
        page.goto("https://www.walmart.com/cp/protein-fitness/1166769?povid=GlobalNav_rWeb_PharmacyHealthWellness_Wellness_ProteinSupplements", timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        scroll_page_like_human(page)
        human_delay(3, 6)

        print("Extracting __NEXT_DATA__...")
        next_data = page.evaluate("window.__NEXT_DATA__")

        if not next_data:
            print("__NEXT_DATA__ not found.")
            return

        modules = next_data["props"]["pageProps"]["initialTempoData"]["contentLayout"]["modules"]
        all_categories = []

        generic_name_elements = page.query_selector_all(".dn > [link-identifier='Generic Name']")

        for el in generic_name_elements:
            name = el.inner_text().strip()
            url = el.get_attribute("href")
            if name and url:
                all_categories.append({
                    "source": "generic_name_selector",
                    "name": name,
                    "url": url
                })

        for module in modules:
            configs = module.get("configs", {})

            for item in configs.get("categories4x1", []):
                all_categories.append({
                    "source": "categories4x1",
                    "name": item.get("name"),
                    "url": item.get("image", {}).get("clickThrough", {}).get("value")
                })

            for nav in configs.get("navHeaders", []):
                header = nav.get("header", {})
                if header:
                    all_categories.append({
                        "source": "top_nav_header",
                        "name": header.get("linkText"),
                        "url": header.get("clickThrough", {}).get("value")
                    })

                for group in nav.get("categoryGroup", []):
                    category = group.get("category", {})
                    if category:
                        all_categories.append({
                            "source": "categoryGroup",
                            "name": category.get("linkText"),
                            "url": category.get("clickThrough", {}).get("value")
                        })

                    for sub_group in group.get("subCategoryGroup") or []:
                        sub = sub_group.get("subCategory", {})
                        if sub:
                            all_categories.append({
                                "source": "subCategoryGroup",
                                "name": sub.get("linkText"),
                                "url": sub.get("clickThrough", {}).get("value")
                            })

        seen = set()
        unique_categories = []
        for item in all_categories:
            key = (item['name'], item['url'])
            if key not in seen:
                seen.add(key)
                unique_categories.append(item)

        with open("all_walmart_categories.json", "w", encoding="utf-8") as f:
            json.dump(unique_categories, f, indent=2, ensure_ascii=False)

        print(f"Extracted and saved {len(unique_categories)} categories to 'all_walmart_categories.json'")
        browser.close()

if __name__ == "__main__":
    extract_all_categories()
