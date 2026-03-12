import pandas as pd
import os
import re

def clean_val(val):
    return re.sub(r'\.0$', '', str(val).strip().lower())

def test_logic():
    print("Testing Refined Validation Logic...")
    file_path = r's:\Work\work-script\refund-application\cleanbackend\New All Data.xlsx'
    df = pd.read_excel(file_path)
    
    # Test case from user: regNo=120198002591 should match Roll No.==120198002591
    test_reg = "120198002591"
    
    is_valid = False
    if 'Roll No.' in df.columns:
        clean_rolls = df['Roll No.'].astype(str).str.strip().str.lower().str.replace(r'\.0$', '', regex=True)
        if clean_rolls.eq(test_reg.lower()).any():
             is_valid = True
             print(f"Match found in 'Roll No.' for {test_reg}")

    if not is_valid and 'Registration No' in df.columns:
        clean_regs = df['Registration No'].astype(str).str.strip().str.lower().str.replace(r'\.0$', '', regex=True)
        if clean_regs.eq(test_reg.lower()).any():
             is_valid = True
             print(f"Match found in 'Registration No' for {test_reg}")

    print(f"Validation for '{test_reg}': {'SUCCESS' if is_valid else 'FAILED'}")

    # Test case for float artifacts: "123.0" should match "123"
    print("\nTesting numeric cleaning...")
    sample_val = "120198002591.0"
    cleaned = re.sub(r'\.0$', '', str(sample_val).strip().lower())
    print(f"Original: {sample_val}, Cleaned: {cleaned}")
    if cleaned == "120198002591":
        print("Numeric cleaning works correctly.")
    else:
        print("Numeric cleaning FAILED.")

if __name__ == "__main__":
    test_logic()
