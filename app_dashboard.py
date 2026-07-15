import sys
import streamlit as st
import sqlite3
import pandas as pd
import os
import re
from datetime import datetime, timedelta
import altair as alt

# ==============================================================================
# SUNTIKAN ENGINE TAMBAHAN (Letakkan di mana saja sebelum blok Tab)
# ==============================================================================
def apply_index_1(df):
    """Fungsi helper untuk merubah index dataframe dimulai dari 1 (bukan 0)"""
    if df is not None and not df.empty:
        df_copy = df.copy()
        df_copy.index = range(1, len(df_copy) + 1)
        return df_copy
    return df

# ==============================================================================
# 🎯 1. CONFIG CORE & COMPATIBLE EXECUTIVE DARK THEME
# ==============================================================================
BASE_DIR = ","
LIVE_DB_NAME = "spx_terminal_data.db"
SECRET_KEY_GIEEM = "GieeemSPX2026"

st.set_page_config(
    page_title="🔥 SSS MM PERFORMANCE DASHBOARD MASTERPIECE",
    layout="wide"
)

# Inject CSS Premium Slate-Dark Anti-Crash kanggo Streamlit Versi Lawas
st.markdown("""
    <style>
    .reportview-container, .main { background-color: #0b0f19; color: #f1f5f9; }
    .sidebar .sidebar-content, [data-testid="stSidebar"] { background-color: #111827 !important; }
    div.stButton > button:first-child { background-color: #7c3aed; color: white; border-radius: 6px; }
    .metric-card { background: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 10px; }
    .alert-good { background: #064e3b; padding: 12px; border-radius: 6px; border-left: 5px solid #10b981; color: #a7f3d0; margin-bottom: 10px; }
    .alert-fail { background: #7f1d1d; padding: 12px; border-radius: 6px; border-left: 5px solid #ef4444; color: #fca5a5; margin-bottom: 10px; }
    .alert-warn { background: #78350f; padding: 12px; border-radius: 6px; border-left: 5px solid #f59e0b; color: #fde68a; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# Helper Visual "Bunder-Bunder Sakti" nggunakno SVG Inline Premium (Anti-Crash WinPython Portable)
def render_bunderan_persentase(percentage, label, subtext):
    pct = min(max(float(percentage), 0.0), 100.0)
    stroke_dash = (pct / 100.0) * 283
    color = "#10b981" if pct >= 100.0 else "#ef4444"
    svg_html = f"""
    <div style="text-align: center; background: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155; margin: 5px; min-width: 160px;">
        <p style="margin:0 0 8px 0; font-weight:bold; color:#f1f5f9; font-size:14px;">{label}</p>
        <svg width="100" height="100" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="45" stroke="#334155" stroke-width="10" fill="transparent" />
            <circle cx="60" cy="60" r="45" stroke="{color}" stroke-width="10" fill="transparent"
                    stroke-dasharray="283" stroke-dashoffset="{283 - stroke_dash}" stroke-linecap="round"
                    transform="rotate(-90 60 60)" />
            <text x="50%" y="50%" text-anchor="middle" fill="#ffffff" font-weight="bold" font-size="16px" dy=".3em">{percentage:.1f}%</text>
        </svg>
        <p style="margin:8px 0 0 0; font-size:11px; color:{color}; font-weight:500;">{subtext}</p>
    </div>
    """
    return svg_html

# Master List Filter Destinasi Sesuai Rekapan Forensik User
BY_AIR_DEST_LIST = [
    "Abepura DC", "Alak DC", "Bacan Hub", "Baguala DC", "Balikpapan Barat DC", "Balikpapan DC", 
    "Banjarbaru DC", "Banjarmasin 2 DC", "Banjarmasin DC", "Batam DC", "Dungingi DC", "Jailolo DC", 
    "Kalawat DC", "Kota Waingapu 2 Hub", "Kota Waingapu 4 Hub", "Kota Waingapu Hub", "Labuhan Bajo DC", 
    "Loli Hub", "Loura (Laura) Hub", "Makassar DC", "Manokwari Barat DC", "Mantikulore DC", "Maros DC", 
    "Medan Amplas DC", "Medan DC", "Merauke DC", "Mimika Baru Hub", "Nabire Hub", "Palangka Raya DC", 
    "Pekanbaru 2 DC", "Pekanbaru DC", "Percut Sei Tuan DC", "Pontianak 2 DC", "Pontianak DC", 
    "Sorong Utara DC", "Sungai Kakap DC", "Tamalanrea DC", "Tarakan Barat Hub", "Tarakan Timur Hub", 
    "Tarakan Utara Hub", "Teluk Mutiara Hub", "Ternate Hub", "Ternate Selatan 2 Hub", "Ternate Selatan Hub", 
    "Ternate Utara Hub", "Wamena Hub", "Wua-Wua DC"
]

BY_SEA_DEST_LIST = [
    "Banjarbaru DC", "Banjarmasin 2 DC", "Banjarmasin DC", "Maros DC", "Tamalanrea DC", "Balikpapan DC"
]

# ==============================================================================
# 🧠 2. ENGINE INTELIJEN: REGEX PARSER & METRIC EVALUATOR
# ==============================================================================
def bedah_trip_name_via_regex(trip_name):
    if not trip_name or pd.isna(trip_name):
        return "Unknown", "Reguler", "Slot N/A"
    text = str(trip_name).strip()
    
    dest_match = re.search(r'>\s*([^(]+)', text)
    destination = dest_match.group(1).strip() if dest_match else "Unknown"
    destination = re.sub(r'\s+\d+$', '', destination)
    
    slot_match = re.search(r'Slot\s*(\d+)', text, re.IGNORECASE)
    slot = f"Slot {slot_match.group(1)}" if slot_match else "Slot N/A"
    
    if "hardblock" in text.lower():
        category = "Hardblock"
    elif "sv" in text.lower() or "star vendor" in text.lower():
        category = "SV"
    else:
        category = "Reguler"
        
    return destination, category, slot

def hitung_akurasi_relatif(nilai_fms, nilai_gdocs):
    if nilai_fms == 0 and nilai_gdocs == 0:
        return 100.0
    if nilai_fms == 0 or nilai_gdocs == 0:
        return 0.0
    selisih = abs(nilai_fms - nilai_gdocs)
    percent_error = (selisih / nilai_fms) * 100
    return max(0.0, min(100.0, 100.0 - percent_error))

def evaluasi_status_kompartemen(nilai, tipe="selisih"):
    if tipe == "selisih":
        if nilai == 0: return "GOOD", 100.0, "alert-good"
        elif nilai > 0: return "FAIL", max(0.0, 100.0 - (nilai * 5)), "alert-fail"
        else: return "WARNING", 50.0, "alert-warn"
    elif tipe == "sla_cetak":
        if nilai >= 100.0: return "ACHIEVE", 100.0, "alert-good"
        else: return "LATE", nilai, "alert-fail"
    elif tipe == "batch":
        if nilai >= 50.0: return "OK", nilai, "alert-good"
        else: return "POOR", nilai, "alert-fail"
    elif tipe == "gdgp_status":
        if nilai >= 50.0: return "GOOD", nilai, "alert-good"
        else: return "FAIL", nilai, "alert-fail"

# ==============================================================================
# 🔒 3. SPECIAL PROTOCOL: ACCESS CONTROL FOR BACKDATE BANK DATA
# ==============================================================================
TARGET_DB_PATH = os.path.join(BASE_DIR, LIVE_DB_NAME)

with st.sidebar:
    st.markdown("<h2 style='color:#a78bfa; text-align:center;'>🔒 CONTROL ROOM</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # NAVIGATION CONTROL SINKRON 100%
    pilihan_tab = st.radio(
        "PILIH WORKSPACE DASHBOARD:",
        [
            "📊 TAB.1 ADMINISTRATION PERFORMANCE", 
            "🚛 TAB.2 OPS PERFORMANCE", 
            "🏆 TAB.3 SPECIAL OVERALL GDGP",
            "📊 TONASE MONITORING FREIGHT"
        ]
    )
    
    st.markdown("---")
    st.markdown("### 🔑 SPECIAL PROTOCOL (BACKDATE)")
    sandi_input = st.text_input("Sandi Otoritas Gieeem:", type="password")
    
    if sandi_input == SECRET_KEY_GIEEM:
        st.success("🔓 BANK DATA UNLOCKED")
        list_arsip = [f for f in os.listdir(BASE_DIR) if f.lower().endswith('.db')]
        if list_arsip:
            st.info("📂 Berkas Laporan Terkunci Terdeteksi (Locked State Auto Cut-Off 23:59)")
            db_terpilih = st.selectbox("Pilih Kamar Basis Data Histori:", options=list_arsip)
            TARGET_DB_PATH = os.path.join(BASE_DIR, db_terpilih)
    else:
        if sandi_input:
            st.error("❌ Sandi Salah! Hanya Gieeem sing ngerti!")
        st.info("🔒 RUNNING LIVE MODE (LOCK ON)")

# ==============================================================================
# 🖥️ 4. DATA INGESTION ENGINE (DB SOURCE LALU LINTAS KANTOR)
# ==============================================================================
if not os.path.exists(TARGET_DB_PATH):
    st.error(f"Berkas Basis Data `{os.path.basename(TARGET_DB_PATH)}` Gak Ketemu neng direktori!")
    st.stop()

conn = sqlite3.connect(TARGET_DB_PATH)
try:
    df_fms_handedover = pd.read_sql_query("SELECT * FROM staging_fms_handedover", conn)
    df_gdocs = pd.read_sql_query("SELECT * FROM gdocs_pulled_data", conn)
    
    try: 
        df_batch = pd.read_sql_query("SELECT * FROM batch_records", conn)
    except: 
        df_batch = pd.DataFrame(columns=['status'])
        
    try: 
        df_fms_pending = pd.read_sql_query("SELECT * FROM staging_fms_pending", conn)
    except: 
        df_fms_pending = pd.DataFrame()
        
    df_config_library = pd.DataFrame([
        {"VENDOR": "CKL", "UNIQUE CODE": "Hardblock", "KEY DESTINATION": "BANJARMASIN", "TONASE TARGET (kg)": 55000.0, "GROUP DESTINATION": "Banjarmasin DC, Banjarmasin 2 DC, Banjarbaru DC"},
        {"VENDOR": "PBI", "UNIQUE CODE": "Hardblock", "KEY DESTINATION": "BALIKPAPAN", "TONASE TARGET (kg)": 28000.0, "GROUP DESTINATION": "Balikpapan DC, Balikpapan 2 DC"},
        {"VENDOR": "DHS", "UNIQUE CODE": "Hardblock", "KEY DESTINATION": "MAKASSAR", "TONASE TARGET (kg)": 30000.0, "GROUP DESTINATION": "Makassar DC, Maros DC, Tamalanrea DC"},
        {"VENDOR": "CKL", "UNIQUE CODE": "Hardblock", "KEY DESTINATION": "MAKASSAR", "TONASE TARGET (kg)": 58000.0, "GROUP DESTINATION": "Makassar DC, Maros DC, Tamalanrea DC"},
        {"VENDOR": "DHS", "UNIQUE CODE": "Hardblock", "KEY DESTINATION": "BANJARMASIN", "TONASE TARGET (kg)": 10000.0, "GROUP DESTINATION": "Banjarmasin DC, Banjarmasin 2 DC, Banjarbaru DC"},
        {"VENDOR": "Lion Parcel", "UNIQUE CODE": "SV", "KEY DESTINATION": "MEDAN", "TONASE TARGET (kg)": 1000.0, "GROUP DESTINATION": "Medan DC, Medan Amplas DC, Percut Sei Tuan DC, Siborong-borong DC, Gunung Sitoli DC"},
        {"VENDOR": "Lion Parcel", "UNIQUE CODE": "SV", "KEY DESTINATION": "PONTIANAK", "TONASE TARGET (kg)": 1600.0, "GROUP DESTINATION": "Pontianak DC, Pontianak 2 DC, Sungai Kakap DC, Ketapang Kalbar DC"},
        {"VENDOR": "Lion Parcel", "UNIQUE CODE": "SV", "KEY DESTINATION": "PALANGKA RAYA", "TONASE TARGET (kg)": 2100.0, "GROUP DESTINATION": "Palangka Raya DC, Palangka Raya 2 DC"},
        {"VENDOR": "Lion Parcel", "UNIQUE CODE": "SV", "KEY DESTINATION": "BANJARMASIN", "TONASE TARGET (kg)": 3600.0, "GROUP DESTINATION": "Banjarmasin DC, Banjarmasin 2 DC, Banjarbaru DC"},
        {"VENDOR": "Lion Parcel", "UNIQUE CODE": "SV", "KEY DESTINATION": "BALIKPAPAN", "TONASE TARGET (kg)": 3300.0, "GROUP DESTINATION": "Balikpapan DC, Balikpapan 2 DC"}
    ])
finally:
    conn.close()

# Ekstraksi Engine Regex Kembar neng dataframe utama
if not df_fms_handedover.empty and 'lh_trip_name' in df_fms_handedover.columns:
    parsed_fms = df_fms_handedover['lh_trip_name'].apply(bedah_trip_name_via_regex)
    df_fms_handedover['parsed_dest'] = [p[0] for p in parsed_fms]
    df_fms_handedover['parsed_cat'] = [p[1] for p in parsed_fms]
    df_fms_handedover['parsed_slot'] = [p[2] for p in parsed_fms]

if not df_fms_pending.empty and 'lh_trip_name' in df_fms_pending.columns:
    parsed_pend = df_fms_pending['lh_trip_name'].apply(bedah_trip_name_via_regex)
    df_fms_pending['parsed_dest'] = [p[0] for p in parsed_pend]
    df_fms_pending['parsed_cat'] = [p[1] for p in parsed_pend]
    df_fms_pending['parsed_slot'] = [p[2] for p in parsed_pend]

# 🛡️ OLAHAN KHUSUS ANTI-MBLENDUNG (DEDUPLIKASI / MENJAHIT 1 TRIP = 2 BARIS RELASIONAL)
df_fms_unique = pd.DataFrame()
if not df_fms_handedover.empty and 'lh_trip_number' in df_fms_handedover.columns:
    if 'station_number' in df_fms_handedover.columns:
        df_fms_handedover['station_number_num'] = pd.to_numeric(df_fms_handedover['station_number'], errors='coerce')
        
        # Ambil data destination (station_number == 2)
        df_fms_dest = df_fms_handedover[df_fms_handedover['station_number_num'] == 2][['lh_trip_number', 'station_name']].rename(
            columns={'station_name': 'real_destination'}
        ).drop_duplicates(subset=['lh_trip_number'])
        
        # Agregasi robust untuk data FMS agar metrik dari row mana pun tidak hilang (1 Trip = 2 Rows)
        num_cols = ['outbound_weight_kg', 'outbound_order', 'outbound_to', 'outbound_hv_to', 'outbound_dg_to']
        num_cols = [c for c in num_cols if c in df_fms_handedover.columns]
        
        agg_dict = {}
        for col in df_fms_handedover.columns:
            if col in num_cols:
                df_fms_handedover[col] = pd.to_numeric(df_fms_handedover[col], errors='coerce').fillna(0.0)
                agg_dict[col] = 'max'
            elif col not in ['lh_trip_number', 'station_number', 'station_number_num', 'station_name']:
                agg_dict[col] = 'first'
                
        df_fms_agg = df_fms_handedover.groupby('lh_trip_number', as_index=False).agg(agg_dict)
        df_fms_unique = pd.merge(df_fms_agg, df_fms_dest, on='lh_trip_number', how='left')
        df_fms_unique['parsed_dest'] = df_fms_unique['real_destination'].fillna(df_fms_unique.get('parsed_dest', df_fms_unique.get('station_name', '')))
    else:
        df_fms_unique = df_fms_handedover.drop_duplicates(subset=['lh_trip_number']).copy()

# ==============================================================================
# 🚀 5. FITUR BANK DATA BARU: AUTO CUT-OFF ENGINE 23:59 (LOGICAL CUTOFF - POINT 1)
# ==============================================================================
now_time = datetime.now()
yesterday_time = now_time - timedelta(days=1)

# Target cutoff adalah H-1. Tidak peduli jam berapapun app dibuka.
cutoff_date_str = yesterday_time.strftime('%Y%m%d')
cutoff_filename = f"spx_data_{cutoff_date_str}.db"
cutoff_filepath = os.path.join(BASE_DIR, cutoff_filename)

# Jika file H-1 belum ada, sistem akan langsung mengekstrak data dari Live DB dan memfilternya
if not os.path.exists(cutoff_filepath):
    try:
        conn_cutoff = sqlite3.connect(cutoff_filepath)
        
        # Batasan mutlak Point 1: 00:00:00 sampai 23:59:59 (Kemarin)
        batas_awal = pd.to_datetime(yesterday_time.strftime('%Y-%m-%d 00:00:00'))
        batas_akhir = pd.to_datetime(yesterday_time.strftime('%Y-%m-%d 23:59:59'))
        
        def filter_logical_cutoff(df):
            if df is None or df.empty:
                return df
            df_copy = df.copy()
            # Loop aman untuk mendeteksi kolom waktu apapun yang tersedia di dataframe
            for col in ['actual_departure_time', 'sealed_time', 'loading_time', 'timestamp', 'Timestamp']:
                if col in df_copy.columns:
                    t_col = pd.to_datetime(df_copy[col], errors='coerce')
                    mask = (t_col >= batas_awal) & (t_col <= batas_akhir)
                    return df_copy.loc[mask]
            return df_copy # Return utuh jika tidak ditemukan kolom waktu (Fail-safe)

        df_fms_handedover_co = filter_logical_cutoff(df_fms_handedover)
        if not df_fms_handedover_co.empty:
            df_fms_handedover_co.to_sql('staging_fms_handedover', conn_cutoff, if_exists='replace', index=False)
        
        df_gdocs_co = filter_logical_cutoff(df_gdocs)
        if not df_gdocs_co.empty:
            df_gdocs_co.to_sql('gdocs_pulled_data', conn_cutoff, if_exists='replace', index=False)
            
        df_batch_co = filter_logical_cutoff(df_batch)
        if not df_batch_co.empty:
            df_batch_co.to_sql('batch_records', conn_cutoff, if_exists='replace', index=False)
            
        if not df_gdocs_co.empty and 'to_number' in df_gdocs_co.columns:
            v_counts_co = df_gdocs_co['to_number'].value_counts()
            list_dup_co = v_counts_co[v_counts_co > 1].index
            cols_need_co = [c for c in ['vendor', 'lt_number', 'to_number'] if c in df_gdocs_co.columns]
            df_kamar_4 = df_gdocs_co[df_gdocs_co['to_number'].isin(list_dup_co)][cols_need_co].drop_duplicates()
            if not df_kamar_4.empty:
                df_kamar_4.to_sql('kamar_4_special_case_pt8', conn_cutoff, if_exists='replace', index=False)
                
        df_fms_unique_co = filter_logical_cutoff(df_fms_unique)
        if not df_fms_unique_co.empty:
            df_fms_unique_co.to_sql('kamar_5_overall_tab1', conn_cutoff, if_exists='replace', index=False)
            df_fms_unique_co.to_sql('kamar_6_overall_tab2', conn_cutoff, if_exists='replace', index=False)
            
        conn_cutoff.close()
    except Exception:
        pass

# ==============================================================================
# RENDER: TAB.1 ADMINISTRATION PERFORMANCE
# ==============================================================================
if pilihan_tab == "📊 TAB.1 ADMINISTRATION PERFORMANCE":
    st.title("📊 TAB.1 ADMINISTRATION PERFORMANCE")
    st.markdown(f"**Basis Data Terkunci:** `{os.path.basename(TARGET_DB_PATH)}` | **Mode:** Real-time Daily Audit (Auto Cut-Off 23:59)")
    st.markdown("---")
    
    raw_fms_count = len(df_fms_handedover)
    actual_trip_fms = df_fms_unique['lh_trip_number'].nunique() if not df_fms_unique.empty else 0
    raw_gdocs_count = len(df_gdocs)
    raw_batch_count = len(df_batch)
    
    col_top = st.columns(3)
    with col_top[0]:
        st.markdown(f'<div class="metric-card"><small>1. FMS HANDEDOVER</small><h3>{raw_fms_count} Rows</h3><small>Aktual Trip Unique (nunique): {actual_trip_fms} Trips</small></div>', unsafe_allow_html=True)
    with col_top[1]:
        st.markdown(f'<div class="metric-card"><small>2. GDOCS PULLED DATA</small><h3>{raw_gdocs_count} Rows</h3><small>Form Entries Lapangan</small></div>', unsafe_allow_html=True)
    with col_top[2]:
        st.markdown(f'<div class="metric-card"><small>3. BATCH RECORDS (INPUT)</small><h3>{raw_batch_count} Rows</h3><small>Log Data Batch</small></div>', unsafe_allow_html=True)

    st.markdown("### 📐 Hasil Evaluasi Diktat Administrasi (Poin 4-11)")
    
    # --------------------------------------------------------------------------
    # MAINTENANCE BUG FIX: Peksa dadi numerik murni sakdurunge groupby (Anti-Crash TypeError Int+Str)
    # --------------------------------------------------------------------------
    if not df_gdocs.empty:
        if 'gross_weight' in df_gdocs.columns:
            df_gdocs['gross_weight'] = pd.to_numeric(df_gdocs['gross_weight'].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
        if 'qty_parcel' in df_gdocs.columns:
            df_gdocs['qty_parcel'] = pd.to_numeric(df_gdocs['qty_parcel'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    # Pre-Agregasi Granular GDocs per Trip ID sakdurunge dibandingno relasional (Anti Mblendung)
    if not df_gdocs.empty and 'lt_number' in df_gdocs.columns:
        agg_funcs = {
            'gross_weight': 'sum',
            'qty_parcel': 'sum',
            'to_number': 'count'
        }
        if 'vendor' in df_gdocs.columns:
            agg_funcs['vendor'] = 'first'
        
        df_gdocs_agg = df_gdocs.groupby('lt_number').agg(agg_funcs).reset_index()
        df_gdocs_agg.rename(columns={
            'gross_weight': 'total_gross_weight',
            'qty_parcel': 'total_qty_parcel',
            'to_number': 'total_to_count',
            'vendor': 'gdocs_vendor'
        }, inplace=True)
    else:
        df_gdocs_agg = pd.DataFrame(columns=['lt_number', 'total_gross_weight', 'total_qty_parcel', 'total_to_count', 'gdocs_vendor'])

    # 🛡️ ENGINE REKONSILIASI PENYELAMAT SAKRAL (Mencegah Cartesian Product / Many-to-Many Join Explosion)
    df_recon = pd.DataFrame(columns=['lh_trip_number', 'agency_name', 'fms_weight', 'fms_order', 'fms_to_count', 'gdocs_weight', 'gdocs_order', 'gdocs_to_count'])
    if not df_fms_unique.empty:
        df_fms_temp = df_fms_unique.copy()
        fms_to_series = pd.Series(0, index=df_fms_temp.index)
        for col_t in ['outbound_to', 'outbound_hv_to', 'outbound_dg_to']:
            if col_t in df_fms_temp.columns:
                fms_to_series += pd.to_numeric(df_fms_temp[col_t], errors='coerce').fillna(0)
        df_fms_temp['fms_to_count'] = fms_to_series.astype(int)

        fms_cols = ['lh_trip_number', 'agency_name', 'vehicle_plate_number', 'vehicle_type']
        fms_cols = [c for c in fms_cols if c in df_fms_temp.columns]
        
        df_fms_sel = df_fms_temp[fms_cols + ['fms_to_count']].copy()
        df_fms_sel['fms_weight'] = pd.to_numeric(df_fms_temp['outbound_weight_kg'], errors='coerce').fillna(0.0) if 'outbound_weight_kg' in df_fms_temp.columns else 0.0
        df_fms_sel['fms_order'] = pd.to_numeric(df_fms_temp['outbound_order'], errors='coerce').fillna(0).astype(int) if 'outbound_order' in df_fms_temp.columns else 0
        
        df_gdocs_sel = df_gdocs_agg.rename(
            columns={
                'lt_number': 'lh_trip_number',
                'total_gross_weight': 'gdocs_weight',
                'total_qty_parcel': 'gdocs_order',
                'total_to_count': 'gdocs_to_count'
            }
        )
        
        df_recon = pd.merge(df_fms_sel, df_gdocs_sel, on='lh_trip_number', how='outer')
        
        # Integrasikan nama vendor dari GDocs jika data di FMS kosong (Bug 1 Fix)
        if 'gdocs_vendor' in df_recon.columns:
            if 'agency_name' in df_recon.columns:
                df_recon['agency_name'] = df_recon['agency_name'].fillna(df_recon['gdocs_vendor'])
            else:
                df_recon['agency_name'] = df_recon['gdocs_vendor']
        
        # Penanganan NaNs yang aman
        df_recon['fms_weight'] = pd.to_numeric(df_recon['fms_weight'], errors='coerce').fillna(0.0)
        df_recon['gdocs_weight'] = pd.to_numeric(df_recon['gdocs_weight'], errors='coerce').fillna(0.0)
        for col in ['fms_order', 'fms_to_count', 'gdocs_order', 'gdocs_to_count']:
            df_recon[col] = pd.to_numeric(df_recon[col], errors='coerce').fillna(0).astype(int)

    # 4. REVISI SAKRAL AUDIT: Selisih Linehaul Trip ID Unik FMS vs GDocs
    fms_trips = set(df_fms_unique['lh_trip_number'].dropna().unique()) if not df_fms_unique.empty else set()
    gdocs_trips = set(df_gdocs_agg['lt_number'].dropna().unique()) if not df_gdocs_agg.empty else set()
    missing_in_gdocs = fms_trips - gdocs_trips
    selisih_lh = len(missing_in_gdocs)
    pct_lh = hitung_akurasi_relatif(len(fms_trips), len(gdocs_trips))
    lbl_lh = "GOOD" if selisih_lh == 0 else "FAIL"
    cls_lh = "alert-good" if selisih_lh == 0 else "alert-fail"
    
    # 5. SLA Cetak Surat Jalan (<30 mnt)
    pct_sla_cetak = 100.0
    if not df_fms_unique.empty and 'sealed_time' in df_fms_unique.columns and 'actual_departure_time' in df_fms_unique.columns:
        try:
            t_seal = pd.to_datetime(df_fms_unique['sealed_time'], errors='coerce')
            t_dept = pd.to_datetime(df_fms_unique['actual_departure_time'], errors='coerce')
            durasi_menit = (t_dept - t_seal).dt.total_seconds() / 60
            late_cetak = sum(durasi_menit > 30)
            pct_sla_cetak = ( (len(durasi_menit) - late_cetak) / len(durasi_menit) ) * 100 if len(durasi_menit) > 0 else 100.0
        except: 
            pct_sla_cetak = 100.0
    lbl_cetak, _, cls_cetak = evaluasi_status_kompartemen(pct_sla_cetak, "sla_cetak")
    
    # 6. SLA Performance Batch Records
    pct_batch = 100.0
    if raw_batch_count > 0 and 'status' in df_batch.columns:
        ontime_b = sum(df_batch['status'].astype(str).str.upper() == "ONTIME")
        pct_batch = (ontime_b / raw_batch_count) * 100
    lbl_batch, _, cls_batch = evaluasi_status_kompartemen(pct_batch, "batch")
    
    # 7. gdgp_status gdocs_pulled_data
    pct_gdgp = 100.0
    if raw_gdocs_count > 0 and 'gdgp_status' in df_gdocs.columns:
        ok_gdgp = sum(df_gdocs['gdgp_status'].astype(str).str.upper() == "GDGP_OK")
        pct_gdgp = (ok_gdgp / raw_gdocs_count) * 100
    lbl_gdgp, _, cls_gdgp = evaluasi_status_kompartemen(pct_gdgp, "gdgp_status")
    
    # 8. REVISI SAKRAL PROTEKSI: Double TO Gdocs, vendor WAJIB paling ngarep
    double_to_count = 0
    df_detail_pt8 = pd.DataFrame()
    if raw_gdocs_count > 0 and 'to_number' in df_gdocs.columns:
        v_counts = df_gdocs['to_number'].value_counts()
        double_to_count = sum(v_counts > 1)
        list_dup_to = v_counts[v_counts > 1].index
        cols_needed = []
        for c in ['vendor', 'lt_number', 'to_number']:
            if c in df_gdocs.columns: cols_needed.append(c)
        df_detail_pt8 = df_gdocs[df_gdocs['to_number'].isin(list_dup_to)][cols_needed].drop_duplicates()
    
    pct_pt8 = max(0.0, 100.0 - (double_to_count * 2))
    lbl_pt8 = "GOOD" if double_to_count == 0 else "FAIL"
    cls_pt8 = "alert-good" if double_to_count == 0 else "alert-fail"
    
    # 9. Selisih Count TO (Diambil dari subquery terdeduplikasi agar bebas dari cartesian join)
    sum_fms_to = 0
    if not df_fms_unique.empty:
        for col_t in ['outbound_to', 'outbound_hv_to', 'outbound_dg_to']:
            if col_t in df_fms_unique.columns:
                sum_fms_to += pd.to_numeric(df_fms_unique[col_t], errors='coerce').sum() or 0
                
    selisih_to_global = int(sum_fms_to - raw_gdocs_count)
    pct_pt9 = hitung_akurasi_relatif(sum_fms_to, raw_gdocs_count)
    lbl_pt9 = "GOOD" if selisih_to_global == 0 else "FAIL"
    cls_pt9 = "alert-good" if selisih_to_global == 0 else "alert-fail"
    
    # 10. Selisih Outbound Weight vs Gross Weight GDocs (Bebas dari multi-station explosion)
    fms_w = pd.to_numeric(df_fms_unique['outbound_weight_kg'], errors='coerce').sum() if not df_fms_unique.empty and 'outbound_weight_kg' in df_fms_unique.columns else 0.0
    gdoc_w = pd.to_numeric(df_gdocs['gross_weight'], errors='coerce').sum() if 'gross_weight' in df_gdocs.columns else 0.0
    selisih_weight = fms_w - gdoc_w
    pct_pt10 = hitung_akurasi_relatif(fms_w, gdoc_w)
    lbl_pt10 = "GOOD" if int(selisih_weight) == 0 else "FAIL"
    cls_pt10 = "alert-good" if int(selisih_weight) == 0 else "alert-fail"
    
    # 11. Selisih Outbound Order vs Qty Parcel GDocs (Akurat 100%)
    fms_ord = pd.to_numeric(df_fms_unique['outbound_order'], errors='coerce').sum() if not df_fms_unique.empty and 'outbound_order' in df_fms_unique.columns else 0
    gdoc_par = pd.to_numeric(df_gdocs['qty_parcel'], errors='coerce').sum() if 'qty_parcel' in df_gdocs.columns else 0
    selisih_order = fms_ord - gdoc_par
    pct_pt11 = hitung_akurasi_relatif(fms_ord, gdoc_par)
    lbl_pt11 = "GOOD" if selisih_order == 0 else "FAIL"
    cls_pt11 = "alert-good" if selisih_order == 0 else "alert-fail"
    
    # 12. GDGP COMPARTMENT DAILY PERCENTAGE (AVERAGE PT 4-11)
    avg_daily_gdgp = (pct_lh + pct_sla_cetak + pct_batch + pct_gdgp + pct_pt8 + pct_pt9 + pct_pt10 + pct_pt11) / 8.0

    # RENDER BLOK MATRIX REKONSILIASI
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown(f'<div class="{cls_lh}"><b>Point 4. Selisih Linehaul (Unique ID):</b> {selisih_lh} Trips Mismatch ({lbl_lh} | {pct_lh:.1f}%)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="{cls_cetak}"><b>Point 5. SLA Cetak SJ:</b> {lbl_cetak} ({pct_sla_cetak:.1f}%)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="{cls_batch}"><b>Point 6. Performance Batch:</b> {lbl_batch} ({pct_batch:.1f}%)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="{cls_gdgp}"><b>Point 7. GDGP Status GDocs:</b> {lbl_gdgp} ({pct_gdgp:.1f}%)</div>', unsafe_allow_html=True)
    with c_right:
        st.markdown(f'<div class="{cls_pt8}"><b>Point 8. Double TO in GDocs:</b> {double_to_count} TO ({lbl_pt8} | {pct_pt8:.1f}%)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="{cls_pt9}"><b>Point 9. Selisih Count TO:</b> {selisih_to_global} TO ({lbl_pt9} | {pct_pt9:.1f}%)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="{cls_pt10}"><b>Point 10. Selisih Tonase:</b> {selisih_weight:,.1f} Kg ({lbl_pt10} | {pct_pt10:.1f}%)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="{cls_pt11}"><b>Point 11. Selisih Qty Order:</b> {selisih_order} Pcs ({lbl_pt11} | {pct_pt11:.1f}%)</div>', unsafe_allow_html=True)

    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #4c1d95, #1e1b4b); padding: 25px; border-radius: 10px; text-align: center; margin-top: 20px; border: 2px solid #a78bfa;">
            <h2 style="margin:0; color:#f5f3ff;">🏆 Point 12. GDGP COMPARTMENT DAILY PERCENTAGE</h2>
            <h1 style="margin:10px 0; font-size:48px; color:#ffffff;">{avg_daily_gdgp:.2f}%</h1>
            <p style="margin:0; color:#c084fc; font-size:14px;">Indeks Integrasi Sistem Administrasi Aktual Menunggal</p>
        </div>
    """, unsafe_allow_html=True)

    # BLOCK DETAIL DATA COMPARTMENT EXPANDER (FORENSIK INTERAKTIF)
    st.markdown("---")
    st.markdown("### 🔍 RUANG FORENSIK DETAIL ARSIP DATA (TAB.1)")
    
    # 📂 Detail Point 4
    exp4 = st.expander("📂 Detail Point 4 - Kasus Penyimpangan Selisih Transaksi Linehaul")
    with exp4:
        if selisih_lh != 0 and not df_fms_unique.empty:
            cols_p4_show = [c for c in ['agency_name', 'lh_trip_number', 'vehicle_plate_number', 'vehicle_type'] if c in df_fms_unique.columns]
            df_p4 = df_fms_unique[df_fms_unique['lh_trip_number'].isin(missing_in_gdocs)][cols_p4_show].drop_duplicates().reset_index(drop=True)
            df_p4 = apply_index_1(df_p4)
            st.dataframe(df_p4, use_container_width=True)
        else:
            st.success("Clear! Data sinkron total rapi jali.")

    # 📂 Detail Point 8
    exp8 = st.expander("📂 Detail Point 8 - Temuan Double TO in GDocs (Vendor Urutan Terdepan)")
    with exp8:
        if not df_detail_pt8.empty: 
            df_detail_pt8 = df_detail_pt8.reset_index(drop=True)
            df_detail_pt8 = apply_index_1(df_detail_pt8)
            st.dataframe(df_detail_pt8, use_container_width=True)
        else: 
            st.success("Clear! Gak ono data dobel TO blas.")

    # 📂 Detail Point 9 (Forensik Selisih Count TO per Trip ID)
    exp9 = st.expander("📂 Detail Point 9 - Breakdown Vendor & LT (Count Total TO Unique)")
    with exp9: 
        df_detail_pt9 = pd.DataFrame()
        if not df_recon.empty:
            df_recon['diff_to'] = df_recon['fms_to_count'] - df_recon['gdocs_to_count']
            df_detail_pt9 = df_recon[df_recon['diff_to'] != 0].copy()
            if not df_detail_pt9.empty:
                cols_show_pt9 = [c for c in ['agency_name', 'lh_trip_number', 'fms_to_count', 'gdocs_to_count', 'diff_to'] if c in df_detail_pt9.columns]
                df_detail_pt9 = df_detail_pt9[cols_show_pt9].copy()
                df_detail_pt9.rename(columns={
                    'agency_name': 'Agency / Vendor',
                    'lh_trip_number': 'Trip Number',
                    'fms_to_count': 'TO Count (FMS)',
                    'gdocs_to_count': 'TO Count (GDocs)',
                    'diff_to': 'Selisih TO'
                }, inplace=True, errors='ignore')

        if not df_detail_pt9.empty:
            df_detail_pt9 = df_detail_pt9.reset_index(drop=True)
            df_detail_pt9 = apply_index_1(df_detail_pt9)
            st.dataframe(df_detail_pt9, use_container_width=True)
        else:
            st.success("Clear! Selisih Count TO nihil.")

    # 📂 Detail Point 10 (Forensik Selisih Tonase per Trip ID)
    exp10 = st.expander("📂 Detail Point 10 - Breakdown Berat Selisih Tonase per Vendor")
    with exp10: 
        df_detail_pt10 = pd.DataFrame()
        if not df_recon.empty:
            # Menggunakan presisi pembulatan 4 desimal untuk eliminasi anomali float (Bug 2 Fix)
            df_recon['diff_weight'] = (df_recon['fms_weight'] - df_recon['gdocs_weight']).round(4)
            df_detail_pt10 = df_recon[df_recon['diff_weight'] != 0].copy()
            if not df_detail_pt10.empty:
                cols_show_pt10 = [c for c in ['agency_name', 'lh_trip_number', 'fms_weight', 'gdocs_weight', 'diff_weight'] if c in df_detail_pt10.columns]
                df_detail_pt10 = df_detail_pt10[cols_show_pt10].copy()
                df_detail_pt10.rename(columns={
                    'agency_name': 'Agency / Vendor',
                    'lh_trip_number': 'Trip Number',
                    'fms_weight': 'Outbound Weight Kg (FMS)',
                    'gdocs_weight': 'Gross Weight Kg (GDocs)',
                    'diff_weight': 'Selisih Weight (Kg)'
                }, inplace=True, errors='ignore')

        if not df_detail_pt10.empty:
            df_detail_pt10 = df_detail_pt10.reset_index(drop=True)
            df_detail_pt10 = apply_index_1(df_detail_pt10)
            st.dataframe(df_detail_pt10, use_container_width=True)
        else:
            st.success("Clear! Selisih Tonase nihil.")

    # 📂 Detail Point 11 (Forensik Selisih Qty Order per Trip ID)
    exp11 = st.expander("📂 Detail Point 11 - Breakdown Qty Parcel per Vendor/LT")
    with exp11: 
        df_detail_pt11 = pd.DataFrame()
        if not df_recon.empty:
            df_recon['diff_order'] = df_recon['fms_order'] - df_recon['gdocs_order']
            df_detail_pt11 = df_recon[df_recon['diff_order'] != 0].copy()
            if not df_detail_pt11.empty:
                cols_show_pt11 = [c for c in ['agency_name', 'lh_trip_number', 'fms_order', 'gdocs_order', 'diff_order'] if c in df_detail_pt11.columns]
                df_detail_pt11 = df_detail_pt11[cols_show_pt11].copy()
                df_detail_pt11.rename(columns={
                    'agency_name': 'Agency / Vendor',
                    'lh_trip_number': 'Trip Number',
                    'fms_order': 'Outbound Order (FMS)',
                    'gdocs_order': 'Qty Parcel (GDocs)',
                    'diff_order': 'Selisih Order'
                }, inplace=True, errors='ignore')

        if not df_detail_pt11.empty:
            df_detail_pt11 = df_detail_pt11.reset_index(drop=True)
            df_detail_pt11 = apply_index_1(df_detail_pt11)
            st.dataframe(df_detail_pt11, use_container_width=True)
        else:
            st.success("Clear! Selisih Qty Order nihil.")

