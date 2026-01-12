from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
import pandas as pd
import sqlite3
import io
import os
import numpy as np
from dateutil.relativedelta import relativedelta
from datetime import datetime

# --- CONFIGURATION ---
# Default to port 5000 for local development, can be overridden by env var
PORT = int(os.environ.get("PORT", 5000))

app = Flask(__name__, static_folder="../frontend/dist", static_url_path="")
CORS(app, resources={r"/*": {"origins": "*"}})

OUTPUT_FOLDER = 'outputs'
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# --- STATE MAPPING DICTIONARY (Short Code -> Full Name) ---
STATE_MAP = {
    # Valid State Codes
    "AN": "ANDAMAN AND NICOBAR ISLANDS",
    "AP": "ANDHRA PRADESH",
    "AR": "ARUNACHAL PRADESH",
    "AS": "ASSAM",
    "BR": "BIHAR",
    "CH": "CHANDIGARH",
    "CG": "CHHATTISGARH",
    "CT": "CHHATTISGARH",      # Common Variant
    "DN": "DADRA AND NAGAR HAVELI",
    "DD": "DAMAN AND DIU",
    "DL": "DELHI",
    "GA": "GOA",
    "GJ": "GUJARAT",
    "HR": "HARYANA",
    "HP": "HIMACHAL PRADESH",
    "JK": "JAMMU AND KASHMIR",
    "JH": "JHARKHAND",
    "KA": "KARNATAKA",
    "KL": "KERALA",
    "LA": "LADAKH",
    "LD": "LAKSHADWEEP",
    "MP": "MADHYA PRADESH",
    "MH": "MAHARASHTRA",
    "MN": "MANIPUR",
    "ML": "MEGHALAYA",
    "MZ": "MIZORAM",
    "NL": "NAGALAND",
    "OD": "ODISHA",
    "OR": "ODISHA",            # Legacy Code for Orissa -> Odisha
    "PY": "PUDUCHERRY",
    "PB": "PUNJAB",
    "RJ": "RAJASTHAN",
    "SK": "SIKKIM",
    "TN": "TAMIL NADU",
    "TS": "TELANGANA",
    "TR": "TRIPURA",
    "UP": "UTTAR PRADESH",
    "UK": "UTTARAKHAND",
    "UA": "UTTARAKHAND",       # Common Variant
    "WB": "WEST BENGAL",
    "AG": "Agrigento", # Placeholder for AG
}

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

def get_prev_month_name(month_str):
    try:
        dt = datetime.strptime(month_str, "%b %Y")
        prev_dt = dt - relativedelta(months=1)
        return prev_dt.strftime("%b %Y").upper()
    except:
        return "PREV_MONTH"

def normalize_columns(df):
    """Standardizes column names and Fixes State Names."""
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {c.lower().replace("  ", " "): c for c in df.columns}
    renames = {}
    
    if 'courier stauts' in col_map: renames[col_map['courier stauts']] = 'Courier_Status'
    elif 'courier status' in col_map: renames[col_map['courier status']] = 'Courier_Status'
    if 'pickup location' in col_map: renames[col_map['pickup location']] = 'Pickup_Location'
    if 'total' in col_map: renames[col_map['total']] = 'Total'
    if 'lineitem name' in col_map: renames[col_map['lineitem name']] = 'Lineitem_name'
    if 'lineitem quantity' in col_map: renames[col_map['lineitem quantity']] = 'Lineitem_quantity'
    if 'updated status' in col_map: renames[col_map['updated status']] = 'Updated_Status'
    if 'tally hsn' in col_map: renames[col_map['tally hsn']] = 'HSN'
    if 'hsn' in col_map: renames[col_map['hsn']] = 'HSN'
    if 'shipping province' in col_map: renames[col_map['shipping province']] = 'Shipping_Province'

    # Map existing Taxable column if present
    tax_cols = [c for c in df.columns if c.strip().upper() in ['TAXABLE', 'TAXABLE AMOUNT', 'TAXABLE_AMOUNT']]
    if tax_cols: 
        renames[tax_cols[0]] = 'Taxable_Amount'

    if renames: df.rename(columns=renames, inplace=True)
    df.columns = [c.replace(" ", "_") for c in df.columns]
    
    # --- NEW: Fix Merged Cells & State Codes ---
    if 'Shipping_Province' in df.columns:
        # 1. FIX MERGED CELLS (Copy value down to empty rows)
        df['Shipping_Province'] = df['Shipping_Province'].replace(r'^\s*$', np.nan, regex=True).ffill()

        # 2. Convert to string and clean
        df['Shipping_Province'] = df['Shipping_Province'].astype(str).str.strip().str.upper()
        
        # 3. Replace using the STATE_MAP dictionary
        df['Shipping_Province'] = df['Shipping_Province'].replace(STATE_MAP)

        # 4. Remove literal "NAN" strings if they still exist
        df['Shipping_Province'] = df['Shipping_Province'].replace({'NAN': '', 'nan': ''})

    df = df.loc[:, ~df.columns.duplicated()]
    return df

