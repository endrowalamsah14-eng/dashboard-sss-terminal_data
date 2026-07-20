import os
import pandas as pd
import sqlite3
import re

# ==========================================
# CONFIGURATION & ABSOLUTE PATH PROTECTION
# ==========================================
DB_NAME = "spx_terminal_data.db"

# Ngunci jalur folder utama project ben anti-mleset mboh mlayu soko CMD endi wae
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Map konfigurasi menu, kamar tabel, lan jalur folder absolute
MENU_CONFIG = {
    "1": {
        "folder_path": os.path.join(BASE_DIR, "fms_handedover"),
        "table_name": "staging_fms_handedover",
        "label": "FMS HANDEDOVER"
    },
    "2": {
        "folder_path": os.path.join(BASE_DIR, "fms_pending"),
        "table_name": "staging_fms_pending",
        "label": "FMS PENDING"
    }
}

def sanitize_column_name(col_name):
    """Mengubah jeneng kolom dadi format standar database (lowercase, anti-spasi)"""
    if pd.isna(col_name) or str(col_name).strip() == "":
        return "unnamed_column"
    s = str(col_name).strip().lower()
    s = re.sub(re.compile(r'[^a-z0-9_]'), '_', s)
    s = re.sub(re.compile(r'_+'), '_', s)
    return s.strip('_')

def run_pipeline():
    print("\n=============================================")
    print("      EUROPEAN-GRADE PIPELINE SELECTOR       ")
    print("=============================================")
    print(" Pilihen data sing kate mbok upload saiki, Ndrow:")
    print(" [1] Process FMS Handedover -> staging_fms_handedover")
    print(" [2] Process FMS Pending    -> staging_fms_pending")
    print("=============================================")
    
    pilihan = input("Lebokno pilihanmu (1 utawa 2): ").strip()
    
    if pilihan not in MENU_CONFIG:
        print("[X] Pilihan ngawur! Gak ono neng menu. Script ditutup.")
        return
        
    config = MENU_CONFIG[pilihan]
    target_folder = config["folder_path"]
    target_table = config["table_name"]
    
    print(f"\n[*] Memulai Pipeline kanggo: {config['label']}")
    print(f"[*] Jalur Folder: {target_folder}")
    print(f"[*] Kamar Kamar SQLite: {target_table}")
    print("---------------------------------------------")

    if not os.path.exists(target_folder):
        print(f"[X] Folder '{target_folder}' gak ketemu! Pastikno foldere wis ono.")
        return

    files = [f for f in os.listdir(target_folder) if os.path.isfile(os.path.join(target_folder, f))]
    if not files:
        print("[!] Folder kosong melompong, Ndrow.")
        return

    conn = sqlite3.connect(os.path.join(BASE_DIR, DB_NAME))
    total_rows_inserted = 0
    
    # Mode pertama 'replace' nggo nggusah omah lawas lan nggawe struktur anyar sing fresh,
    # file sabanjure otomatis 'append'.
    insert_mode = "replace"

    for file in files:
        file_path = os.path.join(target_folder, file)
        print(f"[*] Lagi moco file: {file}")
        
        df = None
        
        # Jalur 1: Coba moco format CSV dhisik
        try:
            df = pd.read_csv(file_path, header=0)
            print("[✓] File sukses diwoco nggae Engine CSV.")
        except Exception:
            # Jalur 2: Lek gagal CSV, coba format Excel
            try:
                df = pd.read_excel(file_path, sheet_name=0, usecols="A:AX", header=0)
                print("[✓] File sukses diwoco nggae Engine Excel/XLS.")
            except Exception as e_read:
                print(f"[X] Gagal total moco {file}. Error: {e_read}")
                continue

        if df is not None:
            try:
                # 1. Sanitasi jeneng kolom dhisik ben iso diwoco script filter
                df.columns = [sanitize_column_name(col) for col in df.columns]
                
                # 2. FITUR UTAMA: Filter ngguak data 'By Land' (Mung jupuk Sea & Air)
                if 'trip_type' in df.columns:
                    rows_before = len(df)
                    # Mung nyisako sing ngandhut kata 'sea' utawa 'air' (case-insensitive)
                    df = df[df['trip_type'].astype(str).str.lower().str.contains('sea|air', na=False)]
                    rows_after = len(df)
                    print(f"[i] Filter Sukses: Ngguak {rows_before - rows_after} baris data 'By Land'.")
                else:
                    print("[!] Peringatan: Kolom 'trip_type' gak ketemu! Data gak disaring.")

                # 2b. FITUR TAMBAHAN IDE BARU: Filter adhedhasar keisine kolom 'unloaded_time'
                if target_table == "staging_fms_handedover":
                    rows_before_inbound = len(df)
                    
                    if 'unloaded_time' in df.columns and 'lh_trip_number' in df.columns:
                        # Resik-resik string nggo mriksa isine unloaded_time
                        s_unloaded = df['unloaded_time'].astype(str).str.strip().str.lower()
                        
                        # Dianggep keisi TANGGAL lek dudu strip (-), udu kosong, lan dudu NaN/NULL bawaan Pandas
                        is_unloaded_filled = df['unloaded_time'].notna() & (~s_unloaded.isin(['', 'nan', 'none', 'null', '-']))
                        
                        # Goleki kabeh unique 'lh_trip_number' sing salah siji barise wis keisi tanggal
                        bad_trips = df.loc[is_unloaded_filled, 'lh_trip_number'].dropna().unique()
                        bad_trips = [t for t in bad_trips if str(t).strip() not in ['', 'nan', 'none', 'null']]
                        
                        # Hapus sak pasangane sisan (trip number sing wis sukses di-unload)
                        df = df[~df['lh_trip_number'].isin(bad_trips)]
                    else:
                        print("[!] Peringatan: Kolom 'unloaded_time' utawa 'lh_trip_number' ora ketemu!")
                        
                    rows_after_inbound = len(df)
                    print(f"[i] Filter Unloaded Time Sukses: Ngguak {rows_before_inbound - rows_after_inbound} baris data (Trip wis di-unload resmi ditendang total).")

                # 3. Tambah kolom asal file
                df['source_file'] = file
                
                # 4. Jebretno langsung menyang SQLite kamar masing-masing
                df.to_sql(target_table, conn, if_exists=insert_mode, index=False)
                print(f"[✓] Sukses nglebokno {len(df)} baris menyang '{target_table}' nggae mode '{insert_mode}'.")
                
                total_rows_inserted += len(df)
                insert_mode = "append"  # File sateruse nempel neng ngisore
                
            except Exception as e_db:
                print(f"[X] Gagal nglebokno data menyang SQLite. Error: {e_db}")
        print("-" * 45)

    conn.close()
    print(f"\n=== PIPELINE SELESAI: Total {total_rows_inserted} baris resmi mlebu Kamar '{target_table}' ===")

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
    run_pipeline()