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
# ================= ADMIN CONFIG =================
ADMIN_ROLES = {
    "super_admin": {"pass": "super@123", "permissions": "all"},  # Super Admin
    "fee_admin":   {"pass": "fee@123",   "permissions": "fee_cleared"},
    "lib_admin":   {"pass": "lib@123",   "permissions": "library_cleared"},
    "schol_admin": {"pass": "schol@123", "permissions": "scholarship_cleared"},
    "reg_admin":   {"pass": "reg@123",   "permissions": "registration_cleared"},
}

# ================= PATH CONFIG =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENT_LOGIN_FILE = os.path.join(BASE_DIR, "5_6075497004178349834.xlsx")

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
    try:
        if "GOOGLE_SERVICE_ACCOUNT" in os.environ:
            service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
            creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        else:
            # Fallback to local file for easier local development
            creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    except Exception as e:
        print(f"Error loading credentials: {e}")
        # Final fallback/attempt
        creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)

    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(SHEET_NAME)

# ================= MODELS =================
class LoginRequest(BaseModel):
    id: str
    password: str
    course: str | None = None  # Optional for admin, required for student

class StudentData(BaseModel):
    timestamp: str | None = None
    student_id: str
    student_name: str | None = None
    bank_name: str | None = None
    account_no: str | None = None
    ifsc: str | None = None
    account_holder: str | None = None
    fee_cleared: str | None = None
    library_cleared: str | None = None
    scholarship_cleared: str | None = None
    registration_cleared: str | None = None
    status: str | None = None
    remark: str | None = None
    engaged: str | None = None

# ================= HELPERS =================
# Global Cache: Maps sheet_name -> DataFrame
CACHED_DFS = {} 
LAST_MTIME = 0

def get_students_from_excel(sheet_name="Sheet1"):
    global CACHED_DFS, LAST_MTIME
    
    try:
        # Check file modification time
        if not os.path.exists(STUDENT_LOGIN_FILE):
             raise HTTPException(status_code=500, detail="Student login file not found")
             
        current_mtime = os.path.getmtime(STUDENT_LOGIN_FILE)
        
        # Reload if file changed or sheet not in cache
        # If file changed, we might want to clear entire cache? 
        # Yes, good practice to invalidate all if underlying file changed.
        if current_mtime > LAST_MTIME:
            print(f"File changed. Clearing cache. (Modified: {datetime.fromtimestamp(current_mtime)})")
            CACHED_DFS = {}
            LAST_MTIME = current_mtime
            
        if sheet_name not in CACHED_DFS:
            print(f"Loading Sheet: '{sheet_name}'")
            try:
                # Read specific sheet
                df = pd.read_excel(STUDENT_LOGIN_FILE, sheet_name=sheet_name)
            except ValueError:
                 # Sheet not found
                 raise HTTPException(status_code=400, detail=f"Course '{sheet_name}' not found in records")
            
            # Ensure 'id' is treated as a string (handle scientific notation & float)
            if 'id' in df.columns:
                def clean_id(x):
                    try:
                        if pd.isna(x): return ""
                        # If float like 123.0, convert to int then str -> "123"
                        # If numeric string "123", just "123"
                        # If float 1.2E+11, int() handles it usually if small enough, but python float does.
                        if isinstance(x, float):
                            return str(int(x))
                        if isinstance(x, int):
                            return str(x)
                        return str(x).strip()
                    except:
                        return str(x).strip()

                df['id'] = df['id'].apply(clean_id)
            
            # Treat 'dob' as a generic password field (string)
            if 'dob' in df.columns:
                # Try to convert to datetime first to normalize format
                # This handles both Excel date objects and string dates like "25-Jun-2004"
                try:
                    # Convert to datetime, coerce errors to NaT
                    temp_dates = pd.to_datetime(df['dob'], errors='coerce')
                    
                    # Create a mask for valid dates
                    mask = temp_dates.notna()
                    
                    # Format valid dates to DD-MMM-YY (e.g., 08-Sep-04)
                    df.loc[mask, 'dob'] = temp_dates[mask].dt.strftime('%d-%b-%y')
                    
                    # For invalid dates (or already strings that failed parsing), ensure they are strings
                    df.loc[~mask, 'dob'] = df.loc[~mask, 'dob'].astype(str).str.strip()
                    
                except Exception as e:
                    # Fallback
                    print(f"Date conversion error: {e}")
                    df['dob'] = df['dob'].astype(str).str.strip()
            
            CACHED_DFS[sheet_name] = df.fillna("")
            
        return CACHED_DFS[sheet_name]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error reading Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading course data: {str(e)}")

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
    cid = data.id.strip()
    cpass = data.password.strip()

    # ===== ADMIN LOGIN (ROLE BASED) =====
    if cid in ADMIN_ROLES:
        admin_data = ADMIN_ROLES[cid]
        if admin_data["pass"] == cpass:
            return {
                "role": "admin",
                "admin_id": cid,
                "permissions": admin_data["permissions"]
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid Admin Password")

    # ===== STUDENT LOGIN =====
    # Students must select a course
    if not data.course:
         raise HTTPException(status_code=400, detail="Please select a course")
         
    # Load specific sheet
    df = get_students_from_excel(sheet_name=data.course)

    # Clean data: ensure strings and strip whitespace
    # Note: caching might already do this, but safe to do on df view
    # Actually, cache does it. But specific checking here:
    
    input_id = str(data.id).strip()
    input_pass = str(data.password).strip()

    print(f"DEBUG: Input ID: '{input_id}', Input Password: '{input_pass}', Course: '{data.course}'")
    
    # Check if ID exists first
    user_row = df[df["id"] == input_id]
    
    if user_row.empty:
        print(f"DEBUG: ID '{input_id}' not found in {data.course}")
        raise HTTPException(status_code=401, detail=f"User ID '{input_id}' not found in {data.course} records")

    print(f"DEBUG: User found. Stored Pass: '{user_row.iloc[0]['dob']}'")
    
    # Check password
    if user_row.iloc[0]["dob"] == input_pass:
        # Convert row to dict and handle NaN
        student_details = user_row.iloc[0].fillna("").to_dict()
        return {
            "role": "student",
            "student_id": input_id,
            "student_details": student_details
        }

    # If we get here, ID matched but Password didn't
    stored_dob = user_row.iloc[0]['dob']
    raise HTTPException(
        status_code=401, 
        detail=f"Password mismatch."
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
    
    print(f"DEBUG: updating student {data.student_id}. Row: {row_number}")
    print(f"DEBUG: Data Received: {data.dict()}")

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
        data.scholarship_cleared,
        data.registration_cleared,
        data.status,
        data.remark,
        data.engaged
    ]

    if row_number:
        sheet.update(f"A{row_number}:N{row_number}", [row])
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
