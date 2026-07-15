import sqlite3
import os

def init_spx_terminal_db():
    db_name = "spx_terminal_data.db"
    print(f"=== INITIALIZING SLIM & CLEAN API-READY DATABASE ===")
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # -------------------------------------------------------------------------
    # LAYER OVERHAUL: Drop tabel lawas dhisik ben gak tabrakan karo struktur anyar
    # -------------------------------------------------------------------------
    cursor.execute("DROP TABLE IF EXISTS production_size_manual_koli")
    cursor.execute("DROP TABLE IF EXISTS gdocs_pulled_data")
    cursor.execute("DROP TABLE IF EXISTS batch_records")
    cursor.execute("DROP TABLE IF EXISTS staging_fms_handedover")
    
    # 1. KAMAR UTAMA: production_size_manual_koli (URUTAN A-O PAS GDOCS + COL P + COL Q)
    cursor.execute('''
        CREATE TABLE production_size_manual_koli (
            date TEXT,                  -- Kolom A
            vendor TEXT,                -- Kolom B
            origin TEXT,                -- Kolom C
            destination TEXT,           -- Kolom D
            lt_number TEXT,             -- Kolom E
            to_number TEXT,             -- Kolom F
            gross_weight REAL,          -- Kolom G
            qty_parcel INTEGER,         -- Kolom H
            remarks TEXT,               -- Kolom I
            slot TEXT,                  -- Kolom J
            driver_name TEXT,           -- Kolom K
            nopol TEXT,                 -- Kolom L
            vehicle_type TEXT,          -- Kolom M
            ata_origin TEXT,            -- Kolom N
            atd_origin TEXT,            -- Kolom O
            tag TEXT DEFAULT 'PENDING', -- Kolom P (Gantine integrity/validation, anti-boros!)
            trip_type TEXT              -- Kolom Q (Tambahan anyar nggo rute Air / Sea)
        )
    ''')
    print("[✓] Kamar 'production_size_manual_koli' [Murni A-Q] sukses digawe.")

    # 2. KAMAR REVISI ANYAR: gdocs_pulled_data (Jangkep A-O + Audit Layer, trip_type & tag DIBUSAK)
    cursor.execute('''
        CREATE TABLE gdocs_pulled_data (
            date TEXT,                  -- Kolom A
            vendor TEXT,                -- Kolom B
            origin TEXT,                -- Kolom C
            destination TEXT,           -- Kolom D
            lt_number TEXT,             -- Kolom E
            to_number TEXT,             -- Kolom F
            gross_weight REAL,          -- Kolom G
            qty_parcel INTEGER,         -- Kolom H
            remarks TEXT,               -- Kolom I
            slot TEXT,                  -- Kolom J
            driver_name TEXT,           -- Kolom K
            nopol TEXT,                 -- Kolom L
            vehicle_type TEXT,          -- Kolom M
            ata_origin TEXT,            -- Kolom N
            atd_origin TEXT,            -- Kolom O
            gdgp_status TEXT DEFAULT 'GDGP_WARN', -- 'GDGP_OK' lek A-O kebak & akurat, utawa 'GDGP_WARN' lek bolong
            pulled_at TEXT              -- Timestamp waktu pas SSS narik data iki soko Sheets
        )
    ''')
    print("[✓] Kamar 'gdocs_pulled_data' [Anti-Manual Audit Layer - trip_type & tag Removed] sukses di-overhaul.")

    # 3. KAMAR REVISI ANYAR: batch_records (Tracking Sajarah Aktivitas Sync & SLA Input)
    cursor.execute('''
        CREATE TABLE batch_records (
            batch_id TEXT PRIMARY KEY,   -- ID unik per aktivitas sinkronisasi
            lt_number TEXT,              -- Tracking nomor manifest/Surat Jalan sing di-sync
            sync_date TEXT,              -- Tanggal aktual running proses auto_sync
            total_rows_pushed INTEGER,   -- Itungan baris sing sukses munggah menyang GDocs
            start_time TEXT,             -- Waktu awal user mancal sync (Format DATE & TIME)
            end_time TEXT,               -- Waktu pas status data berubah dadi SUCCESS neng GDocs (Format DATE & TIME)
            status TEXT                  -- Itungan otomatis Python: <30 Menit = ONTIME, >30 Menit = LATE
        )
    ''')
    print("[✓] Kamar 'batch_records' [SLA Performance & Log Monitor] sukses di-overhaul.")

    # 4. KAMAR STAGING PDF
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staging_pdf_extracted (
            std_date TEXT,
            vendor TEXT,
            origin TEXT,
            destination TEXT,
            lh_trip_number TEXT,
            to_number TEXT,
            weight_kg REAL,
            jmlh_qty INTEGER,
            remarks TEXT,
            to_type TEXT
        )
    ''')
    print("[✓] Kamar Staging 'staging_pdf_extracted' ready (Steril).")

    # 5. KAMAR STAGING FMS HANDEDOVER (Full Kolom Sesuai Screenshot DB Browser Asli)
    cursor.execute('''
        CREATE TABLE staging_fms_handedover (
            lh_trip_number TEXT,
            lh_trip_name TEXT,
            trip_type TEXT,
            station_number TEXT,
            station_name TEXT,
            vehicle_type TEXT,
            vehicle_plate_number TEXT,
            driver TEXT,
            helper TEXT,
            agency_name TEXT,
            schedule_arrival_time TEXT,
            actual_arrival_time TEXT,
            unsealed_time TEXT,
            unloaded_time TEXT,
            assign_time TEXT,
            loading_time TEXT,
            loaded_time TEXT,
            sealed_time TEXT,
            schedule_departure_time TEXT,
            actual_departure_time TEXT,
            inbound_to TEXT,
            inbound_hv_to TEXT,
            inbound_dg_to TEXT,
            inbound_order TEXT,
            inbound_weight_kg REAL,
            outbound_to TEXT,
            outbound_hv_to TEXT,
            outbound_dg_to TEXT,
            outbound_order TEXT,
            outbound_weight_kg REAL,
            cost_type TEXT,
            draft_name TEXT,
            loading_docked TEXT,
            onsite_registration_id TEXT,
            onsite_arrival_time TEXT,
            onsite_registration_time TEXT,
            seal_status TEXT,
            photo_link TEXT,
            occupancy_rate TEXT,
            reason TEXT,
            remark TEXT,
            trip_tag TEXT,
            late_arrival_status TEXT,
            planned_drive_time TEXT,
            actual_drive_time TEXT,
            late_report_status TEXT,
            late_reason TEXT,
            ongoing_alert TEXT,
            history_alert TEXT,
            source_file TEXT
        )
    ''')
    print("[✓] Kamar Staging 'staging_fms_handedover' [Full 50-Columns Layer] sukses disinkronkan.")
    
    # 6. CAUTION STAGING FMS PENDING
    print("[✓] Kamar Staging 'staging_fms_pending' dikunci rapat (Steril).")
    
    conn.commit()
    conn.close()
    print(f"=== FONDASI FIX SLIM: File '{db_name}' BERHASIL DIRESET & SIAP DIPAKANI DATA DATA MBOIS! ===\n")

if __name__ == "__main__":
    init_spx_terminal_db()