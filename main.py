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
STUDENT_LOGIN_FILE = os.path.join(BASE_DIR, "F926E400.xlsx")

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
    mother_name: str | None = None
    student_mobile: str | None = None
    contact_mobile: str | None = None
    fee_cleared: str | None = None
    library_cleared: str | None = None
    scholarship_cleared: str | None = None
    registration_cleared: str | None = None
    status: str | None = None
    remark: str | None = None
    engaged: str | None = None
    security: str | None = None
    course: str | None = None



# ================= HELPERS =================
def get_all_rows():
    try:
        sheet = get_sheet()
        values = sheet.get_all_values()
        if not values:
            return []
            
        header = values[0]
        # Standard columns we expect
        EXPECTED_COLS = [
            'timestamp', 'student_id', 'student_name', 'bank_name', 'account_no', 
            'ifsc', 'account_holder', 'fee_cleared', 'library_cleared', 
            'scholarship_cleared', 'registration_cleared', 'status', 'remark', 
            'engaged', 'security', 'course', 'contact_mobile', 'mother_name', 
            'photo', 'student_mobile'
        ]
        
        records = []
        for row in values[1:]:
            record = {}
            for i, val in enumerate(row):
                if i < len(EXPECTED_COLS):
                    key = EXPECTED_COLS[i]
                else:
                    # Fallback for extra columns
                    key = header[i] if i < len(header) and header[i] else f"col_{i}"
                
                record[key] = val
            
            # Additional cleanup/normalization
            contact_val = record.get("contact_mobile") or ""
            mother_val = record.get("mother_name") or ""
            
            # Robust mobile check (some older sheets might have 'student mobile no 2')
            if not contact_val:
                for i, col_name in enumerate(header):
                    if i < len(row):
                        clean_key = str(col_name).strip().lower()
                        if "mobile no 2" in clean_key:
                            contact_val = str(row[i]).strip()
            
            record["contact_mobile"] = contact_val
            record["mother_name"] = mother_val
            records.append(record)
            
        return records
    except Exception as e:
        print(f"Error getting records: {e}")
        return []


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

    # ===== STUDENT LOGIN (NOW HANDLED ON FRONTEND VIA OFFICIAL API) =====
    raise HTTPException(status_code=401, detail="Student login must be performed via the official portal")

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

class StudentData(BaseModel):
    timestamp: str | None = None
    student_id: str | None = None
    student_name: str | None = None
    bank_name: str | None = None
    account_no: str | None = None
    ifsc: str | None = None
    account_holder: str | None = None
    mother_name: str | None = None
    contact_mobile: str | None = None
    student_mobile: str | None = None
    fee_cleared: str | None = None
    library_cleared: str | None = None
    scholarship_cleared: str | None = None
    registration_cleared: str | None = None
    status: str | None = None
    remark: str | None = None
    engaged: str | None = None
    security: str | None = None
    course: str | None = None
    photo: str | None = None

@app.post("/admin/student")
def create_or_update_student(data: StudentData):
    sheet = get_sheet()
    student_id = data.student_id or ""
    row_number = find_row_number(student_id)
    
    print(f"DEBUG: updating student {student_id}. Row: {row_number}")
    print(f"DEBUG: Data Received: {data.dict()}")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        timestamp,
        student_id,
        data.student_name or "",
        data.bank_name or "",
        data.account_no or "",
        data.ifsc or "",
        data.account_holder or "",
        data.fee_cleared or "NO",
        data.library_cleared or "NO",
        data.scholarship_cleared or "NO",
        data.registration_cleared or "NO",
        data.status or "PENDING",
        data.remark or "",
        data.engaged or "",
        data.security or "",
        data.course or "",
        data.contact_mobile or "",
        data.mother_name or "",
        data.photo or "",
        data.student_mobile or ""
    ]

    if row_number:
        # A to T (20 columns)
        sheet.update(f"A{row_number}:T{row_number}", [row])
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

    # Only include entries where status is APPROVED
    approved_records = []
    for r in records:
        if str(r.get("status", "")).upper() == "APPROVED":
            approved_records.append(r)

    if not approved_records:
        raise HTTPException(status_code=400, detail="No approved entries to export")

    df = pd.DataFrame(approved_records)
    
    # Clean up backend-only columns and duplicate manual columns
    cols_to_drop = ['contact_mobile', 'mother_name', 'photo']
    for col in cols_to_drop:
        if col in df.columns:
            df = df.drop(columns=[col])

    # Rename the actual Google Sheet column 'student mobile no 2' to 'Application Contact No'
    for col in list(df.columns):
        clean_col = str(col).strip().lower()
        if clean_col == "student mobile no 2" or "mobile no 2" in clean_col:
            df = df.rename(columns={col: 'Application Contact No'})
            break
    
    file_name = "students.xlsx"
    df.to_excel(file_name, index=False)

    return FileResponse(
        file_name,
        filename="students.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
