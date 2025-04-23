from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import json
import time
import random

def human_delay(min_time=2.5, max_time=4.0):
    time.sleep(random.uniform(min_time, max_time))

def scroll_page_like_human(page, steps=6):
    for _ in range(steps):
        page.mouse.wheel(0, random.randint(300, 500))
        human_delay(0.4, 0.8)

def extract_categories_from_page(page, subcategory_url, parent_category_name):
    print(f"Navigating to {subcategory_url}")
    try:
        page.goto(subcategory_url, timeout=60000)
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        time.sleep(7)

        if page.locator("text=Robot or human?").is_visible():
            print("🤖 Bot verification triggered.")
            try:
                button = page.locator("text=PRESS & HOLD")
                button.wait_for(timeout=5000)
                box = button.bounding_box()
                if box:
                    x = box["x"] + box["width"] / 2
                    y = box["y"] + box["height"] / 2
                    page.mouse.move(x, y)
                    page.mouse.down()
                    time.sleep(4.5)
                    page.mouse.up()
                    time.sleep(6)
                else:
                    return []
            except Exception as e:
                print(f"❌ Bot challenge failed: {e}")
                return []

        scroll_page_like_human(page)
        human_delay(3, 6)
        next_data = page.evaluate("window.__NEXT_DATA__")
        if not next_data:
            print("No NEXT_DATA found.")
            return []

        initial_data = next_data.get("props", {}).get("pageProps", {}).get("initialTempoData", {})
        modules = (
            initial_data.get("contentLayout", {}).get("modules")
            or initial_data.get("data", {}).get("contentLayout", {}).get("modules")
            or []
        )

        generic_name_elements = page.query_selector_all(".dn > [link-identifier='Generic Name']")
        has_nav_headers = any("navHeaders" in m.get("configs", {}) for m in modules)
        has_categories4x1 = any("categories4x1" in m.get("configs", {}) for m in modules)
        has_generic_name_elements = len(generic_name_elements) > 0
        has_shop_by_category = any(m.get("configs", {}).get("headingText", "").strip().lower() == "shop by category" for m in modules)

        if has_nav_headers or has_categories4x1 or has_generic_name_elements:
            template_type = "template_1"
        elif has_shop_by_category:
            template_type = "template_2"
        else:
            return []

        categories = []
        if template_type == "template_1":
            for el in generic_name_elements:
                name = el.inner_text().strip()
                url = el.get_attribute("href")
                if name and url:
                    categories.append({
                        "name": name,
                        "url": url,
                        "parent_category": parent_category_name,
                        "source": "generic_name_selector"
                    })

            for module in modules:
                configs = module.get("configs", {})
                for item in configs.get("categories4x1", []):
                    categories.append({
                        "name": item.get("name"),
                        "url": item.get("image", {}).get("clickThrough", {}).get("value"),
                        "parent_category": parent_category_name,
                        "source": "categories4x1"
                    })

                for nav in configs.get("navHeaders", []):
                    header = nav.get("header", {})
                    header_name = header.get("linkText")
                    if header_name:
                        categories.append({
                            "name": header_name,
                            "url": header.get("clickThrough", {}).get("value"),
                            "parent_category": parent_category_name,
                            "source": "top_nav_header"
                        })

                    for group in nav.get("categoryGroup", []):
                        category = group.get("category", {})
                        name = category.get("linkText")
                        url = category.get("clickThrough", {}).get("value")
                        if name and url:
                            categories.append({
                                "name": name,
                                "url": url,
                                "parent_category": header_name,
                                "source": "categoryGroup"
                            })

                        for sub_group in group.get("subCategoryGroup") or []:
                            sub = sub_group.get("subCategory", {})
                            sub_name = sub.get("linkText")
                            sub_url = sub.get("clickThrough", {}).get("value")
                            if sub_name and sub_url:
                                categories.append({
                                    "name": sub_name,
                                    "url": sub_url,
                                    "parent_category": name,
                                    "source": "subCategoryGroup"
                                })

        if template_type in ["template_1", "template_2"]:
            for module in modules:
                configs = module.get("configs", {})
                if configs.get("headingText", "").strip().lower() == "shop by category":
                    for row in configs.get("rows6", []):
                        for cat in row.get("categories", []):
                            name = cat.get("name")
                            url = cat.get("image", {}).get("clickThrough", {}).get("value")
                            if name and url:
                                categories.append({
                                    "name": name,
                                    "url": url,
                                    "parent_category": parent_category_name,
                                    "source": "shop_by_category"
                                })
        return categories

    except Exception as e:
        print(f"Error while scraping {subcategory_url}: {e}")
        return []

def scrape_all_categories():
    all_data = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.walmart.com/")
        time.sleep(7)

        print("🟡 Waiting for page to load...")
        page.wait_for_load_state("load", timeout=30000)  
        time.sleep(7)

        print("🟡 Clicking hamburger menu...")
        try:
            page.wait_for_selector("button[aria-label='Menu']", timeout=15000)
            page.click("button[aria-label='Menu']")
        except:
            page.evaluate("document.querySelector('button[aria-label=\"Menu\"]').click()")
        time.sleep(7)

        print("🟡 Clicking 'Departments'...")
        page.wait_for_selector("span[data-testid='mobile-menu-Departments']", timeout=15000)
        page.click("span[data-testid='mobile-menu-Departments']")

        print("🟢 Waiting for departments list...")
        page.wait_for_selector("ul.list.pa0.ph4.ma0.overflow-auto > li", timeout=15000)
        time.sleep(7)
        items = page.locator("ul.list.pa0.ph4.ma0.overflow-auto > li > button > span.flex-auto")
        departments = items.all_text_contents()

        for i, department in enumerate(departments):
            department_name = department.strip()
            print(f"\n➡️ Department: {department_name}")
            try:
                items.nth(i).click()
                time.sleep(4)

                subcategories = page.locator("ul.list.pa0.ph4.ma0.overflow-auto > li > a")
                sub_links = subcategories.all()

                for sub in sub_links:
                    sub_name = sub.inner_text().strip()
                    sub_url = sub.get_attribute("href")
                    full_url = sub_url if sub_url.startswith("http") else f"https://www.walmart.com{sub_url}"
                    print(f"  ↪ Subcategory: {sub_name} → {full_url}")

                    all_data.append({
                        "name": sub_name,
                        "url": full_url,
                        "parent_category": department_name,
                        "source": "departments"
                    })

                    categories = extract_categories_from_page(page, full_url, sub_name)
                    all_data.extend(categories)

                page.click("button#back-button")
                time.sleep(4)

            except Exception as e:
                print(f"Failed to process department '{department}': {e}")
                continue

        with open("all_categories.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)

        print("Data saved to all_categories.json")
        browser.close()

if __name__ == "__main__":
    scrape_all_categories()