def prepare_sql_data(df):
    df = normalize_columns(df)
    
    if 'Total' in df.columns:
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
    
    # Calculate Taxable Amount (No Rounding to preserve Sum precision)
    df['Taxable_Amount'] = (df['Total'] / 1.18)
    
    df_str = df.astype(str)
    conn = sqlite3.connect(":memory:")
    df_str.to_sql("processed_data", conn, index=False, if_exists="replace")
    return conn

def convert_to_returns(df):
    cols_to_negate = ['Total', 'Taxable_Amount', 'Lineitem_quantity']
    for col in cols_to_negate:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) * -1
    return df

def fix_booleans(df):
    for col in df.columns:
        col_str = str(col).lower()
        if df[col].dtype == bool:
            df[col] = df[col].astype(str).replace({'True': 'True', 'False': 'False'})
        elif set(df[col].dropna().unique()).issubset({0, 1, 0.0, 1.0}):
            if "quantity" not in col_str and "amount" not in col_str and "price" not in col_str:
                 df[col] = df[col].replace({1: 'True', 0: 'False', 1.0: 'True', 0.0: 'False'})
    return df

def reorder_columns_first(df, col_name):
    if col_name in df.columns:
        cols = [col_name] + [c for c in df.columns if c != col_name]
        return df[cols]
    return df

def filter_positive_only(df):
    """Removes rows where Taxable_Amount is strictly less than 0."""
    if 'Taxable_Amount' in df.columns:
        temp_numeric = pd.to_numeric(df['Taxable_Amount'], errors='coerce').fillna(0)
        df = df[temp_numeric >= 0].copy()
    return df

def process_prev_month_returns(file_storage, month_label):
    # READ FILE ONCE into memory object 'xl'
    xl = pd.ExcelFile(file_storage)
    sheet_names = xl.sheet_names
    
    df_hr_returns = pd.DataFrame()
    df_up_returns = pd.DataFrame()
    target_keywords = ['cancelled', 'free order', 'lost', 'refunded', 'rtoed']

    hr_sheet = next((s for s in sheet_names if "HR" in s.upper() and "GSTR1" in s.upper() and "PVT" not in s.upper()), None)
    up_sheet = next((s for s in sheet_names if "UP" in s.upper() and "GSTR1" in s.upper() and "PVT" not in s.upper()), None)

    # --- PROCESS HR ---
    if hr_sheet:
        print(f"   Reading HR Sheet: {hr_sheet}")
        # USE 'xl' object to read, NOT 'file_storage'
        df_raw = pd.read_excel(xl, sheet_name=hr_sheet)
        df_raw = normalize_columns(df_raw)
        
        # Calculate Taxable so we can filter negatives
        if 'Total' in df_raw.columns:
             df_raw['Total'] = pd.to_numeric(df_raw['Total'], errors='coerce').fillna(0)
             df_raw['Taxable_Amount'] = (df_raw['Total'] / 1.18)

        if 'Updated_Status' in df_raw.columns:
            status_col = df_raw['Updated_Status'].astype(str).str.lower().str.strip()
            df_ret = df_raw[status_col.isin(target_keywords)].copy()
            if not df_ret.empty:
                # Filter out rows that are already negative
                df_ret = filter_positive_only(df_ret)
                
                if not df_ret.empty:
                    cols_to_drop = [c for c in df_ret.columns if c.lower() == 'month']
                    if cols_to_drop: df_ret.drop(columns=cols_to_drop, inplace=True)
                    df_ret['Month'] = month_label
                    df_ret = reorder_columns_first(df_ret, 'Month')
                    df_hr_returns = convert_to_returns(df_ret)

    # --- PROCESS UP ---
    if up_sheet:
        print(f"   Reading UP Sheet: {up_sheet}")
        # USE 'xl' object to read, NOT 'file_storage'
        df_raw = pd.read_excel(xl, sheet_name=up_sheet)
        df_raw = normalize_columns(df_raw)
        
        # Calculate Taxable so we can filter negatives
        if 'Total' in df_raw.columns:
             df_raw['Total'] = pd.to_numeric(df_raw['Total'], errors='coerce').fillna(0)
             df_raw['Taxable_Amount'] = (df_raw['Total'] / 1.18)

        if 'Updated_Status' in df_raw.columns:
            status_col = df_raw['Updated_Status'].astype(str).str.lower().str.strip()
            df_ret = df_raw[status_col.isin(target_keywords)].copy()
            if not df_ret.empty:
                # Filter out rows that are already negative
                df_ret = filter_positive_only(df_ret)
                
                if not df_ret.empty:
                    cols_to_drop = [c for c in df_ret.columns if c.lower() == 'month']
                    if cols_to_drop: df_ret.drop(columns=cols_to_drop, inplace=True)
                    df_ret['Month'] = month_label
                    df_ret = reorder_columns_first(df_ret, 'Month')
                    df_up_returns = convert_to_returns(df_ret)

    return df_hr_returns, df_up_returns

