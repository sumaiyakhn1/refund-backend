from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

# ================= APP =================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= ADMIN CONFIG =================
ADMIN_ID = "7705033040"
ADMIN_PASSWORD = "admin@7705"   # 🔐 CHANGE THIS if you want

# ================= PATH CONFIG =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENT_LOGIN_FILE = os.path.join(BASE_DIR, "student_login.xlsx")

# ================= GOOGLE SHEET CONFIG =================
SPREADSHEET_ID = "14iL5gSZTbBYx2yYm8olZ1ICfJLu2UolGEkFLny3kdtQ"
SHEET_NAME = "students"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ================= GOOGLE SHEET =================
import json

def get_sheet():
    service_account_info = json.loads(
        os.environ["GOOGLE_SERVICE_ACCOUNT"]
    )

    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES
    )

    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(SHEET_NAME)

# ================= MODELS =================
class LoginRequest(BaseModel):
    id: str
    password: str

class StudentData(BaseModel):
    student_id: str
    student_name: str | None = None
    bank_name: str | None = None
    account_no: str | None = None
    ifsc: str | None = None
    account_holder: str | None = None
    fee_cleared: str | None = None
    library_cleared: str | None = None
    status: str | None = None

# ================= HELPERS =================
def get_students_from_excel():
    try:
        # Read Excel without forcing all columns to string immediately.
        # This allows pandas to respect Excel's native Date format for the 'dob' column.
        df = pd.read_excel(STUDENT_LOGIN_FILE)
        
        # Ensure 'id' is treated as a string (handles numeric IDs like 123 -> "123")
        if 'id' in df.columns:
            df['id'] = df['id'].astype(str).str.strip()
            
        # Robust Date Parsing:
        # 1. Native Date objects (from Excel) -> Converted to Timestamp
        # 2. Text Strings (e.g. "28-10-2003") -> Parsed with dayfirst=True
        # 3. Handle errors gracefully
        if 'dob' in df.columns:
            df['dob'] = pd.to_datetime(df['dob'], dayfirst=True, errors='coerce').dt.strftime('%d-%m-%Y')
        
        return df.fillna("")
    except Exception as e:
        print(f"Error reading Excel: {e}")
        raise HTTPException(status_code=500, detail="Student login file not found")

def get_all_rows():
    return get_sheet().get_all_records()

def find_row_number(student_id: str):
    for idx, row in enumerate(get_all_rows()):
        if str(row.get("student_id")) == str(student_id):
            return idx + 2
    return None

# ================= LOGIN API =================
@app.post("/login")
def login(data: LoginRequest):

    # ===== ADMIN LOGIN (SECURE) =====
    if data.id == ADMIN_ID and data.password == ADMIN_PASSWORD:
        return {
            "role": "admin",
            "admin_id": ADMIN_ID
        }

    # ===== STUDENT LOGIN (UNCHANGED) =====
    df = get_students_from_excel()

  

    # Clean data: ensure strings and strip whitespace
    df["id"] = df["id"].astype(str).str.strip()
    df["dob"] = df["dob"].astype(str).str.strip()
    
    input_id = str(data.id).strip()
    input_pass = str(data.password).strip()

    print(f"DEBUG: Input ID: '{input_id}', Input Password: '{input_pass}'")
    
    # Check if ID exists first (for better error message)
    user_row = df[df["id"] == input_id]
    
    if user_row.empty:
        print(f"DEBUG: ID '{input_id}' not found in Excel IDs: {df['id'].tolist()}")
        raise HTTPException(status_code=401, detail=f"User ID '{input_id}' not found in records")

    print(f"DEBUG: User found. Stored DOB: '{user_row.iloc[0]['dob']}'")
    
    # Check password
    if user_row.iloc[0]["dob"] == input_pass:
        return {
            "role": "student",
            "student_id": input_id
        }

    # If we get here, ID matched but Password didn't
    stored_dob = user_row.iloc[0]['dob']
    raise HTTPException(
        status_code=401, 
        detail=f"Password mismatch. Input: '{input_pass}', Stored: '{stored_dob}'"
    )

# ================= STUDENT API =================
@app.get("/student/{student_id}")
def get_student(student_id: str):
    for row in get_all_rows():
        if str(row.get("student_id")) == student_id:
            return row
    raise HTTPException(status_code=404, detail="Student not found")

# ================= ADMIN APIs =================
@app.get("/admin/students")
def get_all_students():
    return get_all_rows()

@app.post("/admin/student")
def create_or_update_student(data: StudentData):
    sheet = get_sheet()
    row_number = find_row_number(data.student_id)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        timestamp,
        data.student_id,
        data.student_name,
        data.bank_name,
        data.account_no,
        data.ifsc,
        data.account_holder,
        data.fee_cleared,
        data.library_cleared,
        data.status
    ]

    if row_number:
        sheet.update(f"A{row_number}:J{row_number}", [row])
        return {"message": "Student updated"}
    else:
        sheet.append_row(row)
        return {"message": "Student created"}

# ================= DOWNLOAD =================
@app.get("/admin/download")
def download_excel():
    records = get_all_rows()
    if not records:
        raise HTTPException(status_code=400, detail="No data to export")

    df = pd.DataFrame(records)
    file_name = "students.xlsx"
    df.to_excel(file_name, index=False)

    return FileResponse(
        file_name,
        filename="students.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