# ==============================================================================
# RENDER: TAB.2 OPS PERFORMANCE (REFACTORED, FIXED & BULLETPROOF)
# ==============================================================================
elif pilihan_tab == "🚛 TAB.2 OPS PERFORMANCE":
    st.title("🚛 TAB.2 OPS PERFORMANCE (AKTUAL & LIVE CONDITION)")
    st.markdown("---")
    
    # ==========================================================================
    # FUNGSI RENDER GAUGE KOMPAK (UKURAN DIPERBESAR & TEXT WRAPPED)
    # ==========================================================================
    def render_compact_bunderan(pct, title, sub_text):
        color = "#00E676" if pct >= 100 else ("#FF1744" if pct < 30 else "#FF9100")
        deg = min(360, int((pct / 100) * 360)) if pct > 0 else 0
        return f"""
        <div style="background-color: #1E232F; padding: 12px 8px; border-radius: 10px; text-align: center; margin-bottom: 15px; border: 1px solid #2E3545; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
            <div style="font-size: 12px; font-weight: bold; color: #FFFFFF; margin-bottom: 8px; white-space: normal; line-height: 1.3; min-height: 32px;" title="{title}">{title}</div>
            <div style="position: relative; width: 86px; height: 86px; margin: 0 auto; background: conic-gradient({color} {deg}deg, #2A303C 0deg); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                <div style="width: 66px; height: 66px; background-color: #1E232F; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 13px; font-weight: bold; color: #FFFFFF;">{pct:.1f}%</span>
                </div>
            </div>
            <div style="font-size: 11px; font-weight: 600; color: #B0BEC5; margin-top: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{sub_text}</div>
        </div>
        """

    # ==========================================================================
    # 1. UPGRADE: DYNAMIC GAUGE GRID (ALL HARDBLOCK & SV FROM GDOCS)
    # ==========================================================================
    st.markdown("### 📊 MAPPING PERSENTASE KETERCAPAIAN TARGET DESTINASI DARI HARDBLOCK & SV (State Locked: Auto Cut-Off 23:59)")
    
    if not df_fms_unique.empty and not df_config_library.empty:
        col_vendor = next((c for c in df_config_library.columns if 'VENDOR' in str(c).upper()), 'VENDOR')
        col_code = next((c for c in df_config_library.columns if 'UNIQUE' in str(c).upper() or 'CODE' in str(c).upper()), 'UNIQUE CODE in LH Trip Name (CSV file FMS Handedover)')
        col_key = next((c for c in df_config_library.columns if 'KEY' in str(c).upper() and 'GROUP' not in str(c).upper()), 'KEY DESTINATION')
        col_group = next((c for c in df_config_library.columns if 'GROUP' in str(c).upper()), 'GROUP DESTINATION')
        col_target = next((c for c in df_config_library.columns if 'TARGET' in str(c).upper() or 'TONASE' in str(c).upper()), 'TONASE TARGET (kg)')
        
        gauge_items = []
        
        for idx, row in df_config_library.iterrows():
            v_name = str(row[col_vendor]).strip()
            raw_code = str(row[col_code]).strip()
            key_dest = str(row[col_key]).strip()
            
            if "reguler" in raw_code.lower():
                continue
                
            try:
                if isinstance(row[col_target], str):
                    cleaned_target = row[col_target].split('.')[0].replace(',', '')
                    t_weight = float(cleaned_target)
                else:
                    t_weight = float(row[col_target])
            except:
                t_weight = 0.0
                
            g_dests = [d.strip() for d in str(row[col_group]).split(',') if d.strip()]
            icon = "🏗️" if "hardblock" in raw_code.lower() else ("✈️" if "sv" in raw_code.lower() else "🎯")
            
            mask_contract = (
                (df_fms_unique['agency_name'].astype(str).str.strip().str.lower() == v_name.lower()) &
                (df_fms_unique['parsed_dest'].astype(str).str.strip().isin(g_dests)) &
                (
                    df_fms_unique['lh_trip_name'].astype(str).str.contains(raw_code, case=False, na=False, regex=False) |
                    df_fms_unique['parsed_cat'].astype(str).str.contains(raw_code, case=False, na=False, regex=False)
                )
            )
            
            if 'outbound_weight_kg' in df_fms_unique.columns:
                df_fms_unique['outbound_weight_kg'] = pd.to_numeric(df_fms_unique['outbound_weight_kg'].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
            
            w_act = df_fms_unique.loc[mask_contract, 'outbound_weight_kg'].sum() if 'outbound_weight_kg' in df_fms_unique.columns else 0.0
            pct_vis = (w_act / t_weight) * 100 if t_weight > 0 else 0.0
            
            if w_act >= t_weight:
                sub_txt = "🟢 ACHIEVED"
            else:
                sub_txt = f"⚠️ SISA: -{int(t_weight - w_act):,} Kg"
            
            title_gauge = f"{icon} {v_name} ({key_dest})"
            gauge_items.append({"title": title_gauge, "pct": pct_vis, "sub": sub_txt})
        
        if gauge_items:
            cols_per_row = 5
            for i in range(0, len(gauge_items), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, item in enumerate(gauge_items[i:i+cols_per_row]):
                    with cols[j]:
                        st.markdown(render_compact_bunderan(item['pct'], item['title'], item['sub']), unsafe_allow_html=True)
    else:
        st.info("Data transaksi atau Configuration Library kosong.")
        
    st.markdown("---")

    # ==========================================================================
    # PENAMBAHAN FITUR: HIGHLIGHT TOTAL ACTUAL UNIT (DEPART, LOADING, ASSIGN)
    # ==========================================================================
    st.markdown("### 📊 HIGHLIGHT ACTUAL UNIT & TONASE PER VENDOR (DEPARTED, LOADING, ASSIGNED)")
    
    plat_col_u = 'vehicle_plat_number' if 'vehicle_plat_number' in df_fms_unique.columns else ('vehicle_plate_number' if 'vehicle_plate_number' in df_fms_unique.columns else None)
    plat_col_p = 'vehicle_plat_number' if 'vehicle_plat_number' in df_fms_pending.columns else ('vehicle_plate_number' if 'vehicle_plate_number' in df_fms_pending.columns else None)
    
    col_hl1, col_hl2, col_hl3 = st.columns(3)
    
    with col_hl1:
        st.markdown("#### 🟢 DEPARTED UNITS")
        if not df_fms_unique.empty and plat_col_u:
            if 'outbound_weight_kg' in df_fms_unique.columns:
                df_fms_unique['outbound_weight_kg'] = pd.to_numeric(df_fms_unique['outbound_weight_kg'].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
            
            grp_depart = df_fms_unique.groupby(['agency_name', 'trip_type']).agg(
                Total_Unit=(plat_col_u, 'nunique'),
                Total_Tonase_Kg=('outbound_weight_kg', 'sum')
            ).reset_index()
            st.dataframe(apply_index_1(grp_depart), use_container_width=True)
        else:
            st.info("Belum ada unit yang depart.")

    with col_hl2:
        st.markdown("#### 🚚 LOADING UNITS")
        if not df_fms_pending.empty and 'loading_time' in df_fms_pending.columns and plat_col_p:
            df_loading = df_fms_pending[df_fms_pending['loading_time'].notna()]
            if not df_loading.empty:
                if 'outbound_weight_kg' in df_loading.columns:
                    df_loading['outbound_weight_kg'] = pd.to_numeric(df_loading['outbound_weight_kg'].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
                
                grp_load = df_loading.groupby(['agency_name', 'trip_type']).agg(
                    Total_Unit=(plat_col_p, 'nunique'),
                    Total_Tonase_Kg=('outbound_weight_kg', 'sum')
                ).reset_index()
                st.dataframe(apply_index_1(grp_load), use_container_width=True)
            else:
                st.info("Belum ada unit yang loading.")
        else:
            st.info("Belum ada unit yang loading.")

    with col_hl3:
        st.markdown("#### 🟡 ASSIGNED UNITS")
        if not df_fms_pending.empty and 'loading_time' in df_fms_pending.columns and plat_col_p:
            df_assign = df_fms_pending[df_fms_pending['loading_time'].isna() & df_fms_pending[plat_col_p].notna()]
            if not df_assign.empty:
                if 'outbound_weight_kg' in df_assign.columns:
                    df_assign['outbound_weight_kg'] = pd.to_numeric(df_assign['outbound_weight_kg'].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
                
                grp_assign = df_assign.groupby(['agency_name', 'trip_type']).agg(
                    Total_Unit=(plat_col_p, 'nunique'),
                    Total_Tonase_Kg=('outbound_weight_kg', 'sum')
                ).reset_index()
                st.dataframe(apply_index_1(grp_assign), use_container_width=True)
            else:
                st.info("Belum ada unit yang assign.")
        else:
            st.info("Belum ada unit yang assign.")

    st.markdown("---")
    
    # ==========================================================================
    # POIN 1: VOLUME & DESTINASI REGULER CATEGORY
    # ==========================================================================
    if not df_fms_unique.empty:
        mask_true_reguler = (
            (~df_fms_unique['lh_trip_name'].astype(str).str.contains('Hardblock', case=False, na=False, regex=False)) &
            (~df_fms_unique['lh_trip_name'].astype(str).str.contains('SV', case=False, na=False, regex=False)) &
            (~df_fms_unique['parsed_cat'].astype(str).str.contains('Hardblock', case=False, na=False, regex=False)) &
            (~df_fms_unique['parsed_cat'].astype(str).str.contains('SV', case=False, na=False, regex=False))
        )
        df_p1 = df_fms_unique[mask_true_reguler].copy()
        
        st.markdown("#### 1. Volume & Destinasi Reguler Category (Sea & Air | Auto Cut-Off 23:59)")
        if not df_p1.empty:
            for col_req in ['lh_trip_number', 'outbound_weight_kg', 'parsed_dest', 'trip_type']:
                if col_req not in df_p1.columns:
                    df_p1[col_req] = 0 if 'weight' in col_req else "Unknown"
            
            grp_p1 = df_p1.groupby(['parsed_dest', 'trip_type']).agg(
                Grand_Total_Trip=('lh_trip_number', 'nunique'),
                Total_Outbound_Weight=('outbound_weight_kg', 'sum')
            ).reset_index()
            st.dataframe(apply_index_1(grp_p1), use_container_width=True)
        else:
            st.info("Tidak ada transaksi kategori Reguler pada periode ini.")
            
        st.markdown("---")
            
# ==========================================================================
        # POIN 2 & 3: TARGET STATUS HIGHLIGHT PER KEY DESTINATION & VENDOR
        # ==========================================================================
        st.markdown("#### 2 & 3. Target Status Highlight Per Key Destination & Vendor (Dinamis Hardblock & SV)")
        
        if not df_config_library.empty:
            col_vendor = next((c for c in df_config_library.columns if 'VENDOR' in str(c).upper()), 'VENDOR')
            col_code = next((c for c in df_config_library.columns if 'UNIQUE' in str(c).upper() or 'CODE' in str(c).upper()), 'UNIQUE CODE in LH Trip Name (CSV file FMS Handedover)')
            col_key = next((c for c in df_config_library.columns if 'KEY' in str(c).upper() and 'GROUP' not in str(c).upper()), 'KEY DESTINATION')
            col_group = next((c for c in df_config_library.columns if 'GROUP' in str(c).upper()), 'GROUP DESTINATION')
            col_target = next((c for c in df_config_library.columns if 'TARGET' in str(c).upper() or 'TONASE' in str(c).upper()), 'TONASE TARGET (kg)')
            
            for idx, row in df_config_library.iterrows():
                v_name = str(row[col_vendor]).strip()
                raw_code = str(row[col_code]).strip()
                k_dest = str(row[col_key]).strip()
                
                if "reguler" in raw_code.lower():
                    continue
                    
                try:
                    if isinstance(row[col_target], str):
                        cleaned_target = row[col_target].split('.')[0].replace(',', '')
                        t_weight = float(cleaned_target)
                    else:
                        t_weight = float(row[col_target])
                except:
                    t_weight = 0.0
                    
                g_dests = [d.strip() for d in str(row[col_group]).split(',') if d.strip()]
                icon = "⚜️" if "hardblock" in raw_code.lower() else "✈️"
                
                mask_filtered = (
                    (df_fms_unique['agency_name'].astype(str).str.strip().str.lower() == v_name.lower()) &
                    (df_fms_unique['parsed_dest'].astype(str).str.strip().isin(g_dests)) &
                    (
                        df_fms_unique['lh_trip_name'].astype(str).str.contains(raw_code, case=False, na=False, regex=False) |
                        df_fms_unique['parsed_cat'].astype(str).str.contains(raw_code, case=False, na=False, regex=False)
                    )
                )
                
                act_w = df_fms_unique.loc[mask_filtered, 'outbound_weight_kg'].sum() if 'outbound_weight_kg' in df_fms_unique.columns else 0.0
                def_w = t_weight - act_w
                pct = (act_w / t_weight * 100) if t_weight > 0 else 0.0
                
                st.markdown(f"##### {icon} Vendor: **{v_name}** | Key Destination: **{k_dest}** *(Group: {len(g_dests)} DC)*")
                col_z1, col_z2, col_z3 = st.columns(3)
                col_z1.metric("Actual Perolehan", f"{act_w:,.2f} Kg")
                col_z2.metric("Target Baseline Contract", f"{t_weight:,.2f} Kg")
                
                lbl_def = "⚠️ KEKURANGAN DEFISIT" if def_w > 0 else "✅ TARGET ACHIEVED"
                val_def = max(0.0, def_w)
                col_z3.metric(lbl_def, f"{val_def:,.2f} Kg", delta=f"{pct:.1f}% dari Target" if def_w > 0 else "100%+")
                
                df_chart = pd.DataFrame({
                    'Status Target': ['Actual Perolehan', 'Kekurangan Target Defisit'],
                    'Tonase (Kg)': [act_w, val_def]
                })
                
                # IMPLEMENTASI CHART BARU (STANDAR EUROPE COMPLIANCE - ANTI POTONG)
                chart = alt.Chart(df_chart).mark_bar(color='#0068c9').encode(
                    x=alt.X(
                        'Status Target:N', 
                        axis=alt.Axis(
                            labelAngle=0,       # Teks mendatar (horizontal) agar tidak tegak lurus ke bawah
                            labelLimit=300,     # Mencegah teks dipotong menggunakan titik-titik (...)
                            title=None          # Menghilangkan judul sumbu X agar visual lebih bersih
                        )
                    ),
                    y=alt.Y(
                        'Tonase (Kg):Q', 
                        axis=alt.Axis(title='Tonase (Kg)')
                    )
                ).properties(
                    height=300                  # Tinggi chart yang proporsional untuk 2 bar data
                )
                
                # Menggunakan width="stretch" agar tidak memicu warning di terminal Streamlit Anda
                st.altair_chart(chart, width="stretch")
                st.markdown("---")

    # ==========================================================================
    # POIN 4-7: LIVE REKOR MONITORING ARMADA YARD TERMINAL
    # ==========================================================================
    st.markdown("### 🚨 LIVE REKOR MONITORING ARMADA YARD TERMINAL (POIN 4-7 CARD EXPANDER LAYOUT | Locked State: 23:59)")
    
    plat_col_pending = 'vehicle_plat_number' if 'vehicle_plat_number' in df_fms_pending.columns else ('vehicle_plate_number' if 'vehicle_plate_number' in df_fms_pending.columns else None)
    plat_col_unique = 'vehicle_plat_number' if 'vehicle_plat_number' in df_fms_unique.columns else ('vehicle_plate_number' if 'vehicle_plate_number' in df_fms_unique.columns else None)

    if not df_fms_pending.empty and 'outbound_weight_kg' in df_fms_pending.columns:
        df_fms_pending['outbound_weight_kg'] = pd.to_numeric(df_fms_pending['outbound_weight_kg'].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)

    # 4. Live Actual Unit Status Loading
    st.markdown("#### 4. Live Actual Unit Status Loading (Source: FMS Pending)")
    if not df_fms_pending.empty and 'loading_time' in df_fms_pending.columns and plat_col_pending:
        df_load = df_fms_pending[df_fms_pending['loading_time'].notna()]
        if not df_load.empty:
            for plat in df_load[plat_col_pending].dropna().unique():
                df_plat = df_load[df_load[plat_col_pending] == plat]
                vendor = df_plat['agency_name'].iloc[0] if 'agency_name' in df_plat.columns else "Unknown"
                slot = df_plat['parsed_slot'].iloc[0] if 'parsed_slot' in df_plat.columns else "N/A"
                tot_dest = df_plat['parsed_dest'].nunique()
                tot_w = df_plat['outbound_weight_kg'].sum() if 'outbound_weight_kg' in df_plat.columns else 0.0
                
                with st.expander(f"🚚 {plat} [{vendor}] | {slot} | Total Multi-Drop: {tot_dest} Destinasi ({tot_w:,.1f} Kg)"):
                    cols_show = [c for c in ['lh_trip_number', 'parsed_dest', 'parsed_cat', 'trip_type', 'outbound_weight_kg'] if c in df_plat.columns]
                    st.dataframe(apply_index_1(df_plat[cols_show]), use_container_width=True)
        else: st.info("Gak ono armada neng njero dok muat (0 Loading).")
    else: st.info("Gak ono armada neng njero dok muat (0 Loading).")

    # 5. Live Actual Unit Status Assign
    st.markdown("#### 5. Live Actual Unit Status Assign (Source: FMS Pending)")
    if not df_fms_pending.empty and 'loading_time' in df_fms_pending.columns and plat_col_pending:
        df_assign = df_fms_pending[df_fms_pending['loading_time'].isna() & df_fms_pending[plat_col_pending].notna()]
        if not df_assign.empty:
            for plat in df_assign[plat_col_pending].dropna().unique():
                df_plat = df_assign[df_assign[plat_col_pending] == plat]
                vendor = df_plat['agency_name'].iloc[0] if 'agency_name' in df_plat.columns else "Unknown"
                slot = df_plat['parsed_slot'].iloc[0] if 'parsed_slot' in df_plat.columns else "N/A"
                tot_dest = df_plat['parsed_dest'].nunique()
                
                with st.expander(f"🟡 ASSIGNED: {plat} [{vendor}] | {slot} | Multi-Drop: {tot_dest} Destinasi"):
                    cols_show = [c for c in ['lh_trip_number', 'parsed_dest', 'parsed_cat', 'trip_type'] if c in df_plat.columns]
                    st.dataframe(apply_index_1(df_plat[cols_show]), use_container_width=True)
        else: st.info("Gak ono armada standby sing ke-assign.")
    else: st.info("Gak ono armada standby sing ke-assign.")

    # 6. Grand Total Actual Unit Depart
    st.markdown("#### 6. Grand Total Actual Unit Depart (Source: FMS Unique Clean)")
    if not df_fms_unique.empty and plat_col_unique:
        for plat in df_fms_unique[plat_col_unique].dropna().unique():
            df_plat = df_fms_unique[df_fms_unique[plat_col_unique] == plat]
            vendor = df_plat['agency_name'].iloc[0] if 'agency_name' in df_plat.columns else "Unknown"
            slot = df_plat['parsed_slot'].iloc[0] if 'parsed_slot' in df_plat.columns else "N/A"
            tot_w = df_plat['outbound_weight_kg'].sum() if 'outbound_weight_kg' in df_plat.columns else 0.0
            
            with st.expander(f"🟢 DEPARTED: {plat} [{vendor}] | {slot} | Total Load: {tot_w:,.1f} Kg"):
                cols_show = [c for c in ['lh_trip_number', 'parsed_dest', 'parsed_cat', 'trip_type', 'outbound_weight_kg'] if c in df_plat.columns]
                st.dataframe(apply_index_1(df_plat[cols_show].drop_duplicates()), use_container_width=True)

    # 7. Duration Loading Unit Depart
    st.markdown("#### 7. Duration Loading Unit Depart (loading_time - actual_departure_time)")
    if not df_fms_unique.empty and 'loading_time' in df_fms_unique.columns and 'actual_departure_time' in df_fms_unique.columns and plat_col_unique:
        df_dur = df_fms_unique.copy()
        try:
            df_dur['t_load'] = pd.to_datetime(df_dur['loading_time'], errors='coerce')
            df_dur['t_dept'] = pd.to_datetime(df_dur['actual_departure_time'], errors='coerce')
            df_dur['Duration_Mins'] = (df_dur['t_dept'] - df_dur['t_load']).dt.total_seconds() / 60
            
            for plat in df_dur[plat_col_unique].dropna().unique():
                df_plat = df_dur[df_dur[plat_col_unique] == plat]
                vendor = df_plat['agency_name'].iloc[0] if 'agency_name' in df_plat.columns else "Unknown"
                
                avg_dur = df_plat['Duration_Mins'].mean()
                avg_dur_str = f"{int(avg_dur)} Menit" if pd.notna(avg_dur) else "N/A"
                
                with st.expander(f"⏱️ DURASI LOAD: {plat} [{vendor}] | Rata-rata Durasi: {avg_dur_str}"):
                    cols_show = [c for c in ['lh_trip_number', 'parsed_dest', 'trip_type', 'loading_time', 'actual_departure_time'] if c in df_plat.columns]
                    st.dataframe(apply_index_1(df_plat[cols_show]), use_container_width=True)
        except: 
            st.info("Gagal proses hitung durasi log.")

# ==============================================================================
# RENDER: TAB.3 SPECIAL OVERALL GDGP COMPARTMENT (REFACTORED & BULLETPROOF)
# ==============================================================================
elif pilihan_tab == "🏆 TAB.3 SPECIAL OVERALL GDGP":
    st.title("🏆 TAB.3 PERFORMANCE OVERALL BANK DATA RECORDS")
    st.markdown("---")
    
    st.markdown("### 📂 Gudang Bank Data & Fitur Ekstraksi Berkas")
    
    if os.path.exists(BASE_DIR):
        all_dbs = [f for f in os.listdir(BASE_DIR) if f.lower().endswith('.db')]
        if all_dbs:
            st.info(f"Kamar Record Nemokno **{len(all_dbs)} Berkas Laporan Terkunci (Auto Cut-Off 23:59)**.")
            
            gudang_komparasi = []
            for db_f in all_dbs:
                p_db = os.path.join(BASE_DIR, db_f)
                try:
                    with sqlite3.connect(p_db) as c_temp:
                        tbl_check = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", c_temp)
                        existing_tables = tbl_check['name'].tolist() if not tbl_check.empty else []
                        
                        f_count = len(pd.read_sql_query("SELECT * FROM staging_fms_handedover", c_temp)) if "staging_fms_handedover" in existing_tables else 0
                        g_count = len(pd.read_sql_query("SELECT * FROM gdocs_pulled_data", c_temp)) if "gdocs_pulled_data" in existing_tables else 0
                        
                        idx_acc = (g_count / f_count * 100.0) if f_count > 0 else 0.0
                        idx_acc = min(idx_acc, 100.0)
                        
                        gudang_komparasi.append({
                            "Nama Berkas": db_f, 
                            "FMS Rows": f_count, 
                            "GDocs Rows": g_count, 
                            "Indeks GDGP (%)": round(idx_acc, 2)
                        })
                except: 
                    continue
            
            df_bank = pd.DataFrame(gudang_komparasi)
            
            if not df_bank.empty:
                st.dataframe(apply_index_1(df_bank), use_container_width=True)
                overall_avg = df_bank['Indeks GDGP (%)'].mean()
                st.markdown(f"""
                    <div style="background: #1e1b4b; padding: 20px; border-radius: 8px; border: 2px solid #3b82f6; text-align: center;">
                        <h3 style='margin:0; color:#93c5fd;'>🎯 OVERALL GDGP COMPARTMENT HISTORIS INDEX</h3>
                        <h1 style='margin:10px 0; font-size:42px; color:#ffffff;'>{overall_avg:.2f}%</h1>
                        <p style='margin:0; font-size:12px; color:#60a5fa;'>Rata-rata kumulatif akurasi sinkronisasi sak njerone Gudang Bank Data</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("#### 💾 Ekstraksi & Download Kamar Berkas")
                opsi_dl = st.selectbox("Pilih file neng Bank Data sing arep mbok download:", options=all_dbs)
                
                try:
                    with open(os.path.join(BASE_DIR, opsi_dl), "rb") as f_dl:
                        st.download_button(
                            label=f"📥 DOWNLOAD BERKAS {opsi_dl}",
                            data=f_dl,
                            file_name=opsi_dl,
                            mime="application/octet-stream"
                        )
                except Exception as e:
                    st.error(f"Gagal membaca file untuk di-download: {str(e)}")
            else:
                st.warning("Gudang kosong utowo file basis data ora teko-toko.")
        else:
            st.warning("Gudang kosong, durung ono file `.db` liyane.")
    else:
        st.error("Direktori basis data (BASE_DIR) tidak ditemukan.")

# ==============================================================================
# RENDER KAMAR BARU: 📊 TONASE MONITORING FREIGHT (TRUE REAL MASTER LAYOUT)
# ==============================================================================
else:
    st.title("📊 TONASE MONITORING FREIGHT (SURABAYA DC EXECUTIVE TRACKING)")
    st.markdown("---")
    
    if df_fms_unique.empty:
        st.warning("Data Transaksi Handedover Kosong. Gak ono data sing iso diolah.")
    else:
        df_fms_monitoring = df_fms_unique.copy()
        
        for core_col in ['actual_departure_time', 'outbound_weight_kg', 'parsed_dest', 'agency_name', 'lh_trip_name', 'trip_type']:
            if core_col not in df_fms_monitoring.columns:
                df_fms_monitoring[core_col] = 0.0 if 'weight' in core_col else "Unknown"
        
        df_fms_monitoring['actual_departure_time'] = pd.to_datetime(df_fms_monitoring['actual_departure_time'], errors='coerce')
        df_fms_monitoring['Hour_String'] = df_fms_monitoring['actual_departure_time'].dt.strftime('%H:00').fillna('00:00')
        
        df_fms_monitoring['outbound_weight_kg'] = pd.to_numeric(
            df_fms_monitoring['outbound_weight_kg'].astype(str).str.replace(',', ''), errors='coerce'
        ).fillna(0.0)
        
        df_fms_monitoring['parsed_dest'] = df_fms_monitoring['lh_trip_name'].astype(str).apply(
            lambda x: x.split('>')[1].split('(')[0].strip() if '>' in x else x.strip()
        )
        
        # ----------------------------------------------------------------------
        # PINNED & HARDCODED REAL VENDOR MAPPING (STRICT FILTER)
        # ----------------------------------------------------------------------
        VENDOR_REAL_AIR = ['CKL', 'Avia Cargo', 'Lion Parcel', 'AB Cargo', 'ESP', 'Cipta Global']
        VENDOR_REAL_SEA = ['DHS', 'CKL', 'PBI', 'AB Cargo']
        master_hours = [f"{str(h).zfill(2)}:00" for h in range(24)]
        
        base_air_list = BY_AIR_DEST_LIST if 'BY_AIR_DEST_LIST' in globals() else []
        base_sea_list = BY_SEA_DEST_LIST if 'BY_SEA_DEST_LIST' in globals() else []
        
        df_air_freight = df_fms_monitoring[
            df_fms_monitoring['parsed_dest'].isin(base_air_list) & 
            df_fms_monitoring['agency_name'].isin(VENDOR_REAL_AIR) &
            (df_fms_monitoring['trip_type'].astype(str).str.strip().str.lower() == 'by air')
        ]
        df_sea_freight = df_fms_monitoring[
            df_fms_monitoring['parsed_dest'].isin(base_sea_list) & 
            df_fms_monitoring['agency_name'].isin(VENDOR_REAL_SEA) &
            (df_fms_monitoring['trip_type'].astype(str).str.strip().str.lower() == 'by sea')
        ]
        
        # ----------------------------------------------------------------------
        # MATRIX 1: PEROLEHAN TONASE PER DESTINASI & VENDOR STRATEGIS
        # ----------------------------------------------------------------------
        st.markdown("### 🗂️ MATRIX 1: PEROLEHAN TONASE PER DESTINASI & VENDOR STRATEGIS (LOCKED STRUCTURE)")
        col_m1_left, col_m1_right = st.columns(2)
        
        with col_m1_left:
            st.markdown("✈️ **DESTINASI AIRFREIGHT SURABAYA DC**")
            base_index_air = sorted(list(set(base_air_list))) if base_air_list else ["No Destination"]
            
            if not df_air_freight.empty:
                pivot_air = df_air_freight.pivot_table(
                    index='parsed_dest',
                    columns='agency_name',
                    values='outbound_weight_kg',
                    aggfunc='sum'
                ).reindex(index=base_index_air, columns=VENDOR_REAL_AIR, fill_value=0.0)
            else:
                pivot_air = pd.DataFrame(0.0, index=base_index_air, columns=VENDOR_REAL_AIR)
                
            sum_vendor_air = pivot_air.sum()
            pivot_air['Grand Total Tonase By Dest'] = pivot_air.sum(axis=1)
            
            df_air_total = pd.DataFrame(
                [list(sum_vendor_air) + [sum_vendor_air.sum()]], 
                columns=pivot_air.columns, 
                index=['GRAND TOTAL VENDOR']
            ).astype(float)
            
            df_air_display = pd.concat([df_air_total, pivot_air]).fillna(0.0)
            # Dibiarkan index aslinya agar Matriks Label tidak rusak (namun tetap Full Width)
            st.dataframe(df_air_display, use_container_width=True)
                
        with col_m1_right:
            st.markdown("🚢 **DESTINASI SEAFREIGHT SURABAYA DC**")
            base_index_sea = sorted(list(set(base_sea_list))) if base_sea_list else ["No Destination"]
            
            if not df_sea_freight.empty:
                pivot_sea = df_sea_freight.pivot_table(
                    index='parsed_dest',
                    columns='agency_name',
                    values='outbound_weight_kg',
                    aggfunc='sum'
                ).reindex(index=base_index_sea, columns=VENDOR_REAL_SEA, fill_value=0.0)
            else:
                pivot_sea = pd.DataFrame(0.0, index=base_index_sea, columns=VENDOR_REAL_SEA)
                
            sum_vendor_sea = pivot_sea.sum()
            pivot_sea['Grand Total Tonase By Dest'] = pivot_sea.sum(axis=1)
            
            df_sea_total = pd.DataFrame(
                [list(sum_vendor_sea) + [sum_vendor_sea.sum()]], 
                columns=pivot_sea.columns, 
                index=['GRAND TOTAL VENDOR']
            ).astype(float)
            
            df_sea_display = pd.concat([df_sea_total, pivot_sea]).fillna(0.0)
            st.dataframe(df_sea_display, use_container_width=True)
                
        st.markdown("---")
        
        # ----------------------------------------------------------------------
        # MATRIX 2: HOURLY TONNAGE TRACKING PER VENDOR (RITME OPERASIONAL)
        # ----------------------------------------------------------------------
        st.markdown("### ⏱️ MATRIX 2: HOURLY TONNAGE TRACKING PER VENDOR (RITME OPERASIONAL - LOCKED ROWS/COLS)")
        col_m2_left, col_m2_right = st.columns(2)
        
        with col_m2_left:
            st.markdown("✈️ **HOURLY TONASE AIRFREIGHT TRAFFIC**")
            
            if not df_air_freight.empty:
                pivot_h_air = df_air_freight.pivot_table(
                    index='Hour_String',
                    columns='agency_name',
                    values='outbound_weight_kg',
                    aggfunc='sum'
                ).reindex(index=master_hours, columns=VENDOR_REAL_AIR, fill_value=0.0)
            else:
                pivot_h_air = pd.DataFrame(0.0, index=master_hours, columns=VENDOR_REAL_AIR)
                
            sum_h_vendor_air = pivot_h_air.sum()
            pivot_h_air['Grand Total Hours Tonase'] = pivot_h_air.sum(axis=1)
            
            df_h_air_total = pd.DataFrame(
                [list(sum_h_vendor_air) + [sum_h_vendor_air.sum()]], 
                columns=pivot_h_air.columns, 
                index=['GRAND TOTAL VENDOR']
            ).astype(float)
            
            df_h_air_display = pd.concat([df_h_air_total, pivot_h_air]).fillna(0.0)
            st.dataframe(df_h_air_display, use_container_width=True)
                
        with col_m2_right:
            st.markdown("🚢 **HOURLY TONASE SEAFREIGHT TRAFFIC**")
            
            if not df_sea_freight.empty:
                pivot_h_sea = df_sea_freight.pivot_table(
                    index='Hour_String',
                    columns='agency_name',
                    values='outbound_weight_kg',
                    aggfunc='sum'
                ).reindex(index=master_hours, columns=VENDOR_REAL_SEA, fill_value=0.0)
            else:
                pivot_h_sea = pd.DataFrame(0.0, index=master_hours, columns=VENDOR_REAL_SEA)
                
            sum_h_vendor_sea = pivot_h_sea.sum()
            pivot_h_sea['Grand Total Hours Tonase'] = pivot_h_sea.sum(axis=1)
            
            df_h_sea_total = pd.DataFrame(
                [list(sum_h_vendor_sea) + [sum_h_vendor_sea.sum()]], 
                columns=pivot_h_sea.columns, 
                index=['GRAND TOTAL VENDOR']
            ).astype(float)
            
            df_h_sea_display = pd.concat([df_h_sea_total, pivot_h_sea]).fillna(0.0)
            st.dataframe(df_h_sea_display, use_container_width=True)
