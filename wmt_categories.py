from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import json
import random
import time
import pandas as pd

KEYWORDS = [
    "category", "girls'", "boys'", "style", "jewelry", "watch", "color", "shop", "brand", "character", "categories", 
    "toys", "age", "shop", "sport", "kids'", "books", "ways", "brands", "love", "outdoor", "decor", "outdoor cooking", "ways", "furniture", "living", "room", "must haves", 
    "bedroom", "essentials", "work", "play","organize", "picks", "appliances", "cookware", "bakeware", "tools", "gadgets", "dining", "entertaining", "standout", "kitchen", "brands", 
    "all","needs", "appliance", "standouts", "essential", "innovative", "kitchen", "appliances", "size", "mattress", "must-haves", "decor", "category", 
    "bedding", "complete", "bedroom", "essentials", "shop", "bathroom", "accessories", "explore", "bathroom", "top-rated", "shop", "price", 
    "browse", "all", "storage", "organization", "top", "brands", "garage", "storage", "housekeeping", "home", "tech", "tvs", "size", "what’s", "tv", "accessories", 
    "price", "cameras", "action", "photoshoot", "cameras", "space", "smart", "home", "additional", "carriers", "video", "games", 
    "pc", "gaming", "movies", "format", "genre", "kids'", "repeat", "vinyl", "cd", "genres", "good times", "age", "featured", "characters", "picks", 
    "action", "figures" ,"love", "pests", "under", "control", "fave", "shop", "cuisines", "tour", "global", "save", "value", "top", "bowl", 
    "toast", "yumminess", "breakfast", "mixes", "decorations", "favorite", "kitchen", "popular", "categories", "beer", "wine", "spirits", "rollbacks", "condition", 
    "small", "pet", "more", "shaving", "boost", "car", "maintenance", "spring", "automotive", "vehicle", "tires", 
    "auto", "batteries", "oil", "fluids", "balloon", "party", "card", "crowd", "seasonal", "party", "pick", "sport", "exercise", 
    "tech", "outdoor", "activities", "camping", "boating", "explore", "camp", "camping", "outside", "type", "accessories", 
    "bikes", "cycling", "floats", "gear", "brands", "office", "job", "boxes", "packing", "shipping", "explore", "pattern", "material", "commercial"
]

def heading_matches(heading):
    heading = heading.lower()
    return any(keyword in heading for keyword in KEYWORDS)

def human_delay(min_time=2.5, max_time=4.0):
    time.sleep(random.uniform(min_time, max_time))

def scroll_page_like_human(page, steps=6):
    for _ in range(steps):
        page.mouse.wheel(0, random.randint(300, 500))
        human_delay(0.4, 0.8)

