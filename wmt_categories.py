from playwright.sync_api import sync_playwright
import json
import time

def scrape_walmart_brands():
    data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)  
        page = browser.new_page()

        print("Visiting Vitamins & Supplements page...")
        page.goto("https://www.walmart.com/cp/vitamins-supplements/1005863", timeout=60000)
        page.wait_for_load_state("networkidle")
        time.sleep(5)

        print("Clicking 'Brands' tab...")
        try:
            brands_tab = page.locator("//button[text()='Brands']")
            brands_tab.wait_for(state="visible", timeout=10000)
            brands_tab.click()
            time.sleep(3)
        except Exception as e:
            print(f"Failed to click 'Brands' tab: {e}")
            browser.close()
            return

        print("Locating brand containers...")
        containers = page.locator("div.w_aoqv")
        total = containers.count()
        print(f"Found {total} containers")

        for j in range(total):
            try:
                container = containers.nth(j)
                title_elem = container.locator("h2.f5").first

                if title_elem.count() == 0:
                    print(f"Skipping container #{j} - No title")
                    continue

                subcategory_name = title_elem.inner_text(timeout=2000).strip()
                anchor = container.locator("a").first
                subcategory_url = anchor.get_attribute("href") if anchor else None

                print(f"Subcategory: {subcategory_name} ({subcategory_url})")

                sub_list = []
                sub_links = container.locator("li a.f6")
                for k in range(sub_links.count()):
                    try:
                        sub = sub_links.nth(k)
                        name = sub.inner_text(timeout=2000).strip()
                        href = sub.get_attribute("href")
                        print(f"  {name}: {href}")
                        sub_list.append({
                            "name": name,
                            "url": href
                        })
                    except Exception as sub_e:
                        print(f"Skipping broken link: {sub_e}")
                        continue

                data.append({
                    "subcategory": subcategory_name,
                    "url": subcategory_url,
                    "children": sub_list
                })

            except Exception as e:
                print(f"Failed to parse container #{j}: {e}")
                continue

        browser.close()

    with open("subcategories.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Data saved to subcategories.json")

if __name__ == "__main__":
    scrape_walmart_brands()
