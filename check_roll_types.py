import pandas as pd
import os

file_path = r's:\Work\work-script\refund-application\cleanbackend\New All Data.xlsx'
if os.path.exists(file_path):
    df = pd.read_excel(file_path)
    print("Columns:", df.columns.tolist())
    if 'Roll No.' in df.columns:
        print("\nFirst 10 Roll No. values and their types:")
        rolls = df['Roll No.'].head(10)
        for val in rolls:
            print(f"Value: {val}, Type: {type(val)}")
    else:
        print("\n'Roll No.' column not found.")
else:
    print(f"\nFile not found: {file_path}")
