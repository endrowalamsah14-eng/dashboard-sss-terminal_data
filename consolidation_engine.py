import sqlite3
import re
import os
from datetime import datetime

def get_table_columns(cursor, table_name):
    """Moco struktur asli kolom soko tabel database"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]
    except Exception:
        return []

def find_best_column(existing_cols, aliases):
    """Nggoleki kolom sing paling cocok soko daftar jeneng alias"""
    for alias in aliases:
        for col in existing_cols:
            if col.lower() == alias.lower():
                return col
    return None

def extract_slot(lh_tripname, fallback_lt=""):
    """Fungsi nggo rontgen angka Slot soko tripname utawa LT number"""
    text_to_search = str(lh_tripname if lh_tripname else fallback_lt)
    if not text_to_search or text_to_search == "None":
        return ""
    match = re.search(r'SLOT\s*[-_\s]?\s*(\d+)', text_to_search, re.IGNORECASE)
    if match:
        return match.group(1)
    backup = re.search(r'\d+', text_to_search)
    return backup.group(0) if backup else ""

def format_date_to_custom(datetime_str):
    """Ngresiki jam, lan moco format tanggal murni prioritas MM-DD-YYYY dadi '7-May-2026'"""
    if not datetime_str or str(datetime_str).lower() == 'none':
        return ""
    
    clean_date = str(datetime_str).split()[0]
    
    formats_to_try = [
        "%m-%d-%Y",  # MM-DD-YYYY
        "%m/%d/%Y",  # MM/DD/YYYY
        "%Y-%m-%d",  # YYYY-MM-DD
        "%d-%m-%Y",  # DD-MM-YYYY
        "%d/%m/%Y",  # DD/MM/YYYY
        "%Y/%m/%d"   # YYYY/MM/DD
    ]
    
    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(clean_date, fmt)
            return f"{dt.day}-{dt.strftime('%b')}-{dt.strftime('%Y')}"
        except ValueError:
            continue
            
    return clean_date

def run_consolidation_pipeline():
    db_name = "spx_terminal_data.db"
    print("\n=== STARTING CONSOLIDATION ENGINE (RELOAD FRESH MODE) ===")
    
    if not os.path.exists(db_name):
        print(f"[X] Error: Database '{db_name}' ora nemu!")
        return

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # 1. INSPEKSI STRUKTUR TABEL ASLI
    fms_cols = get_table_columns(cursor, "staging_fms_handedover")
    pdf_cols = get_table_columns(cursor, "staging_pdf_extracted")
    
    if not fms_cols or not pdf_cols:
        print("[X] Error: Salah siji tabel staging kosong utawa durung digawe!")
        conn.close()
        return

    # LAYER AMAN: AUTO-PATCH STRUKTUR TABEL PRODUKSI
    prod_cols_info = []
    try:
        cursor.execute("PRAGMA table_info(production_size_manual_koli)")
        prod_cols_info = cursor.fetchall()
    except Exception:
        pass

    if prod_cols_info:
        col_names = [col[1] for col in prod_cols_info]
        is_posisi_pas = False
        if "tag" in col_names and "trip_type" in col_names:
            if col_names.index("trip_type") == col_names.index("tag") + 1:
                is_posisi_pas = True
        
        if not is_posisi_pas:
            print("[+] Nata ulang struktur tabel ben 'trip_type' manggon neng sebelahe 'tag'...")
            new_cols_definition = []
            for col in prod_cols_info:
                c_name = col[1]
                c_type = col[2] or "TEXT"
                if c_name == "trip_type":
                    continue
                new_cols_definition.append(f"{c_name} {c_type}")
                if c_name == "tag":
                    new_cols_definition.append("trip_type TEXT")
            
            try:
                cursor.execute("ALTER TABLE production_size_manual_koli RENAME TO old_prod_table")
                cursor.execute(f"CREATE TABLE production_size_manual_koli ({', '.join(new_cols_definition)})")
                old_cols = [c[1] for c in prod_cols_info]
                all_cols_str = ", ".join(old_cols)
                cursor.execute(f"INSERT INTO production_size_manual_koli ({all_cols_str}) SELECT {all_cols_str} FROM old_prod_table")
                cursor.execute("DROP TABLE old_prod_table")
                conn.commit()
                print("[✓] Schema Patch: Kolom 'trip_type' saiki wis sukses mapan neng tengene 'tag'!")
            except Exception as e:
                print(f"[-] Gagal nata urutan fisik, fallback alter table: {e}")
                try:
                    cursor.execute("ALTER TABLE production_size_manual_koli ADD COLUMN trip_type TEXT")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass

    # 🔥 SUNTINGAN I: SYSTEM WIPE DIAKTIFKAN MANEH! (Nggo ngresiki data cacat/putih sakdurunge)
    cursor.execute("DELETE FROM production_size_manual_koli")
    conn.commit()
    print("[✓] Mode Kamar Produksi: FRESH REFRESH LOAD ACTIVE (Data cacat lawas wis diresiki).")

    # 3. DYNAMIC MAPPING
    fms_lt = find_best_column(fms_cols, ['lh_trip_number', 'trip_number', 'lh_number']) or 'rowid'
    fms_std = find_best_column(fms_cols, ['schedule_departure_time', 'scheduled_departure_time', 'std']) or 'NULL'
    fms_name = find_best_column(fms_cols, ['lh_tripname', 'lh_trip_name', 'trip_name']) or 'NULL'
    fms_driver = find_best_column(fms_cols, ['driver', 'driver_name']) or 'NULL'
    fms_plat = find_best_column(fms_cols, ['vehicle_plate_number', 'vehicle_plat_number', 'vehicle_no', 'nopol']) or 'NULL'
    fms_vtype = find_best_column(fms_cols, ['vehicle_type', 'vehicle_type_pickup', 'vtype']) or 'NULL'
    fms_ata = find_best_column(fms_cols, ['actual_arrival_time', 'ata']) or 'NULL'
    fms_atd = find_best_column(fms_cols, ['actual_departure_time', 'atd']) or 'NULL'
    fms_ttype = find_best_column(fms_cols, ['trip_type', 'freight_type', 'type_trip', 'transport_mode', 'trip_type_name']) or 'NULL'

    pdf_vendor = find_best_column(pdf_cols, ['vendor']) or 'NULL'
    pdf_origin = find_best_column(pdf_cols, ['origin']) or 'NULL'
    pdf_dest = find_best_column(pdf_cols, ['destination']) or 'NULL'
    pdf_lt = find_best_column(pdf_cols, ['lh_trip_number', 'lh_number', 'trip_number']) or 'rowid'
    pdf_to = find_best_column(pdf_cols, ['to_number', 'to_no']) or 'NULL'
    pdf_weight = find_best_column(pdf_cols, ['weight_kg', 'gross_weight', 'weight']) or 'NULL'
    pdf_qty = find_best_column(pdf_cols, ['jmlh_qty', 'qty', 'qty_parcel']) or 'NULL'
    pdf_type = find_best_column(pdf_cols, ['to_type', 'remarks', 'type']) or 'NULL'

    # 4. RACIK QUERY DYNAMIC (JOIN di-tweak nganggo TRIM lan UPPER ben anti-mleset!)
    query = f"""
        WITH fms_origin_only AS (
            SELECT 
                {fms_lt} AS lh_trip_number,
                {fms_std} AS schedule_departure_time,
                {fms_name} AS lh_tripname,
                {fms_driver} AS driver,
                {fms_plat} AS vehicle_plat_number,
                {fms_vtype} AS vehicle_type,
                {fms_ata} AS actual_arrival_time,
                {fms_atd} AS actual_departure_time,
                {fms_ttype} AS trip_type,
                ROW_NUMBER() OVER (PARTITION BY {fms_lt} ORDER BY rowid ASC) as rn
            FROM staging_fms_handedover
        )
        SELECT 
            fms.schedule_departure_time,
            pdf.{pdf_vendor},
            pdf.{pdf_origin},
            pdf.{pdf_dest},
            pdf.{pdf_lt},
            pdf.{pdf_to},
            pdf.{pdf_weight},
            pdf.{pdf_qty},
            pdf.{pdf_type},
            fms.lh_tripname,
            fms.driver,
            fms.vehicle_plat_number,
            fms.vehicle_type,
            fms.actual_arrival_time,
            fms.actual_departure_time,
            fms.trip_type
        FROM staging_pdf_extracted pdf
        LEFT JOIN fms_origin_only fms 
            ON TRIM(UPPER(pdf.{pdf_lt})) = TRIM(UPPER(fms.lh_trip_number)) AND fms.rn = 1
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"[✓] Berhasil menganalisa {len(rows)} baris data teko staging.")
        
        compiled_data = []
        
        for r in rows:
            fms_sched_time, p_vendor, p_orig, p_dest, p_lt, p_to, p_w, p_qty, p_type, \
            f_tripname, f_driver, f_nopol, f_vtype, f_ata, f_atd, f_ttype = r
            
            # 🔥 SUNTINGAN III: FUNGSI GUARD ANTI-TINDIH SING NGUNCI DATA COSOK WIS DIILANGI TOTAL NDROW!
            
            col1_date = format_date_to_custom(fms_sched_time)          
            col2_vendor = p_vendor if p_vendor else ""
            col3_origin = p_orig if p_orig else ""
            col4_destination = p_dest if p_dest else ""
            col5_lt_number = p_lt if p_lt else ""
            col6_to_number = p_to if p_to else ""
            col7_gross_weight = p_w if p_w else 0.0
            col8_qty_parcel = p_qty if p_qty else 0
            col9_remarks = p_type if p_type else ""                    
            col10_slot = extract_slot(f_tripname, fallback_lt=p_lt)      
            col11_driver = f_driver if f_driver else ""
            col12_nopol = f_nopol if f_nopol else ""                    
            col13_vtype = f_vtype if f_vtype else ""
            col14_ata = f_ata if f_ata else ""                          
            col15_atd = f_atd if f_atd else ""                          
            col16_tag = "PENDING"                                       
            col17_trip_type = f_ttype if f_ttype else "" 
            
            final_row = (
                col1_date, col2_vendor, col3_origin, col4_destination, col5_lt_number, col6_to_number,
                col7_gross_weight, col8_qty_parcel, col9_remarks, col10_slot, col11_driver, col12_nopol,
                col13_vtype, col14_ata, col15_atd, col16_tag, col17_trip_type
            )
            compiled_data.append(final_row)
            
        if compiled_data:
            cursor.executemany("""
                INSERT INTO production_size_manual_koli (
                    date, vendor, origin, destination, lt_number, to_number, 
                    gross_weight, qty_parcel, remarks, slot, driver_name, nopol, 
                    vehicle_type, ata_origin, atd_origin, tag, trip_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, compiled_data)
            
            conn.commit()
            print(f"[✓] SUCCESS SUPER! {len(compiled_data)} data gres dengan rincian FMS lengkap berhasil disuntikno.")
        else:
            print("[✓] Aman Ndrow! Ora ono data sing iso diproses.")
            
    except sqlite3.OperationalError as e:
        print(f"\n[X] CRITICAL DATABASE ERROR, NDROW:")
        print(f"    👉 {e}\n")
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
    run_consolidation_pipeline()