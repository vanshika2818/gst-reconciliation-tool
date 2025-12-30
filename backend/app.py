from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
import pandas as pd
import sqlite3
import io
import os
from dateutil.relativedelta import relativedelta
from datetime import datetime

app = Flask(__name__)
CORS(app)

OUTPUT_FOLDER = 'outputs'
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

def get_prev_month_name(month_str):
    try:
        dt = datetime.strptime(month_str, "%b %Y")
        prev_dt = dt - relativedelta(months=1)
        return prev_dt.strftime("%b %Y").upper()
    except:
        return "PREV_MONTH"

def normalize_columns(df, preserve_taxable=False):
    """Standardizes column names."""
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

    tax_cols = [c for c in df.columns if c.strip().upper() in ['TAXABLE', 'TAXABLE AMOUNT', 'TAXABLE_AMOUNT']]
    if preserve_taxable:
        for t in tax_cols: renames[t] = 'Taxable_Amount'
    else:
        if tax_cols: df.drop(columns=tax_cols, inplace=True)

    if renames: df.rename(columns=renames, inplace=True)
    df.columns = [c.replace(" ", "_") for c in df.columns]
    
    # Remove duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]
    return df

def prepare_sql_data(df):
    df = normalize_columns(df, preserve_taxable=False)
    if 'Total' in df.columns:
        df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
        df['Taxable_Amount'] = (df['Total'] / 1.18).round(2)
    else:
        df['Taxable_Amount'] = 0
    
    df_str = df.astype(str)
    conn = sqlite3.connect(":memory:")
    df_str.to_sql("processed_data", conn, index=False, if_exists="replace")
    return conn

def convert_to_returns(df):
    """Multiplies Total, Taxable, and Quantity by -1."""
    cols_to_negate = ['Total', 'Taxable_Amount', 'Lineitem_quantity']
    for col in cols_to_negate:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) * -1
    return df

def fix_booleans(df):
    """Forces boolean columns to appear as 'True'/'False' strings."""
    for col in df.columns:
        if df[col].dtype == bool:
            df[col] = df[col].astype(str).replace({'True': 'True', 'False': 'False'})
        elif set(df[col].dropna().unique()).issubset({0, 1, 0.0, 1.0}):
            if "quantity" not in col.lower() and "amount" not in col.lower() and "price" not in col.lower():
                 df[col] = df[col].replace({1: 'True', 0: 'False', 1.0: 'True', 0.0: 'False'})
    return df

def reorder_columns_first(df, col_name):
    """Moves a specific column to the first position."""
    if col_name in df.columns:
        cols = [col_name] + [c for c in df.columns if c != col_name]
        return df[cols]
    return df