def process_current_month(df):
    conn = prepare_sql_data(df)
    df_whole = pd.read_sql_query("SELECT * FROM processed_data", conn)

    try:
        df_hr = pd.read_sql_query("""
            SELECT * FROM processed_data WHERE 
            TRIM(UPPER(Courier_Status)) IN ('DELIVERED', 'INTRANSIT', 'IN TRANSIT', 'YET TO BE PICKUP', 'YET TO PICKUP')
            AND 
            (
                TRIM(UPPER(Pickup_Location)) IN ('FAR_LF', 'GLAUCUS GURGAON WAREHOUSE 3', 'YET TO BE PICKUP', 'YET TO PICKUP')
                OR 
                TRIM(UPPER(Pickup_Location)) LIKE '%HARYANA%'
            )
        """, conn)
    except: df_hr = pd.DataFrame()

    try:
        df_up = pd.read_sql_query("""
            SELECT * FROM processed_data WHERE 
            TRIM(UPPER(Courier_Status)) IN ('DELIVERED', 'INTRANSIT', 'IN TRANSIT', 'YET TO BE PICKUP', 'YET TO PICKUP')
            AND 
            TRIM(UPPER(Pickup_Location)) = 'NOIDA G-202'
        """, conn)
    except: df_up = pd.DataFrame()
    
    conn.close()
    return df_whole, df_hr, df_up

def generate_pivot_summary(df_merged):
    conn = sqlite3.connect(":memory:")
    
    # Ensure numeric columns before querying
    if 'Taxable_Amount' in df_merged.columns:
        df_merged['Taxable_Amount'] = pd.to_numeric(df_merged['Taxable_Amount'], errors='coerce').fillna(0)
    if 'Lineitem_quantity' in df_merged.columns:
        df_merged['Lineitem_quantity'] = pd.to_numeric(df_merged['Lineitem_quantity'], errors='coerce').fillna(0)
    
    df_merged.to_sql("data", conn, index=False, if_exists="replace")
    
    # --- QUERY FOR HR SUMMARY (With Items & Quantity) ---
    query_hr = """
        SELECT 
            Shipping_Province,
            Lineitem_name,
            SUM(Lineitem_quantity) as Total_Quantity,
            SUM(Taxable_Amount) as Total_Taxable
        FROM data
        WHERE Source_Warehouse = 'HR' AND Shipping_Province IS NOT NULL
        GROUP BY Shipping_Province, Lineitem_name
        ORDER BY Shipping_Province ASC, Lineitem_name ASC
    """
    
    # --- QUERY FOR UP SUMMARY (With Items & Quantity) ---
    query_up = """
        SELECT 
            Shipping_Province,
            Lineitem_name,
            SUM(Lineitem_quantity) as Total_Quantity,
            SUM(Taxable_Amount) as Total_Taxable
        FROM data
        WHERE Source_Warehouse = 'UP' AND Shipping_Province IS NOT NULL
        GROUP BY Shipping_Province, Lineitem_name
        ORDER BY Shipping_Province ASC, Lineitem_name ASC
    """

    try:
        df_summary_hr = pd.read_sql_query(query_hr, conn)
        df_summary_up = pd.read_sql_query(query_up, conn)
    except Exception as e:
        print(f"Pivot Error: {e}")
        df_summary_hr = pd.DataFrame()
        df_summary_up = pd.DataFrame()
        
    conn.close()
    return df_summary_hr, df_summary_up

