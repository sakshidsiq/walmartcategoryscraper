import pandas as pd

df = pd.read_json("walmart_departments.json")

def assign_hierarchy_levels(df):
    df['level'] = pd.NA  

    missing_source_df = df[df['source'].isna() | (df['source'] == '')]

    missing_source_df.to_json("missing_source_data.json", orient='records', lines=True)

    # df = df.dropna(subset=['source'])

    df.loc[df['parent_category_name'].isna(), 'level'] = 0

    current_level = 0

    while True:
        current_level_names = df.loc[df['level'] == current_level, 'name']

        mask = df['level'].isna() & df['parent_category_name'].isin(current_level_names)

        if not mask.any():
            break

        if current_level == 0:
            source_mask = mask & (df['source'] == 'departments')
            df.loc[source_mask, 'level'] = 1

        if current_level == 1:
            source_mask = mask & df['source'].isin(['top_nav_header', 'generic_name_selector', 
                                                    'shop_by_category', 'categories4x4', 'categories4x1'])
            df.loc[source_mask, 'level'] = 2

        if current_level == 2:
            source_mask = mask & (df['source'] == 'categoryGroup')
            df.loc[source_mask, 'level'] = 3

        if current_level == 3:
            source_mask = mask & (df['source'] == 'subCategoryGroup')
            df.loc[source_mask, 'level'] = 4

        current_level += 1

    # df['level'] = df['level'].astype('Int64')

    return df


df = assign_hierarchy_levels(df)

# print(df)

df.to_excel('outputanother.xlsx', index=False)