import os
import sys
import time
import sqlite3
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Hardcoded folder utama teko Explorer-mu
BASE_DIR = r"C:\Users\5CG40413SD-SPXOps\Desktop\SSS-Terminal_Data\WinPython_Portable\WPy64-313130"

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
MASTER_SPREADSHEET_NAME = "Configuration Library"

def auto_scan_json_key():
    """Scan kabeh file nang folder, angger ono konco .json langsung sikat!"""
    folder_targets = [BASE_DIR, os.getcwd(), "."]
    for folder in folder_targets:
        if not os.path.exists(folder):
            continue
        try:
            files = os.listdir(folder)
            for f in files:
                if f.endswith('.json') and ('key' in f.lower() or 'service' in f.lower()):
                    return os.path.join(folder, f)
            for f in files:
                if f.endswith('.json'):
                    return os.path.join(folder, f)
        except Exception:
            pass
    return None

def auto_scan_database():
    """Scan database .db, saiki tak kunci kudu ngutamakan spx_terminal_data.db"""
    folder_targets = [BASE_DIR, os.getcwd(), "."]
    
    # PRIORITAS 1: Golek sing bener-bener pas omah asline
    for folder in folder_targets:
        if not os.path.exists(folder):
            continue
        target_pasti = os.path.join(folder, "spx_terminal_data.db")
        if os.path.exists(target_pasti):
            return target_pasti
            
    # PRIORITAS 2: Pasrah brutal scan lek pancen gak ketemu
    for folder in folder_targets:
        if not os.path.exists(folder):
            continue
        try:
            files = os.listdir(folder)
            for f in files:
                if f.endswith('.db') and 'spx' in f.lower():
                    return os.path.join(folder, f)
            for f in files:
                if f.endswith('.db'):
                    return os.path.join(folder, f)
        except Exception:
            pass
    return None

def standardise_date(input_date):
    input_date = input_date.strip()
    try:
        dt = datetime.strptime(input_date, "%d-%b-%Y")
        return f"{dt.day}-{dt.strftime('%b')}-{dt.year}"
    except ValueError:
        pass

    try:
        dt = datetime.strptime(input_date, "%d-%m-%Y")
        return f"{dt.day}-{dt.strftime('%b')}-{dt.year}"
    except ValueError:
        # Filter ben gak ngebaki terminal pas moco teks header / panduan gdocs
        teks_sampah = ["DATE", "MAX TIME NEEDED TO BE FILLED", ""]
        is_sampah = any(x in input_date.upper() for x in teks_sampah) or "[TYPING]" in input_date.upper()
        
        if not is_sampah:
            print(f"[!] Format tanggal salah nang baris: '{input_date}'")
        return None

