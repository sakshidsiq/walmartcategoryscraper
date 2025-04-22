from playwright.sync_api import sync_playwright
import json
import random
import time

def human_delay(min_time=2.5, max_time=4.0):
    time.sleep(random.uniform(min_time, max_time))

def scroll_page_like_human(page, steps=6):
    for _ in range(steps):
        page.mouse.wheel(0, random.randint(300, 500))
        human_delay(0.4, 0.8)

def extract_all_categories():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            geolocation={"longitude": -121.4944, "latitude": 38.5816},
            permissions=["geolocation"]
        )

        page = context.new_page()
        print("Navigating...")
        page.goto("https://www.walmart.com/cp/digestive-health/1396434?povid=GlobalNav_rWeb_PharmacyHealthWellness_Wellness_DigestiveHealth", timeout=60000, wait_until="domcontentloaded")

        page.wait_for_load_state("domcontentloaded")
        if "verify" in page.title().lower():
            print("🚨 Bot detection triggered. Page title:", page.title())
            page.screenshot(path="bot_detected.png")
            return

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

        current_parent_category = "Digestive Health & Wellness"

        for el in generic_name_elements:
            name = el.inner_text().strip()
            url = el.get_attribute("href")
            if name and url:
                all_categories.append({
                    "source": "generic_name_selector",
                    "name": name,
                    "url": url,
                    "parent_category_name" : current_parent_category
                })

        for module in modules:
            configs = module.get("configs", {})

            for item in configs.get("categories4x1", []):
                all_categories.append({
                    "source": "categories4x1",
                    "name": item.get("name"),
                    "url": item.get("image", {}).get("clickThrough", {}).get("value"),
                    "parent_category_name" : current_parent_category
                })


            for nav in configs.get("navHeaders", []):
                header = nav.get("header", {})
                header_name = header.get("linkText")
                if header:
                    all_categories.append({
                        "source": "top_nav_header",
                        "name": header_name,
                        "url": header.get("clickThrough", {}).get("value"),
                        "parent_category_name" : current_parent_category
                    })

                parent_category = header_name

                for group in nav.get("categoryGroup", []):
                    category = group.get("category", {})
                    category_name = category.get("linkText")
                    category_url = category.get("clickThrough", {}).get("value")

                    if category_name and category_url:
                        all_categories.append({
                            "source": "categoryGroup",
                            "name": category_name,
                            "url": category_url,
                            "parent_category": parent_category
                        })

                    subcategory_parent = category_name  

                    for sub_group in group.get("subCategoryGroup") or []:
                        sub = sub_group.get("subCategory", {})
                        if sub:
                            sub_name = sub.get("linkText")
                            sub_url = sub.get("clickThrough", {}).get("value")

                            if sub_name and sub_url:
                                all_categories.append({
                                    "source": "subCategoryGroup",
                                    "name": sub_name,
                                    "url": sub_url,
                                    "parent_category": subcategory_parent  
                                })
        print("Extracting Shop by Category section...")
        shop_sections = page.query_selector_all("section")
        for section in shop_sections:
            h2 = section.query_selector("h2.w_kV33.w_Sl3f.w_mvVb.ma0.undefined.lh-title")
            if h2:
                h2_text = h2.inner_text().strip().lower()
                print("🧩 Found H2 text:", h2_text)
                if "category" in h2_text:
                    grid_elements = section.query_selector_all("[id*='Hubspokes4orNxMGrid']>.w_aoqv.w_wRee.content-between.flex-grow-0")
                    for el in grid_elements:
                        cat_name = el.inner_text().strip()
                        cat_url = el.get_attribute("href")
                        if cat_name and cat_url:
                            all_categories.append({
                                "source": "shop_by_category_section",
                                "name": cat_name,
                                "url": cat_url,
                                "parent_category_name": current_parent_category
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
