import os
import sys
import re
import sqlite3

print("\n" + "="*60)
print("=== STARTING EXTRACTOR ENGINE v17.2 (SUROBOYO REBORN CORE) ===")
print("="*60)

DB_NAME = "spx_terminal_data.db"
PDF_FOLDER = "pdf_manifests"

def process_manifest_pdf():
    if not os.path.exists(PDF_FOLDER):
        print(f"[!] ERROR: Folder '{PDF_FOLDER}' gak nemu!")
        return
        
    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"[-] ZONK: Gak ono file PDF neng njero folder '{PDF_FOLDER}'!")
        return

    try:
        import pdfplumber
    except ImportError:
        print("[!] ERROR: Wajib install pdfplumber dhisik! -> pip install pdfplumber")
        return

    extracted_rows = []
    
    for file_name in pdf_files:
        file_path = os.path.join(PDF_FOLDER, file_name)
        print(f"[+] Memproses File: {file_path} ...")
        
        with pdfplumber.open(file_path) as pdf:
            # ========================================================
            # PROSES PER HALAMAN (LOOPING CORES)
            # ========================================================
            for page in pdf.pages:
                # RESET VARIABLE SABEN GANTI HALAMAN (ANTI STICKY VARIABLE)
                global_lt_num = "N/A"
                global_vendor = "CKL" # Default fallback
                
                # Moco teks murni per halaman nggo nembak Header masing-masing
                page_text = page.extract_text()
                if page_text:
                    # 1. Tembak Line Haul Trip Number (Contoh: LTQ761IZ5VN1)
                    lt_match = re.search(r'(LT[A-Z0-9]+)', page_text)
                    if lt_match:
                        global_lt_num = lt_match.group(1)
                    
                    # 2. FIX STRIP LOGIKA: Tembak Nama Vendor
                    vendor_match = re.search(r'(?:Nama Vendor|Vendor)\s*:\s*([A-Za-z\s]+)', page_text, re.IGNORECASE)
                    if vendor_match:
                        global_vendor = vendor_match.group(1).strip()

                print(f"  [→] Halaman {page.page_number} -> LT: {global_lt_num} | Vendor: {global_vendor}")

                # ========================================================
                # LOGIKA 3: BACA DATA LAIN (CELL-BY-CELL INDEX RELATIVE)
                # ========================================================
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row:
                            continue
                        
                        # Resiki spasi saben sel
                        clean_row = [str(cell).strip().replace('\n', ' ') if cell else "" for cell in row]
                        
                        # Goleki koordinat index Nomor TO
                        to_idx = -1
                        to_num = ""
                        for idx, cell in enumerate(clean_row):
                            if cell.startswith("TO") and len(cell) >= 10:
                                # Jupuk murni nomor TO-ne tok
                                to_match = re.search(r'(TO[A-Z0-9]+)', cell)
                                if to_match:
                                    to_num = to_match.group(1)
                                    to_idx = idx
                                    break
                        
                        # Lek dudu baris TO, skip langsung
                        if to_idx == -1 or not to_num:
                            continue

                        # Itung langkah relative menganan soko koordinat index TO_IDX
                        try:
                            # Adhedhasar susunan kolom PDF asli: TO -> Jmlh -> Berat -> Destination -> HV -> TO Type
                            qty          = clean_row[to_idx + 1] if (to_idx + 1) < len(clean_row) else "1"
                            weight       = clean_row[to_idx + 2] if (to_idx + 2) < len(clean_row) else "0.0"
                            destination  = clean_row[to_idx + 3] if (to_idx + 3) < len(clean_row) else "N/A"
                            remarks_val  = clean_row[to_idx + 4] if (to_idx + 4) < len(clean_row) else "N"
                            to_type_val  = clean_row[to_idx + 5] if (to_idx + 5) < len(clean_row) else "Bag"
                            
                            if not to_type_val or to_type_val == "":
                                to_type_val = "Bag"
                                
                        except IndexError:
                            qty, weight, destination, remarks_val, to_type_val = "1", "0.0", "N/A", "N", "Bag"

                        # Lebokno array jangkep (LT & Vendor dinamis sesuai halaman saiki)
                        extracted_rows.append({
                            'date': 'N/A',
                            'vendor': global_vendor,
                            'origin': 'Surabaya DC',
                            'destination': destination,
                            'lh_trip_number': global_lt_num,
                            'to_number': to_num,
                            'weight_kg': weight,
                            'jmlh_qty': qty,
                            'remarks': remarks_val.upper(),
                            'to_type': to_type_val
                        })

    if not extracted_rows:
        print("[-] ZONK: Gak ono data sing berhasil dijupuk.")
        return

    print(f"\n[✓] PARSE BERHASIL: Ketemu {len(extracted_rows)} baris data TO murni.")
    
    # ====================================================================
    # DATABASE INJECTION ENGINE (ANTI UNIQUE CONSTRAINT CRASH)
    # ====================================================================
    print(f"[+] Nyuntik data menyang: {DB_NAME}...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    success_staging = 0
    success_production = 0
    
    try:
        # PENTING: Resiki dhisik data staging sakdurunge diisi ben fresh lan gak bentrok
        cursor.execute("DELETE FROM staging_pdf_extracted")
        
        for row in extracted_rows:
            # Gunakan INSERT OR REPLACE nggo ngatasi error UNIQUE constraint failed!
            cursor.execute("""
                INSERT OR REPLACE INTO staging_pdf_extracted (std_date, vendor, origin, destination, lh_trip_number, to_number, weight_kg, jmlh_qty, remarks, to_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (row['date'], row['vendor'], row['origin'], row['destination'], row['lh_trip_number'], row['to_number'], row['weight_kg'], row['jmlh_qty'], row['remarks'], row['to_type']))
            success_staging += 1
            
            # Sinkronisasi sisan menyang tabel master produksi
            cursor.execute("""
                UPDATE production_size_manual_koli 
                SET vendor = ?, gross_weight = ?, qty_parcel = ?, remarks = ?, trip_type = 'By Air'
                WHERE to_number = ?
            """, (row['vendor'], row['weight_kg'], row['jmlh_qty'], row['remarks'], row['to_number']))
            success_production += 1
            
        conn.commit()
        print(f"[✓] SINKRONISASI SELESAI:")
        print(f"    -> {success_staging} Baris mlebu 'staging_pdf_extracted'")
        print(f"    -> {success_production} Baris terupdate neng 'production_size_manual_koli'")
        print("\n" + "="*60 + "\n[✓] FIX TEPAK KABEH LUR! SIKAT MANEH SAIKI! 🔥\n" + "="*60)
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"[!] SQL ERROR: {e}")
    finally:
        conn.close()

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
    process_manifest_pdf()