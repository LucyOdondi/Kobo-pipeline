import json

import pandas as pd

with open("data/raw/submissions_raw.json", encoding="utf-8") as raw_file:
    submissions_list = json.load(raw_file)

submissions_dataframe = pd.DataFrame(submissions_list)

print("Rows and columns:", submissions_dataframe.shape)
print()

for column_name in submissions_dataframe.columns:
    print(column_name)