def process_prev_month_returns(file_storage, month_label):
    """
    Targets 'HR GSTR1' and 'UP GSTR1'. Filters 'Updated_Status'.
    Ensures EXACTLY ONE 'Month' column exists AND IS FIRST.
    """
    xl = pd.ExcelFile(file_storage)
    sheet_names = xl.sheet_names
    print(f"   [DEBUG] All Sheets: {sheet_names}")
    
    df_hr_returns = pd.DataFrame()
    df_up_returns = pd.DataFrame()

    target_keywords = ['cancelled', 'free order', 'lost', 'refunded', 'rtoed']

    hr_sheet = next((s for s in sheet_names if "HR" in s.upper() and "GSTR1" in s.upper() and "PVT" not in s.upper()), None)
    up_sheet = next((s for s in sheet_names if "UP" in s.upper() and "GSTR1" in s.upper() and "PVT" not in s.upper()), None)

    # --- PROCESS HR ---
    if hr_sheet:
        print(f"   Reading HR Sheet: {hr_sheet}")
        df_raw = pd.read_excel(file_storage, sheet_name=hr_sheet)
        df_raw = normalize_columns(df_raw, preserve_taxable=True)
        if 'Updated_Status' in df_raw.columns:
            status_col = df_raw['Updated_Status'].astype(str).str.lower().str.strip()
            df_ret = df_raw[status_col.isin(target_keywords)].copy()
            
            if not df_ret.empty:
                print(f"   ✅ Found {len(df_ret)} HR Returns.")
                
                # Remove ANY existing Month columns
                cols_to_drop = [c for c in df_ret.columns if c.lower() == 'month']
                if cols_to_drop:
                    df_ret.drop(columns=cols_to_drop, inplace=True)
                
                # Add Month & Move to Front
                df_ret['Month'] = month_label
                df_ret = reorder_columns_first(df_ret, 'Month')
                
                df_hr_returns = convert_to_returns(df_ret)

    # --- PROCESS UP ---
    if up_sheet:
        print(f"   Reading UP Sheet: {up_sheet}")
        df_raw = pd.read_excel(file_storage, sheet_name=up_sheet)
        df_raw = normalize_columns(df_raw, preserve_taxable=True)
        if 'Updated_Status' in df_raw.columns:
            status_col = df_raw['Updated_Status'].astype(str).str.lower().str.strip()
            df_ret = df_raw[status_col.isin(target_keywords)].copy()
            
            if not df_ret.empty:
                print(f"   ✅ Found {len(df_ret)} UP Returns.")
                
                # Remove ANY existing Month columns
                cols_to_drop = [c for c in df_ret.columns if c.lower() == 'month']
                if cols_to_drop:
                    df_ret.drop(columns=cols_to_drop, inplace=True)
                
                # Add Month & Move to Front
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
            TRIM(UPPER(Courier_Status)) IN ('DELIVERED', 'INTRANSIT', 'IN TRANSIT', 'YET TO BE PICKUP')
            AND 
            TRIM(UPPER(Pickup_Location)) IN ('FAR_LF', 'GLAUCUS GURGAON WAREHOUSE 3', 'YET TO BE PICKUP')
        """, conn)
    except: df_hr = pd.DataFrame()

    try:
        df_up = pd.read_sql_query("""
            SELECT * FROM processed_data WHERE 
            TRIM(UPPER(Courier_Status)) IN ('DELIVERED', 'INTRANSIT', 'IN TRANSIT', 'YET TO BE PICKUP')
            AND 
            TRIM(UPPER(Pickup_Location)) = 'NOIDA G-202'
        """, conn)
    except: df_up = pd.DataFrame()
    
    conn.close()
    return df_whole, df_hr, df_up

def clean_and_format_final(df):
    cols = ['Total', 'Taxable_Amount', 'Lineitem_quantity']
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df = fix_booleans(df)
    return df

# --- SAVER FOR CURRENT MONTH ---
def save_current_excel(whole, hr, up, month_name, filename):
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    whole = clean_and_format_final(whole)
    hr = clean_and_format_final(hr)
    up = clean_and_format_final(up)

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        up.to_excel(writer, sheet_name=f"{month_name} GSTR1 LEAF UP PVT", index=False)
        up.to_excel(writer, sheet_name=f"{month_name} GSTR1 LEAF UP", index=False)
        hr.to_excel(writer, sheet_name=f"{month_name} GSTR1 LEAF HR PVT", index=False)
        hr.to_excel(writer, sheet_name=f"{month_name} GSTR1 LEAF HR", index=False)
        whole.to_excel(writer, sheet_name=f"{month_name} WHOLE DATA", index=False)
    return filename

# --- SAVER FOR RETURNS ---
def save_returns_excel(hr, up, month_name, filename):
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    hr = clean_and_format_final(hr)
    up = clean_and_format_final(up)

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        hr.to_excel(writer, sheet_name=f"{month_name} GSTR1 LEAF HR", index=False)
        up.to_excel(writer, sheet_name=f"{month_name} GSTR1 LEAF UP", index=False)
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
        
        curr_filename = f"Processed_{curr_month.replace(' ', '_')}.xlsx"
        save_current_excel(c_whole, c_hr, c_up, curr_month, curr_filename)

        print(f"Processing Previous Month Returns ({prev_month})...")
        p_hr_returns, p_up_returns = process_prev_month_returns(file_prev, prev_month)

        prev_filename = f"Returns_{prev_month.replace(' ', '_')}.xlsx"
        save_returns_excel(p_hr_returns, p_up_returns, prev_month, prev_filename)

        return jsonify({
            "message": "Processing Complete",
            "current_file": curr_filename,
            "prev_file": prev_filename
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)