def log_failed_url(url, subcat, dept, reason):
    failed_entry = {
        "url": url,
        "subcategory": subcat,
        "department": dept,
        "reason": reason
    }
    try:
        with open("failed_category_urls.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    data.append(failed_entry)
    with open("failed_category_urls.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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
        full_url = f"https://www.walmart.com{subcat_url}" if subcat_url.startswith("/") else subcat_url
        page.goto(full_url, timeout=60000, wait_until="domcontentloaded")

        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        if "application error" in page.content().lower():
            print("Detected client-side application error. Retrying after 5 seconds...")
            time.sleep(5)
            page.reload()
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            if "application error" in page.content().lower():
                print(f"[ERROR] Application error on page: {subcat_url}")
                log_failed_url(subcat_url, subcat_name, department_name, "application error")
                return
            
        if "verify" in page.title().lower():
            print(f"[ERROR] Bot verification required: {subcat_url}")
            log_failed_url(subcat_url, subcat_name, department_name, "application error")
            return

        scroll_page_like_human(page)
        human_delay(5, 10)

        print("Extracting __NEXT_DATA__...")
        next_data = page.evaluate("window.__NEXT_DATA__")
        if not next_data:
            print(f"[ERROR] __NEXT_DATA__ not found for {subcat_url}")
            log_failed_url(subcat_url, subcat_name, department_name, "application error")
            return
        

        initial_data = next_data.get("props", {}).get("pageProps", {}).get("initialTempoData", {})
        modules_1 = initial_data.get("contentLayout", {}).get("modules", [])
        modules_2 = initial_data.get("data", {}).get("contentLayout", {}).get("modules", [])
        modules_3 = []
        pills_top_zone = next_data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("moduleDataByZone", {}).get("pillsTopZone")
        if isinstance(pills_top_zone, dict):
            modules_3.append(pills_top_zone)

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
                log_failed_url(subcat_url, subcat_name, department_name, "application error")
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
        current_parent_url = subcat_url
        all_categories = []
        all_categories.append({
            "name": department_name,
            "url": ""
        })
        all_categories.append({
            "source": "departments",
            "name": subcat_name,
            "parent_category_name": department_name,
            "parent_category_url": "",
            "source_url": subcat_url
        })

        if template_type == "template_1":
            for el in generic_name_elements:
                name = el.inner_text().strip()
                url = el.get_attribute("href")
                if name and url:
                    gen_data_type = "brand_data" if 'brand' in url else "category_data"
                    all_categories.append({
                        "source": "generic_name_selector",
                        "name": name,
                        "url": url,
                        "parent_category_name": current_parent_category,
                        "parent_category_url": current_parent_url,
                        "data_type": gen_data_type,
                        "source_url": subcat_url
                    })

            for module in modules:
                configs = module.get("configs", {})

                for item in configs.get("categories4x1", []):
                    heading_text = configs.get("headingText", "").strip().lower()
                    brand_indentifier = "brand_data" if 'brand' in heading_text else "category_data"
                    all_categories.append({
                        "source": "categories4x1",
                        "name": item.get("name"),
                        "url": item.get("image", {}).get("clickThrough", {}).get("value"),
                        "parent_category_name": current_parent_category,
                        "parent_category_url": current_parent_url,
                        "source_url": subcat_url,
                        "data_type": brand_indentifier
                    })

                for row in configs.get("rows", []):
                    for item in row.get("categories4x4", []):
                        cat_heading_text = configs.get("headingText", "").strip().lower()
                        cat_brand_indentifier = "brand_data" if 'brand' in cat_heading_text else "category_data"
                        all_categories.append({
                            "source": "categories4x4",
                            "name": item.get("name"),
                            "url": item.get("image", {}).get("clickThrough", {}).get("value"),
                            "parent_category_name": current_parent_category,
                            "parent_category_url": current_parent_url,
                            "source_url": subcat_url,
                            "data_type": cat_brand_indentifier
                        })

                for nav in configs.get("navHeaders", []):
                    header = nav.get("header", {})
                    header_name = header.get("linkText")
                    header_url = header.get("clickThrough", {}).get("value")
                    if header:
                        nav_data_type = "brand_data" if "brand" in header_name.lower() else "category_data"
                        all_categories.append({
                            "source": "top_nav_header",
                            "name": header_name,
                            "url": header_url,
                            "parent_category_name": current_parent_category,
                            "parent_category_url": current_parent_url,
                            "source_url": subcat_url,
                            "data_type": nav_data_type
                        })

                    parent_category = header_name
                    parent_url = header_url

                    for group in nav.get("categoryGroup", []):
                        category = group.get("category", {})
                        category_name = category.get("linkText")
                        category_url = category.get("clickThrough", {}).get("value")

                        if category_name and category_url:
                            data_type = "brand_data" if "brand" in category_name.lower() else ("brand_data" if nav_data_type == "brand_data" else "category_data")
                            all_categories.append({
                                "source": "categoryGroup",
                                "name": category_name,
                                "url": category_url,
                                "parent_category_name": parent_category,
                                "parent_category_url": parent_url,
                                "ancestor_name": current_parent_category,
                                "source_url": subcat_url,
                                "data_type": data_type
                            })

                        subcategory_parent = category_name
                        subcategory_parent_url = category_url

                        for sub_group in group.get("subCategoryGroup") or []:
                            sub = sub_group.get("subCategory", {})
                            if sub:
                                sub_name = sub.get("linkText")
                                sub_url = sub.get("clickThrough", {}).get("value")

                                if sub_name and sub_url:
                                    sub_data_type = "brand_data" if data_type == "brand_data" else "category_data"
                                    all_categories.append({
                                        "source": "subCategoryGroup",
                                        "name": sub_name,
                                        "url": sub_url,
                                        "parent_category_name": subcategory_parent,
                                        "parent_category_url": subcategory_parent_url,
                                        "ancestor_name": current_parent_category,
                                        "source_url": subcat_url,
                                        "data_type": sub_data_type
                                    })

        if template_type in ["template_1", "template_2"]:
            for module in modules:
                configs = module.get("configs", {})
                heading = configs.get("headingText", "").strip().lower()

                if heading_matches(heading):
                    rows6 = configs.get("rows6")
                    rows4 = configs.get("rows4")  
                    if isinstance(rows6, list):
                        for row in rows6:
                            for category in row.get("categories", []):
                                name = category.get("name")
                                url = category.get("image", {}).get("clickThrough", {}).get("value")
                                if name and url:
                                    row_data_type = "brand_data" if 'brand' in heading else "category_data"
                                    all_categories.append({
                                        "source": "shop_by_category",
                                        "name": name,
                                        "url": url,
                                        "parent_category_name": current_parent_category,
                                        "parent_category_url": current_parent_url,
                                        "source_url": subcat_url,
                                        "data_type": row_data_type
                                    })
                    elif isinstance(rows4, list):
                        for row in rows4:
                            for category in row.get("categories", []):
                                name = category.get("name")
                                url = category.get("image", {}).get("clickThrough", {}).get("value")
                                if name and url:
                                    row_data_type = "brand_data" if 'brand' in heading else "category_data"
                                    all_categories.append({
                                        "source": "shop_by_category",
                                        "name": name,
                                        "url": url,
                                        "parent_category_name": current_parent_category,
                                        "parent_category_url": current_parent_url,
                                        "source_url": subcat_url,
                                        "data_type": row_data_type
                                    })

        if template_type == "template_3":
            for module in modules:
                configs = module.get("configs", {})
                pillsV2 = configs.get("pillsV2")
                if isinstance(pillsV2, list): 
                    for pill in pillsV2:
                        name = pill.get("title")
                        pill_url = pill.get("url")
                        if name and url:
                            pill_data_type = "brand_data" if 'brand' in pill_url else "category_data"
                            all_categories.append({
                                "name": name,
                                "url": pill_url,
                                "source": "shop_by_category",
                                "parent_category_name": current_parent_category,
                                "parent_category_url": current_parent_url,
                                "source_url": subcat_url,
                                "data_type": pill_data_type
                            })

        if template_type == "unknown":
            print(f"[ERROR] Unknown template type for {subcat_url}")
            log_failed_url(subcat_url, subcat_name, department_name, "application error")
            return

        seen = set()
        unique_categories = []
        try:
            with open("second_walmart_categories.json", "r", encoding="utf-8") as f:
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

        with open("second_walmart_categories.json", "w", encoding="utf-8") as f:
            json.dump(combined_categories, f, indent=2, ensure_ascii=False)

        print(f"Extracted and saved {len(unique_categories)} categories to 'second_walmart_categories.json'")
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