def clean_and_format_final(df):
    cols = ['Total', 'Taxable_Amount', 'Lineitem_quantity']
    for c in cols:
        if c in df.columns:
            # Convert to numeric, but NO ROUNDING here
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df = fix_booleans(df)
    if 'Source_Warehouse' in df.columns:
        df.drop(columns=['Source_Warehouse'], inplace=True)
    return df

def append_with_gap(df_main, df_append):
    if df_append.empty: return df_main
    blank_row = pd.DataFrame([np.nan], index=[0]) 
    combined = pd.concat([df_main, blank_row, df_append], ignore_index=True)
    return combined

def save_processed_excel(whole, hr, up, month_name, filename):
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    whole = clean_and_format_final(whole)
    hr = clean_and_format_final(hr)
    up = clean_and_format_final(up)
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        up.to_excel(writer, sheet_name=f"{month_name} GSTR1 LEAF UP", index=False)
        hr.to_excel(writer, sheet_name=f"{month_name} GSTR1 LEAF HR", index=False)
        whole.to_excel(writer, sheet_name=f"{month_name} WHOLE DATA", index=False)
    return filename

def save_returns_excel(hr, up, month_name, filename):
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    hr = clean_and_format_final(hr)
    up = clean_and_format_final(up)
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        hr.to_excel(writer, sheet_name=f"{month_name} GSTR1 LEAF HR", index=False)
        up.to_excel(writer, sheet_name=f"{month_name} GSTR1 LEAF UP", index=False)
    return filename

def save_summary_only(hr_summary, up_summary, filename):
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        if not hr_summary.empty:
            hr_summary.to_excel(writer, sheet_name="HR_Itemized_Summary", index=False)
        else:
            pd.DataFrame({'Message': ['No Data']}).to_excel(writer, sheet_name="HR_Itemized_Summary", index=False)
            
        if not up_summary.empty:
            up_summary.to_excel(writer, sheet_name="UP_Itemized_Summary", index=False)
        else:
            pd.DataFrame({'Message': ['No Data']}).to_excel(writer, sheet_name="UP_Itemized_Summary", index=False)
            
    return filename

@app.route('/process', methods=['POST'])
def process_files():
    try:
        if 'file_current' not in request.files or 'file_prev' not in request.files:
            return jsonify({"error": "Missing files"}), 400
        
        file_curr = request.files['file_current']
        file_prev = request.files['file_prev']
        curr_month = request.form.get('month', 'DEC 2025').upper()
        prev_month = get_prev_month_name(curr_month)
        
        print(f"Processing Current Month ({curr_month})...")
        df_curr_raw = pd.read_excel(file_curr)
        c_whole, c_hr, c_up = process_current_month(df_curr_raw)
        
        print(f"Processing Previous Month Returns ({prev_month})...")
        p_hr_returns, p_up_returns = process_prev_month_returns(file_prev, prev_month)

        c_hr['Source_Warehouse'] = 'HR'
        p_hr_returns['Source_Warehouse'] = 'HR'
        c_up['Source_Warehouse'] = 'UP'
        p_up_returns['Source_Warehouse'] = 'UP'

        print("Generating Split Pivot Summary...")
        all_data = pd.concat([c_hr, p_hr_returns, c_up, p_up_returns], ignore_index=True)
        
        # --- NEW: Get Tuple of DataFrames (HR, UP) ---
        df_hr_summary, df_up_summary = generate_pivot_summary(all_data)

        print("Merging Returns into Current Sheets...")
        final_hr = append_with_gap(c_hr, p_hr_returns)
        final_up = append_with_gap(c_up, p_up_returns)
        
        curr_filename = f"Processed_{curr_month.replace(' ', '_')}.xlsx"
        save_processed_excel(c_whole, final_hr, final_up, curr_month, curr_filename)
        
        prev_filename = f"Returns_{prev_month.replace(' ', '_')}.xlsx"
        save_returns_excel(p_hr_returns, p_up_returns, prev_month, prev_filename)
        
        summary_filename = f"Summary_{curr_month.replace(' ', '_')}.xlsx"
        # --- NEW: Pass both summaries ---
        save_summary_only(df_hr_summary, df_up_summary, summary_filename)

        return jsonify({
            "message": "Processing Complete",
            "current_file": curr_filename,
            "prev_file": prev_filename,
            "summary_file": summary_filename
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
