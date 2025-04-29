import pandas as pd

df = pd.read_json("new_departments.json")

# print(df.head())

# df.to_excel('departments.xlsx', index=False)
 
for index, row in df.iterrows():
    department_name = row['department']
    subcategories = row['subcategories']

    print(f"\nDepartment: {department_name}")

    for subcat in subcategories:
        name = subcat.get("name")
        url = subcat.get("url")

        print(f"  Subcategory Name: {name}")
        print(f"  Subcategory URL: {url}")
