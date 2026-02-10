from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from fastapi.responses import FileResponse

app = FastAPI()

# ================= CONFIG =================
ADMIN_ID = "7705033040"
ADMIN_PASSWORD = "7705033040"

SPREADSHEET_ID = "14iL5gSZTbBYx2yYm8olZ1ICfJLu2UolGEkFLny3kdtQ"
SHEET_NAME = "students"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ============ GOOGLE SHEET (LAZY LOAD) ============
def get_sheet():
    creds = Credentials.from_service_account_file(
        "service_account.json",
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
def get_all_rows():
    sheet = get_sheet()
    return sheet.get_all_records()


def find_row_number(student_id: str):
    records = get_all_rows()
    for idx, row in enumerate(records):
        if str(row.get("student_id")) == str(student_id):
            return idx + 2  # header + index
    return None


# ================= APIs =================

@app.post("/login")
def login(data: LoginRequest):
    if data.id == ADMIN_ID and data.password == ADMIN_PASSWORD:
        return {"role": "admin"}

    records = get_all_rows()
    for row in records:
        if str(row.get("student_id")) == data.id:
            return {"role": "student", "student_id": data.id}

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/student/{student_id}")
def get_student(student_id: str):
    records = get_all_rows()
    for row in records:
        if str(row.get("student_id")) == student_id:
            return row
    raise HTTPException(status_code=404, detail="Student not found")


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
