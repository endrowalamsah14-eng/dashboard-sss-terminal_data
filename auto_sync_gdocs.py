import os
import sys
import time
import sqlite3
import re
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. SETUP CONFIGURATION & CREDENTIALS
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
KEY_FILE = "service-account-key.json"
DB_NAME = "spx_terminal_data.db"
MASTER_SPREADSHEET_NAME = "Configuration Library"

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
        print("[!] Format tanggal salah! Gunakno format DD-MM-YYYY utawa d-MMM-YYYY.")
        return None

def calculate_sla_status(start_time_str, end_dt, start_dt_fallback):
    """Fungsi ngitung status SLA dhedhasar start_time baris data"""
    duration_minutes = 0
    if start_time_str and start_time_str != "UNKNOWN":
        try:
            actual_start_dt = None
            for fmt in ["%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M"]:
                try:
                    actual_start_dt = datetime.strptime(start_time_str.strip(), fmt)
                    break
                except ValueError:
                    continue
            
            if actual_start_dt:
                duration_minutes = (end_dt - actual_start_dt).total_seconds() / 60
            else:
                duration_minutes = (end_dt - start_dt_fallback).total_seconds() / 60
        except Exception:
            duration_minutes = (end_dt - start_dt_fallback).total_seconds() / 60
    else:
        duration_minutes = (end_dt - start_dt_fallback).total_seconds() / 60

    return "ONTIME" if duration_minutes <= 30 else "LATE"

