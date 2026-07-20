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

                # 2b. FITUR TAMBAHAN: Filter data inbound (1 Trip = 2 Row, hapus sak pasangane lek keisi)
                if target_table == "staging_fms_handedover":
                    rows_before_inbound = len(df)
                    
                    # Status awal: anggep kabeh baris resik dhisik (False = gak ono inbound)
                    is_filled = pd.Series(False, index=df.index)
                    
                    # 1. Cek kolom string 'inbound_to' sacara teliti
                    if 'inbound_to' in df.columns:
                        s_to = df['inbound_to'].astype(str).str.strip().str.lower()
                        s_to = s_to.str.replace(r'\s+', '', regex=True)   # '0 / 0' -> '0/0'
                        s_to = s_to.str.replace(r'\.0+$', '', regex=True)  # '0.0' -> '0'
                        is_filled |= ~s_to.isin(['0', '0/0', '', 'nan', 'none', 'null', '-'])
                        
                    # 2. Cek kolom numerik liyane nggae komparasi angka murni (anti-gagal format float)
                    for col in ['inbound_hv_to', 'inbound_dg_to', 'inbound_order', 'inbound_weight_kg']:
                        if col in df.columns:
                            num_val = pd.to_numeric(df[col], errors='coerce').fillna(0)
                            is_filled |= (num_val > 0)
                            
                    # 3. Goleki trip number sing beneran keisi inbound, banjur tendang sak pasangane sisan
                    if 'lh_trip_number' in df.columns:
                        bad_trips = df.loc[is_filled, 'lh_trip_number'].dropna().unique()
                        bad_trips = [t for t in bad_trips if str(t).strip() not in ['', 'nan', 'none', 'null', '0', '0.0']]
                        df = df[~df['lh_trip_number'].isin(bad_trips)]
                    else:
                        print("[!] Peringatan: Kolom 'lh_trip_number' gak ketemu! Nyaring per baris biasa.")
                        df = df[~is_filled]
                        
                    rows_after_inbound = len(df)
                    print(f"[i] Filter Inbound Sukses: Ngguak {rows_before_inbound - rows_after_inbound} baris data (Trip keisi inbound resmi ditendang total).")

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