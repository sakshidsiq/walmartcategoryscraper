from playwright.sync_api import sync_playwright
import json
import time

def scrape_walmart_departments():
    data = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page()
        page.goto("https://www.walmart.com/", timeout=60000)
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

        print("Departments found:")
        for i, department in enumerate(departments):
            department_name = department.strip()
            print(f"• {department_name}")
            print(f"🟡 Clicking department: {department_name}")
            try:
                    items.nth(i).click()
                    time.sleep(3)

                    page.wait_for_selector("ul.list.pa0.ph4.ma0.overflow-auto > li > a", timeout=15000)
                    time.sleep(1)

                    subcategories = page.locator("ul.list.pa0.ph4.ma0.overflow-auto > li > a")
                    sub_links = subcategories.all()

                    sub_list = []
                    for sub in sub_links:
                        name = sub.inner_text().strip()
                        href = sub.get_attribute("href")
                        sub_list.append({
                            "name": name,
                            "url": href
                        })

                    data.append({
                        "department": department_name,
                        "subcategories": sub_list
                    })

                    page.click("button#back-button")
                    time.sleep(3)

            except Exception as e:
                print(f"Failed on {department_name}: {e}")
                continue

        browser.close()

    with open("new_departments.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Data saved to new_departments.json")

if __name__ == "__main__":
    scrape_walmart_departments()