def main():
    print("\n========================================================")
    print("    GOOGLE SHEETS AUTO-SYNC ENGINE v3.2 (VERTICALLY LOG) ")
    print("========================================================\n")

    # ---- 🛡️ GENERATE BATCH ID OTOMATIS (URUT BARIS ANYAR) ----
    next_id_number = 1
    if os.path.exists(DB_NAME):
        try:
            audit_conn = sqlite3.connect(DB_NAME)
            audit_cursor = audit_conn.cursor()
            
            # 🎯 MAINTENANCE ZONE: Struktur pengaman kene disinkronkan nggawa Composite PK
            audit_cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_records (
                    batch_id TEXT, 
                    lt_number TEXT, 
                    sync_date TEXT, 
                    total_rows_pushed INTEGER, 
                    start_time TEXT, 
                    end_time TEXT, 
                    status TEXT,
                    PRIMARY KEY (batch_id, lt_number)
                )
            """)
            audit_cursor.execute("SELECT batch_id FROM batch_records")
            all_rows = audit_cursor.fetchall()
            max_num = 0
            for row in all_rows:
                match = re.match(r'ID(\d+)', str(row[0]))
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
            next_id_number = max_num + 1
            audit_conn.close()
        except Exception as e:
            print(f"[!] Gagal ngecek Batch ID terakhir: {e}")

    batch_id = f"ID{next_id_number:03d}"
    start_dt = datetime.now()
    sync_date = start_dt.strftime("%Y-%m-%d")

    if not os.path.exists(KEY_FILE):
        print(f"[!] Error: File '{KEY_FILE}' ora ditemokno neng folder iki!")
        sys.exit(1)

    tgl_user = input("Masukkan tanggal target (e.g. 10-07-2026 utawa 10-Jul-2026): ")
    target_date = standardise_date(tgl_user)
    
    if not target_date:
        print("[!] Process dibatalkan mergo format tanggal salah.")
        sys.exit(1)

    print(f"\n[+] Tanggal ter-standarisasi: '{target_date}'")

    if not os.path.exists(DB_NAME):
        print(f"[!] Error: Database '{DB_NAME}' ora ono neng folder iki!")
        sys.exit(1)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query_check = """
        SELECT COUNT(*) FROM production_size_manual_koli 
        WHERE date = ? AND tag = 'PENDING'
    """
    cursor.execute(query_check, (target_date,))
    total_pending = cursor.fetchone()[0]

    if total_pending == 0:
        print(f"[!] Gak ono data neng SQLite gawa status 'PENDING' kanggo tanggal {target_date}.")
        conn.close()
        sys.exit(0)

    print(f"[✓] Ketemu {total_pending} baris data 'PENDING' neng SQLite. Siap di-upload.")

    print(f"[+] Ngakses Master Google Sheets API nggawa '{KEY_FILE}'...")
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(KEY_FILE, SCOPE)
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
        print("[!] Peringatan: Ora ono Vendor sing statuse 'Live' neng Configuration Library!")
        conn.close()
        sys.exit(1)

    # 🎯 TEMPAT PENAMPUNGAN LOG REKAP PER LT NUMBER
    lt_summary_records = {}

    for config in live_configs:
        vendor_name = config.get('VENDOR', '')
        gdocs_link_name = str(config.get('SUBJECT LINK GDOCS', '')).strip()
        sheet_target_tab = config.get('SHEET TARGET', '')
        trip_type_config = config.get('TRIP TYPE IDENTIFICATION', '')

        print(f"\n--------------------------------------------------------")
        print(f"[>] Memproses Vendor: {vendor_name} ({trip_type_config})")

        query_data = """
            SELECT 
                date, vendor, origin, destination, lt_number, to_number, 
                gross_weight, qty_parcel, remarks, slot, driver_name, nopol, 
                vehicle_type, ata_origin, atd_origin
            FROM production_size_manual_koli
            WHERE date = ? AND vendor = ? AND tag = 'PENDING'
        """
        
        if vendor_name in ['CKL', 'AB Cargo']:
            query_data += " AND trip_type = ?"
            cursor.execute(query_data, (target_date, vendor_name, trip_type_config))
        else:
            cursor.execute(query_data, (target_date, vendor_name))
            
        rows_to_upload = cursor.fetchall()

        if not rows_to_upload:
            print(f"[-] Gak ono data PENDING neng SQLite kanggo Vendor {vendor_name} [{trip_type_config}].")
            continue

        print(f"[+] Menarik {len(rows_to_upload)} baris data seko SQLite...")

        payload = []
        for r in rows_to_upload:
            clean_row = ["" if val is None else val for val in r]
            payload.append(clean_row)

        max_retries = 3
        success_upload = False
        
        for attempt in range(1, max_retries + 1):
            try:
                if "docs.google.com/spreadsheets" in gdocs_link_name:
                    target_sh = gc.open_by_url(gdocs_link_name)
                elif len(gdocs_link_name) >= 40 and "/" not in gdocs_link_name:
                    target_sh = gc.open_by_key(gdocs_link_name)
                else:
                    target_sh = gc.open(gdocs_link_name)
                
                target_ws = target_sh.worksheet(sheet_target_tab)
                
                # Goleki baris kosong khusus teko Kolom A wae
                col_a_values = target_ws.col_values(1)
                next_blank_row_col_a = len(col_a_values) + 1
                
                range_target = f"A{next_blank_row_col_a}"
                target_ws.update(range_name=range_target, values=payload, value_input_option="USER_ENTERED")
                
                print(f"[✓] SUCCESS! Data {vendor_name} kasil nemplek lurus teko {range_target}.")
                success_upload = True
                
                # 🎯 REKAP DATA PER LT_NUMBER SECARA SPESIFIK
                for r in rows_to_upload:
                    lt_num = str(r[4]).strip() if r[4] else "UNKNOWN"
                    atd_time = str(r[14]).strip() if r[14] else "UNKNOWN"
                    
                    if lt_num not in lt_summary_records:
                        lt_summary_records[lt_num] = {
                            "total_rows": 0,
                            "start_time": atd_time
                        }
                    lt_summary_records[lt_num]["total_rows"] += 1
                
                break
                
            except Exception as e:
                print(f"[!] Kendala Google API Percobaan {attempt}: {type(e).__name__} - {str(e)}")
                time.sleep(2)

        if success_upload:
            if vendor_name in ['CKL', 'AB Cargo']:
                query_update = """
                    UPDATE production_size_manual_koli
                    SET tag = 'SUCCESS'
                    WHERE date = ? AND vendor = ? AND tag = 'PENDING' AND trip_type = ?
                """
                cursor.execute(query_update, (target_date, vendor_name, trip_type_config))
            else:
                query_update = """
                    UPDATE production_size_manual_koli
                    SET tag = 'SUCCESS'
                    WHERE date = ? AND vendor = ? AND tag = 'PENDING'
                """
                cursor.execute(query_update, (target_date, vendor_name))
            conn.commit()

    # ---- 📝 TEMBAK LOG BATCH SECARA VERTIKAL PER LT_NUMBER (REKAP JUARA) ----
    end_dt = datetime.now()
    end_time = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    if lt_summary_records:
        print(f"\n========================================================")
        print(f"[📝] MEMULAI PROSES PENULISAN VERTIKAL NENG BATCH_RECORDS")
        print(f"========================================================")
        
        try:
            # Loop saben LT Number unik kanggo dijadikan baris anyar dewe-dewe mengisor
            for lt_number_key, data_info in sorted(lt_summary_records.items()):
                total_pushed_for_this_lt = data_info["total_rows"]
                start_time_for_this_lt = data_info["start_time"]
                
                # Hitung status SLA murni per LT Number adhedhasar atd_origin-ne dewe
                status_sla_for_this_lt = calculate_sla_status(start_time_for_this_lt, end_dt, start_dt)
                
                cursor.execute("""
                    INSERT INTO batch_records (batch_id, lt_number, sync_date, total_rows_pushed, start_time, end_time, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (batch_id, lt_number_key, sync_date, total_pushed_for_this_lt, start_time_for_this_lt, end_time, status_sla_for_this_lt))
                
                print(f"[✓] Vertikal Log -> Batch: {batch_id} | LT: {lt_number_key} | Rows: {total_pushed_for_this_lt} | Status: {status_sla_for_this_lt}")
            
            conn.commit()
            print(f"\n[✓] SYSTEM GUARD: Kabeh {len(lt_summary_records)} LT Number kasil direkap rapi mengisor!")
        except Exception as e:
            print(f"[!] Gagal nulis vertikal neng batch_records: {e}")

    conn.close()
    print("\n========================================================")
    print("    PROSES SELESAI & EXIT TOTAL... TERMINAL BEBAS NDROW! ")
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