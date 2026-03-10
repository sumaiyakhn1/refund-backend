
import os
import json
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "14iL5gSZTbBYx2yYm8olZ1ICfJLu2UolGEkFLny3kdtQ"
SHEET_NAME = "students"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    try:
        creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        return spreadsheet.worksheet(SHEET_NAME)
    except Exception as e:
        print(f"Error: {e}")
        return None

sheet = get_sheet()
if sheet:
    print("Success!")
    values = sheet.get_all_values()
    print(f"Found {len(values)} rows (including header).")
    if len(values) > 0:
        print(f"Header: {values[0]}")
else:
    print("Failed!")
