from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
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
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )

        page = context.new_page()
        stealth_sync(page)
        print("Navigating...")
        page.goto("https://www.walmart.com/cp/shoes/1045804?povid=GlobalNav_rWeb_ClothingShoesAccessories_Shoes", timeout=60000, wait_until="domcontentloaded")

        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        if "application error" in page.content().lower():
            print("Detected client-side application error. Retrying after 5 seconds...")
            time.sleep(5)
            page.reload()
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            if "application error" in page.content().lower():
                print("Still encountering application error after reload.")
                return
        if "verify" in page.title().lower():
            print("Bot detection triggered. Page title:", page.title())
            return

        scroll_page_like_human(page)
        human_delay(5, 10)

        print("Extracting __NEXT_DATA__...")
        next_data = page.evaluate("window.__NEXT_DATA__")
        if not next_data:
            print("__NEXT_DATA__ not found.")
            return

        initial_data = next_data.get("props", {}).get("pageProps", {}).get("initialTempoData", {})
        modules_1 = initial_data.get("contentLayout", {}).get("modules", [])
        modules_2 = initial_data.get("data", {}).get("contentLayout", {}).get("modules", [])

        modules = modules_1 + modules_2

        generic_name_elements = page.query_selector_all(".dn > [link-identifier='Generic Name']")
        has_nav_headers = any("navHeaders" in m.get("configs", {}) for m in modules)
        has_categories4x1 = any("categories4x1" in m.get("configs", {}) for m in modules)
        has_generic_name_elements = len(generic_name_elements) > 0
        has_shop_by_category = any(
            m.get("configs", {}).get("headingText", "").strip().lower() == "shop by category"
            for m in modules
        )

        if has_nav_headers or has_categories4x1 or has_generic_name_elements:
            template_type = "template_1"
        elif has_shop_by_category:
            template_type = "template_2"
        else:
            template_type = "unknown"

        print(f"Detected layout: {template_type}")
        current_parent_category = "Shoes"
        all_categories = []

        if template_type == "template_1":
            for el in generic_name_elements:
                name = el.inner_text().strip()
                url = el.get_attribute("href")
                if name and url:
                    all_categories.append({
                        "source": "generic_name_selector",
                        "name": name,
                        "url": url,
                        "parent_category_name": current_parent_category
                    })

            for module in modules:
                configs = module.get("configs", {})

                for item in configs.get("categories4x1", []):
                    all_categories.append({
                        "source": "categories4x1",
                        "name": item.get("name"),
                        "url": item.get("image", {}).get("clickThrough", {}).get("value"),
                        "parent_category_name": current_parent_category
                    })

                for nav in configs.get("navHeaders", []):
                    header = nav.get("header", {})
                    header_name = header.get("linkText")
                    if header:
                        all_categories.append({
                            "source": "top_nav_header",
                            "name": header_name,
                            "url": header.get("clickThrough", {}).get("value"),
                            "parent_category_name": current_parent_category
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

        if template_type in ["template_1", "template_2"]:
            for module in modules:
                configs = module.get("configs", {})
                heading = configs.get("headingText", "").strip().lower()

                if heading in ["shop by category", "shop girls' categories", "shop boys' categories", "shop by style"]:
                    rows = configs.get("rows6")
                    if isinstance(rows, list):
                        for row in rows:
                            for category in row.get("categories", []):
                                name = category.get("name")
                                url = category.get("image", {}).get("clickThrough", {}).get("value")
                                if name and url:
                                    all_categories.append({
                                        "source": "shop_by_category",
                                        "name": name,
                                        "url": url,
                                        "parent_category_name": current_parent_category
                                    })

        if template_type == "unknown":
            print("No recognizable category structure found.")
            return

        seen = set()
        unique_categories = []
        for item in all_categories:
            key = (item['name'], item['url'])
            if key not in seen:
                seen.add(key)
                unique_categories.append(item)

        output_data = {
            "template_type": template_type,
            "category_count": len(unique_categories),
            "categories": unique_categories
        }

        with open("all_walmart_categories.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"Extracted and saved {len(unique_categories)} categories to 'all_walmart_categories.json'")
        browser.close()


if __name__ == "__main__":
    extract_all_categories()
