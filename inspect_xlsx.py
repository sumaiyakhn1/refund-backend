import pandas as pd
import os

file_path = r's:\Work\work-script\refund-application\cleanbackend\New All Data.xlsx'
if os.path.exists(file_path):
    df = pd.read_excel(file_path)
    print("Columns:")
    for col in df.columns:
        print(f"'{col}'")
    print("\nFirst 5 Registration No values:")
    if 'Registration No' in df.columns:
        print(df['Registration No'].head().to_list())
    else:
        # Try to find a column that looks like Registration No
        reg_cols = [c for c in df.columns if 'reg' in str(c).lower()]
        print(f"Potential registration columns: {reg_cols}")
        if reg_cols:
             print(df[reg_cols[0]].head().to_list())
else:
    print(f"File not found: {file_path}")