def main():
    print("\n========================================================")
    print("    GOOGLE SHEETS GDGP PULLER v2.1 [SINKRON TOTAL]    ")
    print("========================================================\n")

    key_file_path = auto_scan_json_key()
    if not key_file_path:
        print("[!] ERROR CRITICAL: File JSON beneran gak ono nang folder!")
        sys.exit(1)
    print(f"[✓] Kunci Google API Ketemu: '{key_file_path}'")

    db_file_path = auto_scan_database()
    if not db_file_path:
        print("[!] ERROR CRITICAL: File Database .db beneran gak ono nang folder!")
        sys.exit(1)
    print(f"[✓] Database SQLite Dikunci neng: '{db_file_path}'")

    tgl_user = input("Masukkan tanggal target penarikan (e.g. 06-07-2026): ")
    target_date = standardise_date(tgl_user)
    
    if not target_date:
        print("[!] Format tanggal salah. Proses batal.")
        sys.exit(1)

    print(f"[+] Tanggal Kuncian Target: '{target_date}'")

    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()

    print(f"[+] Ngakses Configuration Library...")
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(key_file_path, SCOPE)
        gc = gspread.authorize(creds)
        master_sh = gc.open(MASTER_SPREADSHEET_NAME)
        config_worksheet = master_sh.worksheet("Size Manual Koli")
        config_rows = config_worksheet.get_all_records()
    except Exception as e:
        print(f"[!] Gagal ngakses Master Configuration: {str(e)}")
        conn.close()
        sys.exit(1)

    live_configs = [row for row in config_rows if str(row.get('STATUS', '')).strip().upper() == 'LIVE']

    if not live_configs:
        print("[!] Gak ono Vendor sing statuse 'LIVE'.")
        conn.close()
        sys.exit(0)

    total_inserted_all_vendor = 0

    for config in live_configs:
        vendor_name = config.get('VENDOR', '').strip()
        unique_code = str(config.get('UNIQUE CODE IN GDOCS NAME', '')).strip()
        gdocs_link_name = str(config.get('SUBJECT LINK GDOCS', '')).strip()
        sheet_target_tab = str(config.get('SHEET TARGET', '')).strip() 

        print(f"--------------------------------------------------------")
        print(f"[>] Memproses Vendor: {vendor_name}")
        
        if not gdocs_link_name or not sheet_target_tab:
            print(f"[-] Skip: Link/Sheet Target kosong gae {vendor_name}!")
            continue

        max_retries = 3
        success_pull = False
        rows_to_save = []
        
        for attempt in range(1, max_retries + 1):
            try:
                if "docs.google.com/spreadsheets" in gdocs_link_name:
                    target_sh = gc.open_by_url(gdocs_link_name)
                elif len(gdocs_link_name) >= 40 and "/" not in gdocs_link_name:
                    target_sh = gc.open_by_key(gdocs_link_name)
                else:
                    target_sh = gc.open(gdocs_link_name)
                
                sheet_title = target_sh.title
                if unique_code.upper() not in sheet_title.upper():
                    print(f"[X] CRITICAL: Kode Unik '{unique_code}' GAK MATCH karo judul file!")
                    break 
                
                target_ws = target_sh.worksheet(sheet_target_tab)
                all_values = target_ws.get_all_values()
                
                if not all_values:
                    success_pull = True
                    break
                
                header_skipped = False
                for row in all_values:
                    if not header_skipped:
                        header_skipped = True
                        continue
                        
                    if len(row) == 0 or not row[0].strip():
                        continue
                        
                    row_date = str(row[0]).strip()
                    std_row_date = standardise_date(row_date)
                    
                    if std_row_date == target_date:
                        clean_row = [str(cell).strip() for cell in row[:15]]
                        
                        while len(clean_row) < 15:
                            clean_row.append("")
                        
                        is_fulfilled = all(cell != "" for cell in clean_row)
                        status_tag = "GDGP_OK" if is_fulfilled else "GDGP_WARN"
                        current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        full_payload = clean_row + [status_tag, current_timestamp]
                        rows_to_save.append(full_payload)
                
                success_pull = True
                break 
                
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(attempt * 1)

        if success_pull and rows_to_save:
            try:
                query_insert = """
                    INSERT INTO gdocs_pulled_data (
                        date, vendor, origin, destination, lt_number, to_number, 
                        gross_weight, qty_parcel, remarks, slot, driver_name, nopol, 
                        vehicle_type, ata_origin, atd_origin, gdgp_status, pulled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.executemany(query_insert, rows_to_save)
                conn.commit()
                print(f"[✓] SUKSES! {len(rows_to_save)} baris mlebu kanggo {vendor_name}.")
                total_inserted_all_vendor += len(rows_to_save)
                
            except Exception as sql_err:
                print(f"[!] Gagal nulis SQLite: {str(sql_err)}")
                conn.rollback()

    conn.close()
    print("\n========================================================")
    print(f"  PULLER KELAR TOTAL. {total_inserted_all_vendor} BARIS REAL SUKSES MASUK TRANSIT!")
    print("========================================================\n")

if __name__ == "__main__":
    import atexit
    def execute_git_push_addon():
        import subprocess
        print("\n[+] Running Automatic Git Push Addon...")
        try:
            subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True)
            subprocess.run(["git", "add", "."], capture_output=True)
            subprocess.run(["git", "commit", "-m", "System Auto-Update: Real-Time Pipeline Sync"], capture_output=True)
            subprocess.run(["git", "push", "origin", "main"], capture_output=True)
            print("[✓] Git Push Addon executed successfully!")
        except Exception as e:
            print(f"[!] Git Push Addon error: {e}")
    atexit.register(execute_git_push_addon)
    main()