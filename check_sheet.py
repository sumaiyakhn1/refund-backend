import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "14iL5gSZTbBYx2yYm8olZ1ICfJLu2UolGEkFLny3kdtQ"
SHEET_NAME = "students"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def check_sheet():
    creds = Credentials.from_service_account_file("s:/Work/work-script/refund-application/cleanbackend/service_account.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    
    headers = sheet.row_values(1)
    print("Row 1 Headers:")
    for i, h in enumerate(headers):
        # A is 0, B is 1... P is 15, Q is 16, R is 17
        print(f"Col {chr(65+i)} (index {i}): {h}")

if __name__ == "__main__":
    check_sheet()
