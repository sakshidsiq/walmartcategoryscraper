from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import json
import random
import time
import pandas as pd



def human_delay(min_time=2.5, max_time=4.0):
    time.sleep(random.uniform(min_time, max_time))

def scroll_page_like_human(page, steps=6):
    for _ in range(steps):
        page.mouse.wheel(0, random.randint(300, 500))
        human_delay(0.4, 0.8)

def extract_all_categories(subcat_name, subcat_url, department_name):
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
        page.goto(subcat_url, timeout=60000, wait_until="domcontentloaded")

        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        failed_urls = []

        if "application error" in page.content().lower():
            print("Detected client-side application error. Retrying after 5 seconds...")
            time.sleep(5)
            page.reload()
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            if "application error" in page.content().lower():
                print(f"[ERROR] Application error on page: {subcat_url}")
                failed_urls.append({"url": subcat_url, "subcategory": subcat_name, "department": department_name, "reason": "application error"})
                return
            
        if "verify" in page.title().lower():
            print(f"[ERROR] Bot verification required: {subcat_url}")
            failed_urls.append({"url": subcat_url, "subcategory": subcat_name, "department": department_name, "reason": "bot verification"})
            return

        scroll_page_like_human(page)
        human_delay(5, 10)

        print("Extracting __NEXT_DATA__...")
        next_data = page.evaluate("window.__NEXT_DATA__")
        if not next_data:
            print(f"[ERROR] __NEXT_DATA__ not found for {subcat_url}")
            failed_urls.append({"url": subcat_url, "subcategory": subcat_name, "department": department_name, "reason": "__NEXT_DATA__ missing"})
            return
        

        initial_data = next_data.get("props", {}).get("pageProps", {}).get("initialTempoData", {})
        modules_1 = initial_data.get("contentLayout", {}).get("modules", [])
        modules_2 = initial_data.get("data", {}).get("contentLayout", {}).get("modules", [])
        modules_3 = []
        pills_top_zone = next_data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("moduleDataByZone", {}).get("pillsTopZone")
        if isinstance(pills_top_zone, dict):
            modules_3.append(pills_top_zone)
        # modules_4 = []
        # chip_module = next_data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("contentLayout", {}).get("modules", [])
        # module_index = chip_module[2] if len(chip_module)>2 else None
        # if isinstance(chip_module[2], dict):
        #     modules_4.append(module_index)

        module_detected = None
        if modules_1:
            module_detected = modules_1
            print("Detected module source: modules_1 (initialTempoData > contentLayout)")
        elif modules_2:
            module_detected = modules_2
            print("Detected module source: modules_2 (initialTempoData > data > contentLayout)")
        elif modules_3:
            module_detected = modules_3
            print("Detected module source: modules_3 (moduleDataByZone > pillsTopZone)")
        elif True:
            chip_module = next_data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("contentLayout", {}).get("modules", [])
            if len(chip_module) > 2 and isinstance(chip_module[2], dict):
                module_detected = [chip_module[2]]  
                print("Detected module source: modules_4 (contentLayout index 2)")
            else:
                print(f"[ERROR] No module detected in {subcat_url}")
                failed_urls.append({"url": subcat_url, "subcategory": subcat_name, "department": department_name, "reason": "no modules found"})
                return

        print(f"Modules detected: {len(module_detected)}")

        modules = module_detected

        generic_name_elements = page.query_selector_all(".dn > [link-identifier='Generic Name']")
        has_nav_headers = any("navHeaders" in m.get("configs", {}) for m in modules)
        has_categories4x1 = any("categories4x1" in m.get("configs", {}) for m in modules)
        has_categories4x4 = any(
            any("categories4x4" in row for row in m.get("configs", {}).get("rows", []))
            for m in modules
        )
        has_generic_name_elements = len(generic_name_elements) > 0
        has_shop_by_category = any(
            m.get("configs", {}).get("headingText", "").strip().lower() == "shop by category"
            for m in modules
        )
        has_rows6 = any(isinstance(m.get("configs", {}).get("rows6"), list) for m in modules)
        has_rows4 = any(isinstance(m.get("configs", {}).get("rows4"), list) for m in modules)
        has_pillsV2 = any(isinstance(m.get("configs", {}).get("pillsV2"), list) for m in modules)

        if has_nav_headers or has_categories4x1 or has_generic_name_elements or has_categories4x4:
            template_type = "template_1"
        elif has_shop_by_category or has_rows4 or has_rows6:
            template_type = "template_2"
        elif has_pillsV2:
            template_type = "template_3"
        else:
            template_type = "unknown"
        
        print(f"Detected layout: {template_type}")
        current_parent_category = subcat_name
        all_categories = []
        all_categories.append({
            "source": "departments",
            "name": subcat_name,
            "parent_category_name": department_name,
            "source_url": subcat_url
        })

        if template_type == "template_1":
            for el in generic_name_elements:
                name = el.inner_text().strip()
                url = el.get_attribute("href")
                if name and url:
                    all_categories.append({
                        "source": "generic_name_selector",
                        "name": name,
                        "url": url,
                        "parent_category_name": current_parent_category,
                        "source_url": subcat_url
                    })

            for module in modules:
                configs = module.get("configs", {})

                for item in configs.get("categories4x1", []):
                    all_categories.append({
                        "source": "categories4x1",
                        "name": item.get("name"),
                        "url": item.get("image", {}).get("clickThrough", {}).get("value"),
                        "parent_category_name": current_parent_category,
                        "source_url": subcat_url
                    })

                for row in configs.get("rows", []):
                    for item in row.get("categories4x4", []):
                        all_categories.append({
                            "source": "categories4x4",
                            "name": item.get("name"),
                            "url": item.get("image", {}).get("clickThrough", {}).get("value"),
                            "parent_category_name": current_parent_category,
                            "source_url": subcat_url
                        })

                for nav in configs.get("navHeaders", []):
                    header = nav.get("header", {})
                    header_name = header.get("linkText")
                    if header:
                        all_categories.append({
                            "source": "top_nav_header",
                            "name": header_name,
                            "url": header.get("clickThrough", {}).get("value"),
                            "parent_category_name": current_parent_category,
                            "source_url": subcat_url
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
                                "parent_category_name": parent_category,
                                "ancestor_name": current_parent_category,
                                "source_url": subcat_url
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
                                        "parent_category_name": subcategory_parent,
                                        "ancestor_name": current_parent_category,
                                        "source_url": subcat_url
                                    })

        if template_type in ["template_1", "template_2"]:
            for module in modules:
                configs = module.get("configs", {})
                heading = configs.get("headingText", "").strip().lower()

                if heading in ["shop by category", "shop girls' categories", "shop boys' categories", "shop by style", "jewelry brands we love", "watch brands we love", "shop by color", "shop by brand", "shop by character", "shop kids' categories", 
                               "shop toys by age", "shop by sport", "shop kids' books by age", "more ways to shop", "brands we love", "outdoor decor & more", "outdoor cooking", "ways to shop furniture", "living room must haves", 
                               "bedroom essentials", "work, play, & organize", "kitchen & dining picks", "shop top-rated picks", "shop kitchen appliances", "shop cookware", "shop bakeware", "shop tools & gadgets", "shop dining & entertaining", "standout kitchen brands", 
                               "all your kitchen needs", "appliance standouts", "essential appliances", "innovative kitchen appliances", "shop by mattress size", "explore more mattress types", "decor must-haves", "more decor", "shop by bedding category", 
                               "more bedding categories", "complete your bedroom", "bathroom essentials", "shop bathroom accessories", "explore more for your bathroom", "top-rated in storage & organization", "shop storage by price", 
                               "browse all storage & organization", "top brands", "garage storage", "housekeeping essentials", "brands to take home", "tech brands you love", "shop tvs by size", "what’s your tv type? ", "accessories & more", 
                               "shop by price", "cameras by type", "action cameras by category", "photoshoot gear", "cameras by brand", "shop smart home by space", "top smart home brands", "additional carriers", "shop video games by genre", 
                               "shop pc gaming by category", "movies by format", "shop by genre", "shop kids' by age", "play ’em on repeat", "vinyl & cd genres", "good times for every age", "featured brands", "popular characters", "top picks", 
                               "action figures you'll love", "keep pests under control", "shop your fave brands", "shop our brands", "try our global cuisines", "tour our global goods", "save with great value", "shop top brands", "a bowl of cozy", 
                               "toast up some yumminess", "more breakfast essentials", "easy mixes & decorations", "shop your favorite brands", "kitchen must-haves", "popular categories", "beer", "wine", "spirits", "rollbacks & more", "shop by condition", 
                               "shop by small pet", "more brands", "explore shaving brands", "boost the experience ", "national car care month", "vehicle maintenance", "spring auto must-haves", "automotive pros", "tires by vehicle", "tires by brand", 
                               "auto batteries", "diy oil change", "auto fluids & additives", "the balloon shop", "the party shop", "the greeting card shop", "crowd pleasers", "seasonal shops", "party essentials", "pick a sport", "brands to sport", "exercise essentials brands", 
                               "top tech brands", "outdoor activities", "camping gear", "shop boating & marine", "explore by brand", "set up camp", "camping essentials", "brands to bring outside", "shop by type", "gear & accessories", 
                               "kids’ bikes by wheel size", "specialty cycling", "floats & water fun", "gear for the whole year", "more gotta-have brands", "around the office", "supplies that get the job done", "moving boxes", "packing supplies", "shipping solutions", "explore more", "shop by pattern", "shop by material", "commercial products"]:
                    rows6 = configs.get("rows6")
                    rows4 = configs.get("rows4")  
                    if isinstance(rows6, list):
                        for row in rows6:
                            for category in row.get("categories", []):
                                name = category.get("name")
                                url = category.get("image", {}).get("clickThrough", {}).get("value")
                                if name and url:
                                    all_categories.append({
                                        "source": "shop_by_category",
                                        "name": name,
                                        "url": url,
                                        "parent_category_name": current_parent_category,
                                        "source_url": subcat_url
                                    })
                    elif isinstance(rows4, list):
                        for row in rows4:
                            for category in row.get("categories", []):
                                name = category.get("name")
                                url = category.get("image", {}).get("clickThrough", {}).get("value")
                                if name and url:
                                    all_categories.append({
                                        "source": "shop_by_category",
                                        "name": name,
                                        "url": url,
                                        "parent_category_name": current_parent_category,
                                        "souce_url": subcat_url
                                    })

        if template_type == "template_3":
            for module in modules:
                configs = module.get("configs", {})
                pillsV2 = configs.get("pillsV2")
                if isinstance(pillsV2, list): 
                    for pill in pillsV2:
                        name = pill.get("title")
                        url = pill.get("url")
                        if name and url:
                            all_categories.append({
                                "name": name,
                                "url": url,
                                "source": "shop_by_category",
                                "parent_category_name": current_parent_category,
                                "source_url": subcat_url
                            })

        if template_type == "unknown":
            print(f"[ERROR] Unknown template type for {subcat_url}")
            failed_urls.append({"url": subcat_url, "subcategory": subcat_name, "department": department_name, "reason": "unknown template"})
            return

        seen = set()
        unique_categories = []
        try:
            with open("all_walmart_categories.json", "r", encoding="utf-8") as f:
                existing_categories = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_categories = []
        for item in all_categories:
            if 'name' in item and 'url' in item and item['url']:
                key = (item['name'], item['url'])
                if key not in seen:
                    seen.add(key)
                    unique_categories.append(item)
            else:
                print(f"category with no URL: {item['name']}")
                unique_categories.append(item)
        combined_categories = existing_categories + unique_categories

        # output_data = {
        #     "template_type": template_type,
        #     "category_count": len(unique_categories),
        #     "categories": unique_categories
        # }

        with open("all_walmart_categories.json", "w", encoding="utf-8") as f:
            json.dump(combined_categories, f, indent=2, ensure_ascii=False)

        print(f"Extracted and saved {len(unique_categories)} categories to 'all_walmart_categories.json'")
        if failed_urls:
            with open("failed_category_urls.json", "w", encoding="utf-8") as f:
                json.dump(failed_urls, f, indent=2, ensure_ascii=False)
            print(f"\nSaved {len(failed_urls)} failed URLs to 'failed_category_urls.json'")
        else:
            print("\nNo failed URLs encountered.")
        browser.close()


df = pd.read_json("new_departments.json")
for index, row in df.iterrows():
    department_name = row['department']
    subcategories = row['subcategories']

    print(f"\nDepartment: {department_name}")

    for subcat in subcategories:
        subcat_name = subcat.get("name")
        subcat_url = subcat.get("url")

        print(f"  Subcategory Name: {subcat_name}")
        print(f"  Subcategory URL: {subcat_url}")
        extract_all_categories(subcat_name, subcat_url, department_name)
        time.sleep(180)


# if __name__ == "__main__":
#     extract_all_categories()
