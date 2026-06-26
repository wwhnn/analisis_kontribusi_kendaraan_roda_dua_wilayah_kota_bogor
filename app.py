# ════════════════════════════════════════════════════════════
# IMPORT
# ════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
import json
import os
import io
from streamlit_folium import st_folium
from folium.plugins import Fullscreen

import db
import auth

try:
    import geopandas as gpd
    HAS_GPD = True
except ImportError:
    HAS_GPD = False

# ════════════════════════════════════════════════════════════
# KONFIGURASI HALAMAN
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="R2 Analytics – Kota Bogor",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🏍️",
)

st.markdown("""
<style>
.main-header {
    background: linear-gradient(90deg, #b71c1c, #e53935);
    padding: 20px; border-radius: 10px;
    margin-bottom: 20px; color: #fff; text-align: center;
}
.card {
    background-color: #f8f9fa; padding: 18px; border-radius: 10px;
    margin: 10px 0; border: 1px solid #e0e0e0; color: #333;
}
.stat-box {
    background-color: #fff3f3; border-left: 4px solid #e53935;
    padding: 10px 14px; border-radius: 4px; margin: 5px 0; color: #333;
}
.kpi-box {
    background: linear-gradient(135deg, #ffcdd2, #ef9a9a);
    padding: 16px; border-radius: 10px; text-align: center;
    margin: 6px; color: #1a2526;
}
.insight-box {
    background-color: #e8f5e9; border-left: 4px solid #2e7d32;
    padding: 12px 16px; border-radius: 4px; margin: 8px 0; color: #1a2526;
}
.warn-box {
    background-color: #fff8e1; border-left: 4px solid #f9a825;
    padding: 12px 16px; border-radius: 4px; margin: 8px 0; color: #1a2526;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# DATA KELURAHAN (dari database MySQL)
# ════════════════════════════════════════════════════════════
TAHUN_LIST = [2022, 2023, 2024, 2025]


@st.cache_data(show_spinner="Memuat data dari database...")
def load_data():
    """Ambil tabel r2_data dari MySQL dan bentuk struktur nested
    {kecamatan: {kelurahan: {"r2022":.., "r2023":.., ...}}}, plus total kota per tahun."""
    df = db.fetch_all()
    data_kel = {}
    for row in df.itertuples(index=False):
        kec_dict = data_kel.setdefault(row.kecamatan, {})
        kel_dict = kec_dict.setdefault(row.kelurahan, {})
        kel_dict[f"r{row.tahun}"] = int(row.jumlah)
    total_kota = {yr: int(df.loc[df["tahun"] == yr, "jumlah"].sum()) for yr in TAHUN_LIST}
    return data_kel, total_kota


try:
    DATA_KEL, TOTAL_KOTA = load_data()
except Exception as e:
    st.error(f"❌ Gagal terhubung ke database MySQL: {e}")
    st.stop()

KECAMATAN  = list(DATA_KEL.keys())
COLORS_KEC = ["#bd0026","#e31a1c","#fc4e2a","#fd8d3c","#feb24c","#fed976"]
SHP_PATH   = os.path.join("data","Kota_bogor.shp")

CENTROID = {
    "BOGOR BARAT":   (-6.5771, 106.7459),
    "TANAH SAREAL":  (-6.5523, 106.7703),
    "BOGOR UTARA":   (-6.5389, 106.8094),
    "BOGOR SELATAN": (-6.6056, 106.7789),
    "BOGOR TENGAH":  (-6.5823, 106.7878),
    "BOGOR TIMUR":   (-6.5712, 106.8234),
}

GEOJSON_FALLBACK = {"type":"FeatureCollection","features":[
    {"type":"Feature","properties":{"NAMOBJ":"BOGOR BARAT"},
     "geometry":{"type":"Polygon","coordinates":[[[106.7152,-6.5493],[106.7298,-6.5389],[106.7420,-6.5401],[106.7612,-6.5489],[106.7698,-6.5623],[106.7601,-6.5812],[106.7421,-6.5934],[106.7198,-6.5876],[106.7052,-6.5701],[106.7082,-6.5543],[106.7152,-6.5493]]]}},
    {"type":"Feature","properties":{"NAMOBJ":"TANAH SAREAL"},
     "geometry":{"type":"Polygon","coordinates":[[[106.7420,-6.5401],[106.7612,-6.5489],[106.7801,-6.5398],[106.7923,-6.5312],[106.7987,-6.5489],[106.7876,-6.5623],[106.7698,-6.5623],[106.7612,-6.5489],[106.7420,-6.5401]]]}},
    {"type":"Feature","properties":{"NAMOBJ":"BOGOR UTARA"},
     "geometry":{"type":"Polygon","coordinates":[[[106.7801,-6.5398],[106.7923,-6.5312],[106.8101,-6.5198],[106.8289,-6.5212],[106.8356,-6.5401],[106.8201,-6.5578],[106.7987,-6.5489],[106.7801,-6.5398]]]}},
    {"type":"Feature","properties":{"NAMOBJ":"BOGOR SELATAN"},
     "geometry":{"type":"Polygon","coordinates":[[[106.7421,-6.5934],[106.7601,-6.5812],[106.7698,-6.5623],[106.7876,-6.5623],[106.8023,-6.5756],[106.8156,-6.5934],[106.8089,-6.6189],[106.7876,-6.6312],[106.7623,-6.6289],[106.7378,-6.6134],[106.7289,-6.5987],[106.7421,-6.5934]]]}},
    {"type":"Feature","properties":{"NAMOBJ":"BOGOR TENGAH"},
     "geometry":{"type":"Polygon","coordinates":[[[106.7698,-6.5623],[106.7876,-6.5623],[106.8023,-6.5756],[106.8089,-6.5934],[106.7934,-6.6023],[106.7756,-6.5978],[106.7623,-6.5867],[106.7698,-6.5623]]]}},
    {"type":"Feature","properties":{"NAMOBJ":"BOGOR TIMUR"},
     "geometry":{"type":"Polygon","coordinates":[[[106.7987,-6.5489],[106.8201,-6.5578],[106.8356,-6.5401],[106.8489,-6.5534],[106.8512,-6.5756],[106.8389,-6.5934],[106.8156,-6.5934],[106.8023,-6.5756],[106.7876,-6.5623],[106.7987,-6.5489]]]}},
]}

# ════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════
def kec_total(kec: str, year: int) -> int:
    return sum(v[f"r{year}"] for v in DATA_KEL[kec].values())

def choropleth_color(val: int, year: int) -> str:
    if year == 2025:
        if val >= 50000: return "#bd0026"
        if val >= 40000: return "#e31a1c"
        if val >= 35000: return "#fc4e2a"
        if val >= 25000: return "#fd8d3c"
        if val >= 20000: return "#feb24c"
        return "#fed976"
    else:
        if val >= 40000: return "#bd0026"
        if val >= 35000: return "#e31a1c"
        if val >= 30000: return "#fc4e2a"
        if val >= 25000: return "#fd8d3c"
        if val >= 20000: return "#feb24c"
        return "#fed976"

def choropleth_color_kel(val: int) -> str:
    """Skala warna untuk choropleth level kelurahan (nilai jauh lebih kecil
    daripada total kecamatan)."""
    if val >= 6000: return "#bd0026"
    if val >= 5000: return "#e31a1c"
    if val >= 4000: return "#fc4e2a"
    if val >= 3000: return "#fd8d3c"
    if val >= 2000: return "#feb24c"
    return "#fed976"

def linear_proj(values: list) -> int:
    n = len(values); xs = list(range(n))
    sx = sum(xs); sy = sum(values)
    sxy = sum(xs[i]*values[i] for i in range(n))
    sx2 = sum(x**2 for x in xs)
    d   = n*sx2 - sx**2
    if d == 0: return values[-1]
    slope = (n*sxy - sx*sy)/d
    return int(round((sy - slope*sx)/n + slope*n))

def calc_cagr(s: int, e: int, y: int = 3) -> float:
    return 0.0 if s == 0 else ((e/s)**(1/y)-1)*100

def build_kec_df() -> pd.DataFrame:
    avg = (TOTAL_KOTA[2025]-TOTAL_KOTA[2022])/TOTAL_KOTA[2022]*100
    rows = []
    for kec in KECAMATAN:
        vals = {yr: kec_total(kec, yr) for yr in [2022,2023,2024,2025]}
        t    = (vals[2025]-vals[2022])/vals[2022]*100
        proj = linear_proj([vals[2022],vals[2023],vals[2024],vals[2025]])
        kls  = "TINGGI" if t-avg>2 else ("RENDAH" if t-avg<-2 else "SEDANG")
        rows.append({
            "Kecamatan":      kec,
            "2022":           vals[2022],
            "2023":           vals[2023],
            "2024":           vals[2024],
            "2025":           vals[2025],
            "Delta 22-23":    vals[2023]-vals[2022],
            "Delta 23-24":    vals[2024]-vals[2023],
            "Delta 24-25":    vals[2025]-vals[2024],
            "Tumbuh (%)":     round(t,2),
            "CAGR (%)":       round(calc_cagr(vals[2022],vals[2025]),2),
            "Proyeksi 2026":  proj,
            "Delta Proj":     proj-vals[2025],
            "Klasifikasi":    kls,
            "Kontribusi (%)": round(vals[2025]/TOTAL_KOTA[2025]*100,2),
            "Jml Kelurahan":  len(DATA_KEL[kec]),
        })
    return pd.DataFrame(rows)

def build_kel_df(kec: str = None) -> pd.DataFrame:
    rows = []
    kecs = [kec] if kec else KECAMATAN
    for k in kecs:
        tot = {yr: kec_total(k, yr) for yr in [2022,2023,2024,2025]}
        for kel, d in DATA_KEL[k].items():
            t    = (d["r2025"]-d["r2022"])/d["r2022"]*100
            proj = linear_proj([d["r2022"],d["r2023"],d["r2024"],d["r2025"]])
            rows.append({
                "Kecamatan":      k,
                "Kelurahan":      kel,
                "2022":           d["r2022"],
                "2023":           d["r2023"],
                "2024":           d["r2024"],
                "2025":           d["r2025"],
                "Delta 22-23":    d["r2023"]-d["r2022"],
                "Delta 23-24":    d["r2024"]-d["r2023"],
                "Delta 24-25":    d["r2025"]-d["r2024"],
                "Tumbuh (%)":     round(t,2),
                "CAGR (%)":       round(calc_cagr(d["r2022"],d["r2025"]),2),
                "Proyeksi 2026":  proj,
                "Delta Proj":     proj-d["r2025"],
                "Share Kec (%)":  round(d["r2025"]/tot[2025]*100,2) if tot[2025]>0 else 0,
            })
    return pd.DataFrame(rows)

def page_header(title: str, subtitle: str = "") -> None:
    sub = f"<p style='margin:4px 0 0;'>{subtitle}</p>" if subtitle else ""
    st.markdown(f'<div class="main-header"><h2 style="margin:0;">{title}</h2>{sub}</div>',
                unsafe_allow_html=True)

def _norm_nama(s: str) -> str:
    return str(s).strip().upper().replace(" ", "")


@st.cache_data(show_spinner="Memuat batas wilayah per kelurahan...")
def load_geodata(year: int) -> tuple:
    """Choropleth level kelurahan langsung dari data/Kota_bogor.shp (68 polygon).
    Tiap polygon kelurahan diberi warna sesuai jumlah R2 kelurahan itu sendiri
    (bukan total kecamatannya)."""
    total = TOTAL_KOTA[year]
    kelurahan_by_norm = {_norm_nama(kel): (kec, kel)
                          for kec, kels in DATA_KEL.items() for kel in kels}

    def enrich(gj, kel_field="DESA", kec_field="KECAMATAN"):
        feats = []
        for feat in gj["features"]:
            p = feat.get("properties", {})
            match = kelurahan_by_norm.get(_norm_nama(p.get(kel_field, "")))
            kec, kel = match if match else ("", "")
            d = DATA_KEL.get(kec, {}).get(kel, {})
            val = d.get(f"r{year}", 0)
            pct = round(val / total * 100, 2) if total > 0 else 0
            d22 = d.get("r2022", 0)
            d25 = d.get("r2025", 0)
            feats.append({"type": "Feature", "geometry": feat["geometry"],
                "properties": {**p, "kecamatan": kec, "nama": kel, "r2": val, "persen": pct,
                    "warna": choropleth_color_kel(val),
                    "r2022": d22, "r2025": d25,
                    "tumbuh": round((d25 - d22) / d22 * 100, 2) if d22 > 0 else 0}})
        return {"type": "FeatureCollection", "features": feats}

    if HAS_GPD and os.path.exists(SHP_PATH):
        try:
            gdf = gpd.read_file(SHP_PATH)
            if gdf.crs is None: gdf = gdf.set_crs("EPSG:4326")
            elif gdf.crs.to_epsg()!=4326: gdf = gdf.to_crs("EPSG:4326")
            return enrich(json.loads(gdf.to_json())), "shapefile"
        except Exception:
            pass
    return enrich(GEOJSON_FALLBACK, kel_field="NAMOBJ"), "fallback"


# ════════════════════════════════════════════════════════════
# NAVIGASI
# ════════════════════════════════════════════════════════════
def main():
    st.sidebar.markdown(
        '<div style="background:#b71c1c;color:#fff;padding:12px;border-radius:6px;'
        'text-align:center;margin-bottom:14px;font-size:14px;">'
        '<b>🏍️ R2 Analytics – Kota Bogor</b></div>', unsafe_allow_html=True)
    
    auth.render_login_sidebar() 

    menu = st.sidebar.radio("Pilih Halaman:", [
        "🏠 Beranda",
        "🗺️ Peta Interaktif",
        "📊 Analisis Kecamatan",
        "🏘️ Analisis Kelurahan",
        "📈 Proyeksi 2026",
        "🔍 Analisis Mendalam",
        "🗄️ Kelola Data",
        "📋 Metodologi",
        "ℹ️ Tentang",
    ])
    {
        "🏠 Beranda":           page_beranda,
        "🗺️ Peta Interaktif":  page_peta,
        "📊 Analisis Kecamatan": page_analisis_kec,
        "🏘️ Analisis Kelurahan": page_analisis_kel,
        "📈 Proyeksi 2026":      page_proyeksi,
        "🔍 Analisis Mendalam":  page_analisis_mendalam,
        "🗄️ Kelola Data":        auth.require_admin(page_kelola_data),
        "📋 Metodologi":         page_metodologi,
        "ℹ️ Tentang":            page_tentang,
    }[menu]()


# ════════════════════════════════════════════════════════════
# HALAMAN 1 – BERANDA
# ════════════════════════════════════════════════════════════
def page_beranda():
    page_header("🏍️ R2 Analytics – Kota Bogor",
                "System sebaran kontribusi pajak Kendaraan Roda Dua (R2) Kota Bogor 2022–2025")

    # KPI row
    c1,c2,c3,c4 = st.columns(4)
    avg = (TOTAL_KOTA[2025]-TOTAL_KOTA[2022])/TOTAL_KOTA[2022]*100
    c1.metric("Total R2 (2025)", f"{TOTAL_KOTA[2025]:,}")
    c2.metric("Pertumbuhan 2022–2025", f"+{avg:.2f}%")
    c3.metric("Jumlah Kecamatan", "6")
    c4.metric("Jumlah Kelurahan", "68")

    st.markdown("---")
    col1, col2 = st.columns([2,1])

    with col1:
        st.markdown("""
        <div class="card">
        <h4>🎯 Tujuan Penelitian</h4>
        <p style="text-align:justify;">
        Penelitian ini menganalisis distribusi spasial dan tren temporal kendaraan roda dua (R2)
        di Kota Bogor berdasarkan data pajak kendaraan bermotor tahun 2022–2025, mencakup
        6 kecamatan dan 68 kelurahan. Analisis dilakukan menggunakan pendekatan GIS dan
        statistik untuk mendukung perencanaan transportasi dan kebijakan pajak daerah.
        </p>
        </div>
        """, unsafe_allow_html=True)

        df = build_kec_df()
        st.markdown('<div class="card"><h4>📋 Ringkasan per Kecamatan (2025)</h4>',
                    unsafe_allow_html=True)
        st.dataframe(
            df[["Kecamatan","2025","Tumbuh (%)","CAGR (%)","Klasifikasi","Jml Kelurahan"]],
            use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
        <h4>📍 Lokasi Penelitian</h4>
        <ul>
          <li><b>Kota:</b> Bogor</li>
          <li><b>Provinsi:</b> Jawa Barat</li>
          <li><b>Kecamatan:</b> 6</li>
          <li><b>Kelurahan:</b> 68</li>
          <li><b>Periode:</b> 2022–2025</li>
          <li><b>Sumber:</b> Pajak Kendaraan Bermotor</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div class='card'><h4>📈 Total R2 per Tahun</h4>", unsafe_allow_html=True)
        prev = None
        for yr, tot in TOTAL_KOTA.items():
            d = ""
            if prev:
                p = (tot-prev)/prev*100
                d = f"<span style='color:#888;font-size:12px;'>({p:+.2f}%)</span>"
            st.markdown(f'<div class="stat-box"><b>{yr}</b> — {tot:,} unit {d}</div>',
                        unsafe_allow_html=True)
            prev = tot
        st.markdown("</div>", unsafe_allow_html=True)

    # Chart distribusi 2025
    st.markdown("### 📊 Distribusi R2 per Kecamatan (2025)")
    names  = KECAMATAN
    values = [kec_total(k,2025) for k in KECAMATAN]
    fig = px.pie(names=names, values=values, color_discrete_sequence=COLORS_KEC,
                 title="Distribusi Kendaraan R2 per Kecamatan (2025)")
    st.plotly_chart(fig, use_container_width=True)

    # Top 10 kelurahan
    st.markdown("### 🏆 Top 10 Kelurahan Tertinggi (2025)")
    df_kel = build_kel_df().nlargest(10,"2025")
    fig2 = go.Figure(go.Bar(
        x=df_kel["2025"], y=df_kel["Kelurahan"]+"<br><i>("+df_kel["Kecamatan"]+")</i>",
        orientation="h", marker_color="#e31a1c",
        text=[f"{v:,}" for v in df_kel["2025"]], textposition="outside"))
    fig2.update_layout(title="Top 10 Kelurahan – Jumlah R2 (2025)",
                       xaxis_title="Jumlah R2", height=380,
                       yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════════════════════════════════════
# HALAMAN 2 – PETA INTERAKTIF
# ════════════════════════════════════════════════════════════
def page_peta():
    page_header("🗺️ Peta Interaktif Kendaraan R2 Kota Bogor")
 
    st.sidebar.markdown("### 🎛️ Kontrol Peta")
    year     = st.sidebar.selectbox("Pilih Tahun:", [2022,2023,2024,2025], index=3)
    opacity  = st.sidebar.slider("Transparansi Layer", 0.1, 1.0, 0.75, 0.05)
    show_lbl = st.sidebar.checkbox("Tampilkan Label Kecamatan", value=True)
    show_kel = st.sidebar.checkbox("Tampilkan Label Kelurahan", value=True)
 
    # Pilihan basemap
    st.sidebar.markdown("### 🗺️ Mode Peta")
    BASEMAPS = {
        "🗺️ Peta Jalan (Default)":  ("CartoDB positron",      None, None),
        "🛰️ Satelit (Esri)":         ("https://server.arcgisonline.com/ArcGIS/rest/services/"
                                      "World_Imagery/MapServer/tile/{z}/{y}/{x}",
                                      "Esri WorldImagery",
                                      "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"),
        "🛰️ Satelit + Label (Hybrid)": ("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
                                         "Google Hybrid",
                                         "Map data &copy; Google"),
        "🌍 OpenStreetMap":           ("OpenStreetMap",         None, None),
        "🌑 Dark (CartoDB)":          ("CartoDB dark_matter",   None, None),
        "🏔️ Terrain (ESRI Topo)":     ("https://server.arcgisonline.com/ArcGIS/rest/services/"
                                       "World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
                                       "ESRI Topo",
                                       "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), and the GIS User Community"),
    }
    basemap_choice = st.sidebar.selectbox(
        "Pilih Basemap:", list(BASEMAPS.keys()), index=0
    )
 
    st.sidebar.markdown("### 🎨 Legenda (per Kelurahan)")
    leg = [("≥ 6.000","#bd0026"),("5.000–5.999","#e31a1c"),("4.000–4.999","#fc4e2a"),
           ("3.000–3.999","#fd8d3c"),("2.000–2.999","#feb24c"),("< 2.000","#fed976")]
    for lbl, col in leg:
        st.sidebar.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;">'
            f'<span style="background:{col};width:16px;height:16px;display:inline-block;'
            f'border-radius:3px;border:1px solid #aaa;"></span>'
            f'<span style="font-size:13px;">{lbl}</span></div>', unsafe_allow_html=True)
 
    total = TOTAL_KOTA[year]
    col_map, col_stat = st.columns([3,1])
 
    with col_map:
        geojson, source = load_geodata(year)
        if source == "shapefile":
            st.success("✅ Batas wilayah per kelurahan dari shapefile (data/Kota_bogor.shp)")
        else:
            st.info("ℹ️ Batas wilayah approx — letakkan shapefile di `data/Kota_bogor.shp`")
 
        # ── Build peta dengan basemap terpilih ───────────────
        bm_tiles, bm_name, bm_attr = BASEMAPS[basemap_choice]
 
        # Basemap bawaan folium (string pendek)
        if bm_name is None:
            m = folium.Map(
                location=[-6.595, 106.800],
                zoom_start=13,
                tiles=bm_tiles,
            )
        else:
            # Basemap custom (URL tile)
            m = folium.Map(
                location=[-6.595, 106.800],
                zoom_start=13,
                tiles=None,
            )
            folium.TileLayer(
                tiles=bm_tiles,
                name=bm_name,
                attr=bm_attr,
                max_zoom=20,
            ).add_to(m)
 
        # Tambahkan semua opsi basemap ke layer control
        folium.TileLayer("CartoDB positron",   name="🗺️ Peta Jalan").add_to(m)
        folium.TileLayer("OpenStreetMap",      name="🌍 OpenStreetMap").add_to(m)
        folium.TileLayer("CartoDB dark_matter",name="🌑 Dark").add_to(m)
        folium.TileLayer(
            tiles=("https://server.arcgisonline.com/ArcGIS/rest/services/"
                   "World_Imagery/MapServer/tile/{z}/{y}/{x}"),
            name="🛰️ Satelit",
            attr="Tiles &copy; Esri",
            max_zoom=20,
        ).add_to(m)
        folium.TileLayer(
            tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
            name="🛰️ Hybrid",
            attr="Map data &copy; Google",
            max_zoom=20,
        ).add_to(m)
        folium.TileLayer(
            tiles=("https://server.arcgisonline.com/ArcGIS/rest/services/"
                   "World_Topo_Map/MapServer/tile/{z}/{y}/{x}"),
            name="🏔️ Terrain",
            attr="Tiles &copy; Esri",
            max_zoom=20,
        ).add_to(m)
 
        Fullscreen().add_to(m)
 
        def style_fn(f):
            return {"fillColor":f["properties"]["warna"],"color":"black",
                    "weight":2.0,"fillOpacity":opacity,"opacity":1.0}
        def hl_fn(f):
            return {"fillColor":f["properties"]["warna"],"color":"white",
                    "weight":3.5,"fillOpacity":min(opacity+0.15,1.0)}
 
        folium.GeoJson(
            geojson, name="Batas Kelurahan",
            style_function=style_fn, highlight_function=hl_fn,
            tooltip=folium.GeoJsonTooltip(
                fields=["nama","kecamatan","r2","persen","tumbuh"],
                aliases=["Kelurahan:","Kecamatan:",f"R2 ({year}):","Kontribusi Kota (%):","Tumbuh 22-25 (%):"],
                localize=True, sticky=True, labels=True,
                style="background-color:white;color:#333;font-family:Arial;font-size:13px;padding:8px;border-radius:4px;"),
            popup=folium.GeoJsonPopup(
                fields=["nama","kecamatan","r2022","r2","persen","tumbuh"],
                aliases=["Kelurahan:","Kecamatan:","R2 2022:","R2 2025:","Kontribusi Kota (%):","Tumbuh 22-25 (%):"],
                localize=True, max_width=280),
        ).add_to(m)
 
        if show_lbl:
            kec_label_group = folium.FeatureGroup(name="🏙️ Label Kecamatan", show=True)
            for kec,(lat,lon) in CENTROID.items():
                val = kec_total(kec, year)
                # Warna teks berbeda tergantung basemap
                is_dark = "dark" in basemap_choice.lower() or "satelit" in basemap_choice.lower() or "hybrid" in basemap_choice.lower()
                txt_color = "#fff"
                shadow    = "1px 1px 0 #000,-1px 1px 0 #000,1px -1px 0 #000,-1px -1px 0 #000"
                folium.Marker(
                    location=[lat,lon],
                    icon=folium.DivIcon(
                        html=(
                            f'<div style="font-size:10px;font-weight:bold;color:{txt_color};'
                            f'text-shadow:{shadow};text-align:center;'
                            f'line-height:1.4;pointer-events:none;white-space:nowrap;">'
                            f'{kec}<br>'
                            f'<span style="font-size:9px;">{val:,}</span></div>'
                        ),
                        icon_size=(140,36), icon_anchor=(70,18),
                    ),
                ).add_to(kec_label_group)
            kec_label_group.add_to(m)
 
        # ── Label Kelurahan (opsional) ────────────────────────
        if show_kel:
            kel_label_group = folium.FeatureGroup(name="🏘️ Label Kelurahan", show=True)
            # Warna label kelurahan
            kel_colors = {
                "BOGOR BARAT":   "#fff",
                "TANAH SAREAL":  "#fff",
                "BOGOR UTARA":   "#fff",
                "BOGOR SELATAN": "#fff",
                "BOGOR TENGAH":  "#fff",
                "BOGOR TIMUR":   "#fff",
            }
            # Koordinat centroid per kelurahan, dihitung otomatis dari shapefile
            # dan disimpan di tabel kelurahan_geo (lihat scripts/import_centroid.py)
            CENTROID_KEL = db.fetch_centroid_kel()
            for kec, kels in DATA_KEL.items():
                for kel, d in kels.items():
                    val = d[f"r{year}"]
                    coords = CENTROID_KEL.get(kel)
                    if not coords:
                        continue
                    folium.Marker(
                        location=list(coords),
                        icon=folium.DivIcon(
                            html=(
                                f'<div style="font-size:7px;font-weight:500;'
                                f'color:#fff;background:rgba(0,0,0,0.55);'
                                f'padding:1px 4px;border-radius:3px;'
                                f'text-align:center;line-height:1.4;'
                                f'pointer-events:none;white-space:nowrap;">'
                                f'{kel}<br>'
                                f'<span style="font-size:7px;opacity:0.9;">{val:,}</span>'
                                f'</div>'
                            ),
                            icon_size=(110, 28),
                            icon_anchor=(55, 14),
                        ),
                    ).add_to(kel_label_group)
            kel_label_group.add_to(m)
 
        folium.LayerControl(collapsed=False).add_to(m)
        map_data = st_folium(m, width="100%", height=580, returned_objects=["last_clicked"])
 
    with col_stat:
        st.markdown(f"### 📊 Ranking {year}")
        
        sorted_kec = sorted(KECAMATAN, key=lambda k: kec_total(k,year), reverse=True)
        for rank, kec in enumerate(sorted_kec, 1):
            val = kec_total(kec, year)
            pct = val/total*100
            col_h = choropleth_color(val, year)
            n_kel = len(DATA_KEL[kec])
            st.markdown(
                f'<div class="stat-box">'
                f'<span style="color:{col_h};font-weight:bold;">#{rank} {kec}</span><br>'
                f'{val:,} unit ({pct:.1f}%)<br>'
                f'<span style="font-size:11px;color:#888;">{n_kel} kelurahan</span></div>',
                unsafe_allow_html=True)
        st.markdown(
            f'<div class="card" style="margin-top:10px;">'
            f'<b>Total {year}:</b><br>'
            f'<span style="font-size:20px;font-weight:bold;color:#b71c1c;">{total:,}</span> unit</div>',
            unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# HALAMAN 3 – ANALISIS KECAMATAN
# ════════════════════════════════════════════════════════════
def page_analisis_kec():
    page_header("📊 Analisis Kendaraan R2 per Kecamatan")

    df  = build_kec_df()
    avg = (TOTAL_KOTA[2025]-TOTAL_KOTA[2022])/TOTAL_KOTA[2022]*100

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total R2 (2025)", f"{TOTAL_KOTA[2025]:,}")
    c2.metric("Pertumbuhan Rata-rata", f"+{avg:.2f}%")
    c3.metric("Pertumbuhan Tertinggi", "Bogor Selatan +18.32%")
    c4.metric("Pertumbuhan Terendah", "Bogor Tengah +6.91%")

    st.markdown("---")
    tab1,tab2,tab3,tab4,tab5 = st.tabs([
        "📈 Tren","📊 Perbandingan","🔼 Pertumbuhan","📋 Tabel","🔬 Korelasi"])

    with tab1:
        fig = go.Figure()
        for i,kec in enumerate(KECAMATAN):
            fig.add_trace(go.Scatter(
                x=[2022,2023,2024,2025],
                y=[kec_total(kec,yr) for yr in [2022,2023,2024,2025]],
                mode="lines+markers", name=kec,
                line=dict(color=COLORS_KEC[i],width=2), marker=dict(size=7)))
        fig.add_trace(go.Bar(
            x=[2022,2023,2024,2025], y=[TOTAL_KOTA[yr] for yr in [2022,2023,2024,2025]],
            name="Total Kota", marker_color="rgba(189,0,38,0.15)",
            yaxis="y2", showlegend=True))
        fig.update_layout(
            title="Tren R2 per Kecamatan (2022–2025)",
            xaxis_title="Tahun", yaxis_title="Jumlah R2",
            xaxis=dict(tickvals=[2022,2023,2024,2025]),
            yaxis2=dict(overlaying="y",side="right",title="Total Kota"),
            legend=dict(orientation="h",y=-0.25))
        st.plotly_chart(fig, use_container_width=True)

        # Total kota
        fig2 = go.Figure(go.Bar(
            x=[2022,2023,2024,2025],
            y=[TOTAL_KOTA[yr] for yr in [2022,2023,2024,2025]],
            marker_color="#e31a1c",
            text=[f"{TOTAL_KOTA[yr]:,}" for yr in [2022,2023,2024,2025]],
            textposition="outside"))
        fig2.update_layout(title="Total R2 Kota Bogor (2022–2025)",
                           xaxis=dict(tickvals=[2022,2023,2024,2025]))
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        yr = st.selectbox("Tahun:", [2022,2023,2024,2025], index=3, key="kec_yr")
        vals = [(kec_total(k,yr), k) for k in KECAMATAN]
        vals.sort(reverse=True)
        v_s, n_s = zip(*vals)
        fig = go.Figure(go.Bar(x=list(n_s), y=list(v_s), marker_color=COLORS_KEC,
                               text=[f"{v:,}" for v in v_s], textposition="outside"))
        fig.update_layout(title=f"Jumlah R2 per Kecamatan ({yr})")
        st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            fig_pie = px.pie(names=list(n_s), values=list(v_s),
                             color_discrete_sequence=COLORS_KEC,
                             title=f"Distribusi R2 ({yr})")
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_b:
            # Stacked bar semua tahun
            fig_stk = go.Figure()
            for yr2 in [2022,2023,2024,2025]:
                fig_stk.add_trace(go.Bar(
                    name=str(yr2),
                    x=KECAMATAN,
                    y=[kec_total(k,yr2) for k in KECAMATAN]))
            fig_stk.update_layout(barmode="group", title="Perbandingan Semua Tahun")
            st.plotly_chart(fig_stk, use_container_width=True)

    with tab3:
        tumbuh = [round((kec_total(k,2025)-kec_total(k,2022))/kec_total(k,2022)*100,2)
                  for k in KECAMATAN]
        bar_c  = ["#1a9641" if t>avg else "#e31a1c" for t in tumbuh]
        fig = go.Figure(go.Bar(x=KECAMATAN, y=tumbuh, marker_color=bar_c,
                               text=[f"{t}%" for t in tumbuh], textposition="outside"))
        fig.add_hline(y=avg, line_dash="dash", line_color="black",
                      annotation_text=f"Rata-rata kota: {avg:.2f}%")
        fig.update_layout(title="Pertumbuhan R2 per Kecamatan 2022–2025 (%)")
        st.plotly_chart(fig, use_container_width=True)

        cagr_v = [round(calc_cagr(kec_total(k,2022),kec_total(k,2025)),2) for k in KECAMATAN]
        fig2 = go.Figure(go.Bar(y=KECAMATAN, x=cagr_v, orientation="h",
                                marker_color="#fd8d3c",
                                text=[f"{c}%" for c in cagr_v], textposition="outside"))
        fig2.update_layout(title="CAGR 2022–2025 per Kecamatan")
        st.plotly_chart(fig2, use_container_width=True)

        # Delta per periode
        fig3 = go.Figure()
        for kec,col in zip(KECAMATAN, COLORS_KEC):
            deltas = [
                kec_total(kec,2023)-kec_total(kec,2022),
                kec_total(kec,2024)-kec_total(kec,2023),
                kec_total(kec,2025)-kec_total(kec,2024),
            ]
            fig3.add_trace(go.Bar(name=kec, x=["22→23","23→24","24→25"], y=deltas,
                                  marker_color=col))
        fig3.update_layout(barmode="group", title="Delta R2 per Periode per Kecamatan")
        st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Unduh CSV Kecamatan", csv,
                           "analisis_kecamatan_r2.csv", "text/csv")

    with tab5:
        st.markdown("#### Korelasi Jumlah Kelurahan vs Total R2 (2025)")
        df_cor = pd.DataFrame({
            "Kecamatan": KECAMATAN,
            "Jumlah Kelurahan": [len(DATA_KEL[k]) for k in KECAMATAN],
            "R2 (2025)": [kec_total(k,2025) for k in KECAMATAN],
            "Pertumbuhan (%)": [round((kec_total(k,2025)-kec_total(k,2022))/kec_total(k,2022)*100,2) for k in KECAMATAN],
        })
        fig_sc = px.scatter(df_cor, x="Jumlah Kelurahan", y="R2 (2025)",
                            size="Pertumbuhan (%)", color="Kecamatan",
                            color_discrete_sequence=COLORS_KEC,
                            text="Kecamatan", title="Scatter: Kelurahan vs R2 2025",
                            trendline="ols")
        st.plotly_chart(fig_sc, use_container_width=True)

        corr = df_cor[["Jumlah Kelurahan","R2 (2025)","Pertumbuhan (%)"]].corr()
        st.markdown("**Matriks Korelasi:**")
        st.dataframe(corr.round(3), use_container_width=True)


# ════════════════════════════════════════════════════════════
# HALAMAN 4 – ANALISIS KELURAHAN
# ════════════════════════════════════════════════════════════
def page_analisis_kel():
    page_header("🏘️ Analisis Kendaraan R2 per Kelurahan")

    # Filter kecamatan
    st.sidebar.markdown("### 🔍 Filter")
    kec_sel = st.sidebar.selectbox("Pilih Kecamatan:", ["SEMUA"] + KECAMATAN)

    df = build_kel_df(None if kec_sel=="SEMUA" else kec_sel)

    n_kel  = len(df)
    top1   = df.nlargest(1,"2025").iloc[0]
    bot1   = df.nsmallest(1,"2025").iloc[0]
    avg_t  = df["Tumbuh (%)"].mean()

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Kelurahan Dianalisis", n_kel)
    c2.metric(f"Tertinggi (2025)", f"{top1['Kelurahan']} {top1['2025']:,}")
    c3.metric("Terendah (2025)", f"{bot1['Kelurahan']} {bot1['2025']:,}")
    c4.metric("Rata-rata Tumbuh", f"{avg_t:.2f}%")

    st.markdown("---")
    tab1,tab2,tab3,tab4 = st.tabs(
        ["📊 Distribusi","📈 Tren","🔼 Pertumbuhan","📋 Tabel Lengkap"])

    with tab1:
        yr = st.selectbox("Tahun:", [2022,2023,2024,2025], index=3, key="kel_yr1")
        col_yr = str(yr)
        df_s   = df.sort_values(col_yr, ascending=False)

        # Bar chart per kelurahan
        fig = go.Figure(go.Bar(
            x=df_s[col_yr],
            y=df_s["Kelurahan"] + " (" + df_s["Kecamatan"].str[:4] + ")",
            orientation="h",
            marker_color=px.colors.sample_colorscale(
                "Reds", [v/df_s[col_yr].max() for v in df_s[col_yr]]),
            text=[f"{v:,}" for v in df_s[col_yr]],
            textposition="outside"))
        fig.update_layout(
            title=f"Distribusi R2 per Kelurahan ({yr})",
            xaxis_title="Jumlah R2",
            yaxis=dict(autorange="reversed"),
            height=max(400, n_kel*22))
        st.plotly_chart(fig, use_container_width=True)

        # Treemap
        fig_tree = px.treemap(
            df_s, path=["Kecamatan","Kelurahan"], values=col_yr,
            color=col_yr, color_continuous_scale="Reds",
            title=f"Treemap R2 per Kelurahan ({yr})")
        st.plotly_chart(fig_tree, use_container_width=True)

    with tab2:
        kel_opts = df["Kelurahan"].tolist()
        kel_sel  = st.multiselect("Pilih Kelurahan:", kel_opts,
                                  default=kel_opts[:5] if len(kel_opts)>=5 else kel_opts)
        if kel_sel:
            fig = go.Figure()
            for kel in kel_sel:
                row = df[df["Kelurahan"]==kel].iloc[0]
                fig.add_trace(go.Scatter(
                    x=[2022,2023,2024,2025],
                    y=[row["2022"],row["2023"],row["2024"],row["2025"]],
                    mode="lines+markers",
                    name=f"{kel} ({row['Kecamatan'][:4]})"))
            fig.update_layout(title="Tren R2 per Kelurahan",
                              xaxis=dict(tickvals=[2022,2023,2024,2025]),
                              legend=dict(orientation="h",y=-0.3))
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        df_s  = df.sort_values("Tumbuh (%)", ascending=False)
        avg_t = df_s["Tumbuh (%)"].mean()
        colors_t = ["#1a9641" if t>avg_t else "#e31a1c" for t in df_s["Tumbuh (%)"]]
        fig = go.Figure(go.Bar(
            y=df_s["Kelurahan"]+" ("+df_s["Kecamatan"].str[:4]+")",
            x=df_s["Tumbuh (%)"], orientation="h",
            marker_color=colors_t,
            text=[f"{t:.1f}%" for t in df_s["Tumbuh (%)"]],
            textposition="outside"))
        fig.add_vline(x=avg_t, line_dash="dash", line_color="black",
                      annotation_text=f"Rata-rata: {avg_t:.2f}%")
        fig.update_layout(
            title="Pertumbuhan R2 per Kelurahan 2022–2025 (%)",
            yaxis=dict(autorange="reversed"),
            height=max(400, n_kel*22))
        st.plotly_chart(fig, use_container_width=True)

        # CAGR
        fig2 = go.Figure(go.Bar(
            y=df_s["Kelurahan"]+" ("+df_s["Kecamatan"].str[:4]+")",
            x=df_s["CAGR (%)"], orientation="h",
            marker_color="#fd8d3c",
            text=[f"{c:.2f}%" for c in df_s["CAGR (%)"]],
            textposition="outside"))
        fig2.update_layout(title="CAGR per Kelurahan 2022–2025",
                           yaxis=dict(autorange="reversed"),
                           height=max(400, n_kel*22))
        st.plotly_chart(fig2, use_container_width=True)

    with tab4:
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Unduh CSV Kelurahan", csv,
                           "analisis_kelurahan_r2.csv", "text/csv")


# ════════════════════════════════════════════════════════════
# HALAMAN 5 – PROYEKSI 2026
# ════════════════════════════════════════════════════════════
def page_proyeksi():
    page_header("📈 Proyeksi Kendaraan R2 Kota Bogor 2026","Metode: Regresi Linear")

    df_kec = build_kec_df()
    df_kel = build_kel_df()

    total_2026_kec = int(df_kec["Proyeksi 2026"].sum())
    delta_kec      = total_2026_kec - TOTAL_KOTA[2025]
    total_2026_kel = int(df_kel["Proyeksi 2026"].sum())

    c1,c2,c3 = st.columns(3)
    c1.metric("Total R2 Aktual (2025)", f"{TOTAL_KOTA[2025]:,}")
    c2.metric("Proyeksi 2026 (sum kec)", f"{total_2026_kec:,}", f"+{delta_kec:,}")
    c3.metric("Kenaikan Proyeksi", f"+{delta_kec/TOTAL_KOTA[2025]*100:.2f}%")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📊 Proyeksi Kecamatan","🏘️ Proyeksi Kelurahan","📋 Tabel"])

    with tab1:
        fig = go.Figure()
        for i,(_, row) in enumerate(df_kec.iterrows()):
            fig.add_trace(go.Bar(
                name=row["Kecamatan"],
                x=["Aktual 2025","Proyeksi 2026"],
                y=[int(row["2025"]),int(row["Proyeksi 2026"])],
                marker_color=COLORS_KEC[i%6],
                text=[f"{int(row['2025']):,}",f"{int(row['Proyeksi 2026']):,}"],
                textposition="auto"))
        fig.update_layout(barmode="group",
                          title="Aktual 2025 vs Proyeksi 2026 – Kecamatan",
                          height=450, yaxis=dict(tickformat=","))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        kec_sel = st.selectbox("Pilih Kecamatan:", KECAMATAN, key="proj_kec")
        df_k    = df_kel[df_kel["Kecamatan"]==kec_sel].sort_values("2025",ascending=False)
        fig2 = go.Figure()
        for _,(_, row) in enumerate(df_k.iterrows()):
            fig2.add_trace(go.Bar(
                name=row["Kelurahan"],
                x=["Aktual 2025","Proyeksi 2026"],
                y=[int(row["2025"]),int(row["Proyeksi 2026"])]))
        fig2.update_layout(barmode="group",
                           title=f"Proyeksi 2026 – Kelurahan {kec_sel}",
                           height=420, yaxis=dict(tickformat=","))
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.markdown("**Proyeksi per Kecamatan**")
        cols_k = ["Kecamatan","2025","Proyeksi 2026","Delta Proj","Tumbuh (%)","CAGR (%)","Klasifikasi"]
        def ck(v):
            if v=="TINGGI": return "background-color:#d4edda;color:#155724"
            if v=="RENDAH": return "background-color:#f8d7da;color:#721c24"
            return "background-color:#fff3cd;color:#856404"
        st.dataframe(
            df_kec[cols_k].style.map(ck,subset=["Klasifikasi"])
            .format({"2025":"{:,.0f}","Proyeksi 2026":"{:,.0f}",
                     "Delta Proj":"{:+,.0f}","Tumbuh (%)":"{:.2f}%","CAGR (%)":"{:.2f}%"}),
            use_container_width=True, hide_index=True)

        st.markdown("**Proyeksi per Kelurahan**")
        cols_l = ["Kecamatan","Kelurahan","2025","Proyeksi 2026","Delta Proj","Tumbuh (%)","CAGR (%)"]
        st.dataframe(
            df_kel[cols_l].style.format(
                {"2025":"{:,.0f}","Proyeksi 2026":"{:,.0f}",
                 "Delta Proj":"{:+,.0f}","Tumbuh (%)":"{:.2f}%","CAGR (%)":"{:.2f}%"}),
            use_container_width=True, hide_index=True)
        csv_all = df_kel[cols_l].to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Unduh CSV Proyeksi Kelurahan", csv_all,
                           "proyeksi_2026_kelurahan.csv","text/csv")

    st.markdown("""
    <div class="card">
    <b>⚠️ Catatan Metode</b><br>
    Proyeksi menggunakan regresi linear dari 4 titik data (2022–2025).
    Hasilnya bersifat indikatif.
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# HALAMAN 6 – ANALISIS MENDALAM (DIPERBAIKI)
# ════════════════════════════════════════════════════════════
def page_analisis_mendalam():
    page_header("🔍 Analisis Mendalam R2 Kota Bogor")

    df_kec = build_kec_df()
    df_kel = build_kel_df()
    avg_k  = df_kec["Tumbuh (%)"].mean()
    avg_l  = df_kel["Tumbuh (%)"].mean()

    tab1,tab2,tab3,tab4 = st.tabs([
        "🏆 Ranking & Klasifikasi",
        "📉 Anomali & Fluktuasi",
        "🔗 Konsentrasi Spasial",
        "📝 Ringkasan Analisis"])

    with tab1:
        st.markdown("#### Klasifikasi Kecamatan vs Rata-rata Kota")
        for _, row in df_kec.sort_values("Tumbuh (%)",ascending=False).iterrows():
            kls   = row["Klasifikasi"]
            color = "#155724" if kls=="TINGGI" else ("#721c24" if kls=="RENDAH" else "#856404")
            bg    = "#d4edda" if kls=="TINGGI" else ("#f8d7da" if kls=="RENDAH" else "#fff3cd")
            st.markdown(
                f'<div style="background:{bg};border-left:4px solid {color};'
                f'padding:10px 14px;border-radius:4px;margin:5px 0;color:{color};">'
                f'<b>{row["Kecamatan"]}</b> — Tumbuh {row["Tumbuh (%)"]:.2f}% '
                f'| CAGR {row["CAGR (%)"]:.2f}% | Klasifikasi: <b>{kls}</b><br>'
                f'2022: {row["2022"]:,} → 2025: {row["2025"]:,} '
                f'(+{row["2025"]-row["2022"]:,} unit)</div>',
                unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"#### Top 10 Kelurahan Pertumbuhan Tertinggi (vs rata-rata {avg_l:.2f}%)")
        top10 = df_kel.nlargest(10,"Tumbuh (%)")[
            ["Kecamatan","Kelurahan","2022","2025","Tumbuh (%)","CAGR (%)"]]
        st.dataframe(top10.style.format(
            {"2022":"{:,}","2025":"{:,}","Tumbuh (%)":"{:.2f}%","CAGR (%)":"{:.2f}%"}),
            use_container_width=True, hide_index=True)

        st.markdown("#### Bottom 10 Kelurahan Pertumbuhan Terendah")
        bot10 = df_kel.nsmallest(10,"Tumbuh (%)")[
            ["Kecamatan","Kelurahan","2022","2025","Tumbuh (%)","CAGR (%)"]]
        st.dataframe(bot10.style.format(
            {"2022":"{:,}","2025":"{:,}","Tumbuh (%)":"{:.2f}%","CAGR (%)":"{:.2f}%"}),
            use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("#### Kelurahan dengan Delta Negatif 2022→2023 atau 2023→2024")
        anomali = df_kel[(df_kel["Delta 22-23"]<0) | (df_kel["Delta 23-24"]<0)].copy()
        anomali = anomali.sort_values("Delta 22-23")
        st.markdown(f"**{len(anomali)} kelurahan** mengalami penurunan di setidaknya satu periode")
        
        # PERBAIKAN: Gunakan apply dan lambda sebagai pengganti applymap
        def color_delta(val):
            return "color: red" if val < 0 else "color: green"
        
        st.dataframe(
            anomali[["Kecamatan","Kelurahan","2022","2023","2024","2025",
                     "Delta 22-23","Delta 23-24","Delta 24-25","Tumbuh (%)"]].style.format(
                {"2022":"{:,}","2023":"{:,}","2024":"{:,}","2025":"{:,}",
                 "Delta 22-23":"{:+,}","Delta 23-24":"{:+,}","Delta 24-25":"{:+,}",
                 "Tumbuh (%)":"{:.2f}%"}).apply(
                lambda x: [color_delta(v) for v in x] if x.name in ["Delta 22-23","Delta 23-24","Delta 24-25"] else ['']*len(x),
                axis=0),
            use_container_width=True, hide_index=True)

        # Heatmap delta per periode
        st.markdown("#### Heatmap Delta Pertumbuhan per Kelurahan")
        pivot = df_kel.set_index("Kelurahan")[["Delta 22-23","Delta 23-24","Delta 24-25"]]
        fig_hm = go.Figure(go.Heatmap(
            z=pivot.values,
            x=["22→23","23→24","24→25"],
            y=pivot.index.tolist(),
            colorscale="RdYlGn",
            zmid=0,
            text=pivot.values,
            texttemplate="%{text:+,}",
            textfont=dict(size=8)))
        fig_hm.update_layout(
            title="Heatmap Delta R2 per Kelurahan per Periode",
            height=max(500, len(pivot)*16),
            yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_hm, use_container_width=True)

    with tab3:
        st.markdown("#### Konsentrasi R2: Share Kelurahan dalam Kecamatan (2025)")
        for kec in KECAMATAN:
            df_k = df_kel[df_kel["Kecamatan"]==kec].sort_values("2025",ascending=False)
            total_kec = df_k["2025"].sum()
            top3_share = df_k.nlargest(3,"2025")["2025"].sum()/total_kec*100 if total_kec>0 else 0
            st.markdown(
                f'<div class="stat-box"><b>{kec}</b> — '
                f'Top 3 kelurahan menguasai <b>{top3_share:.1f}%</b> dari total kecamatan</div>',
                unsafe_allow_html=True)

        # Pie per kecamatan
        kec_pie = st.selectbox("Detail distribusi kelurahan:", KECAMATAN, key="pie_kec")
        df_pie  = df_kel[df_kel["Kecamatan"]==kec_pie].sort_values("2025",ascending=False)
        fig_pie = px.pie(df_pie, names="Kelurahan", values="2025",
                         title=f"Distribusi R2 Kelurahan – {kec_pie} (2025)",
                         color_discrete_sequence=px.colors.sequential.Reds_r)
        st.plotly_chart(fig_pie, use_container_width=True)

        # Konsentrasi index (HHI sederhana)
        st.markdown("#### Indeks Konsentrasi (HHI) per Kecamatan")
        hhi_data = []
        for kec in KECAMATAN:
            df_k  = df_kel[df_kel["Kecamatan"]==kec]
            tot   = df_k["2025"].sum()
            hhi   = sum((v/tot*100)**2 for v in df_k["2025"]) if tot>0 else 0
            hhi_data.append({"Kecamatan":kec,"HHI":round(hhi,1),
                             "Interpretasi":"Terkonsentrasi" if hhi>2500 else "Terdistribusi"})
        df_hhi = pd.DataFrame(hhi_data)
        st.dataframe(df_hhi, use_container_width=True, hide_index=True)
        st.caption("HHI > 2500: konsentrasi tinggi (dominasi 1-2 kelurahan). HHI < 1500: distribusi merata.")

    with tab4:
        avg_kota = (TOTAL_KOTA[2025]-TOTAL_KOTA[2022])/TOTAL_KOTA[2022]*100
        top_kec  = df_kec.nlargest(1,"Tumbuh (%)").iloc[0]
        bot_kec  = df_kec.nsmallest(1,"Tumbuh (%)").iloc[0]
        top_kel  = df_kel.nlargest(1,"Tumbuh (%)").iloc[0]
        bot_kel  = df_kel.nsmallest(1,"Tumbuh (%)").iloc[0]
        n_turun  = len(df_kel[(df_kel["Delta 22-23"]<0)|(df_kel["Delta 23-24"]<0)])

        st.markdown(f"""
        <div class="insight-box">
        <b>📌 Temuan Utama (Kecamatan)</b><br>
        • Total R2 Kota Bogor tumbuh <b>{avg_kota:.2f}%</b> dari 2022 ke 2025 (202.745 → 230.331 unit)<br>
        • Lonjakan besar terjadi di 2024→2025 (+13,97%), setelah stagnan di 2022–2024<br>
        • Kecamatan dengan pertumbuhan TERTINGGI: <b>{top_kec['Kecamatan']}</b> ({top_kec['Tumbuh (%)']:.2f}%)<br>
        • Kecamatan dengan pertumbuhan TERENDAH: <b>{bot_kec['Kecamatan']}</b> ({bot_kec['Tumbuh (%)']:.2f}%)<br>
        • Bogor Barat tetap mendominasi dengan {kec_total('BOGOR BARAT',2025):,} unit ({kec_total('BOGOR BARAT',2025)/TOTAL_KOTA[2025]*100:.1f}%)
        </div>

        <div class="insight-box">
        <b>📌 Temuan Utama (Kelurahan)</b><br>
        • Terdapat <b>68 kelurahan</b> dengan variasi pertumbuhan yang signifikan<br>
        • Kelurahan pertumbuhan tertinggi: <b>{top_kel['Kelurahan']}</b> ({top_kel['Kecamatan']}) — {top_kel['Tumbuh (%)']:.2f}%<br>
        • Kelurahan pertumbuhan terendah: <b>{bot_kel['Kelurahan']}</b> ({bot_kel['Kecamatan']}) — {bot_kel['Tumbuh (%)']:.2f}%<br>
        • <b>{n_turun} kelurahan</b> mengalami penurunan di minimal 1 periode (2022-2024)<br>
        • Katulampa & Kedung Badak secara konsisten masuk top 3 tertinggi setiap tahun
        </div>

        <div class="warn-box">
        <b>⚠️ Catatan Analisis</b><br>
        • Lonjakan 2025 kemungkinan disebabkan faktor kebijakan atau perubahan metode pencatatan<br>
        • Beberapa kelurahan menunjukkan tren turun 2022–2024 sebelum naik kembali di 2025<br>
        • Proyeksi 2026 menggunakan regresi linear sederhana; akurasi tergantung stabilitas tren
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# HALAMAN — KELOLA DATA (CRUD + Import CSV + Export Excel)
# ════════════════════════════════════════════════════════════
def _reload_after_write():
    st.cache_data.clear()
    st.rerun()


def page_kelola_data():
    page_header("🗄️ Kelola Data R2", "Tambah / Edit / Hapus / Import CSV / Export Excel — langsung ke MySQL")

    df_raw = db.fetch_all()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["➕ Tambah / Edit", "🗑️ Hapus", "📥 Import CSV", "📤 Export Excel", "📍 Centroid Kelurahan"])

    # ── TAMBAH / EDIT ─────────────────────────────────────────
    with tab1:
        st.markdown("#### Tambah atau Perbarui Data")
        st.caption("Jika kombinasi Kecamatan + Kelurahan + Tahun sudah ada, jumlahnya akan ditimpa (update).")
        with st.form("form_tambah_edit"):
            c1, c2 = st.columns(2)
            with c1:
                kec_opt = sorted(set(df_raw["kecamatan"]).union({"(Kecamatan Baru)"}))
                kec_pilih = st.selectbox("Kecamatan:", kec_opt)
                kec_baru  = st.text_input("Nama Kecamatan Baru (jika pilih di atas):") if kec_pilih == "(Kecamatan Baru)" else None
                tahun = st.selectbox("Tahun:", TAHUN_LIST, index=len(TAHUN_LIST) - 1)
            with c2:
                kelurahan = st.text_input("Kelurahan:")
                jumlah    = st.number_input("Jumlah R2:", min_value=0, step=1)
            submitted = st.form_submit_button("💾 Simpan")
            if submitted:
                kec_final = (kec_baru or "").strip() if kec_pilih == "(Kecamatan Baru)" else kec_pilih
                if not kec_final or not kelurahan.strip():
                    st.error("Kecamatan dan Kelurahan wajib diisi.")
                else:
                    db.upsert_row(kec_final, kelurahan, tahun, jumlah)
                    st.success(f"Tersimpan: {kec_final} / {kelurahan.strip().upper()} / {tahun} = {jumlah:,}")
                    _reload_after_write()

        st.markdown("---")
        st.markdown("#### Data Saat Ini")
        st.dataframe(df_raw, use_container_width=True, hide_index=True)

    # ── HAPUS ─────────────────────────────────────────────────
    with tab2:
        st.markdown("#### Hapus Baris Data")
        if df_raw.empty:
            st.info("Belum ada data.")
        else:
            df_raw["label"] = (df_raw["kecamatan"] + " / " + df_raw["kelurahan"]
                                + " / " + df_raw["tahun"].astype(str)
                                + " = " + df_raw["jumlah"].astype(str))
            pilihan = st.multiselect("Pilih baris yang akan dihapus:", df_raw["id"],
                                      format_func=lambda i: df_raw.loc[df_raw["id"] == i, "label"].iloc[0])
            if pilihan and st.button("🗑️ Hapus Baris Terpilih", type="primary"):
                for row_id in pilihan:
                    db.delete_row(row_id)
                st.success(f"{len(pilihan)} baris dihapus.")
                _reload_after_write()

    # ── IMPORT CSV ────────────────────────────────────────────
    with tab3:
        st.markdown("#### Import dari CSV")
        st.caption(
            "Mode **Data Ringkasan**: kolom `kecamatan, kelurahan, tahun, jumlah`.\n\n"
            "Mode **Data Mentah/Transaksi** (mis. file pajak per kendaraan dengan kolom `KR`, `Kecamatan`, "
            "`Kelurahan`): pilih tahun, sistem akan memfilter `KR == 'R2'` lalu menghitung jumlah per kelurahan otomatis.")
        file = st.file_uploader("Pilih file CSV:", type=["csv"])
        if file is not None:
            try:
                df_csv = pd.read_csv(file)
            except Exception as e:
                st.error(f"Gagal membaca CSV: {e}")
                df_csv = None

            if df_csv is not None:
                cols_lower = {c.lower().strip(): c for c in df_csv.columns}

                if {"kecamatan", "kelurahan", "tahun", "jumlah"}.issubset(cols_lower):
                    st.success("Terdeteksi format Data Ringkasan.")
                    df_prep = df_csv.rename(columns={
                        cols_lower["kecamatan"]: "kecamatan",
                        cols_lower["kelurahan"]: "kelurahan",
                        cols_lower["tahun"]: "tahun",
                        cols_lower["jumlah"]: "jumlah",
                    })[["kecamatan", "kelurahan", "tahun", "jumlah"]]
                    st.dataframe(df_prep.head(20), use_container_width=True, hide_index=True)
                    st.caption(f"Total {len(df_prep)} baris siap di-import.")
                    if st.button("✅ Import ke Database", key="import_ringkasan"):
                        n = db.bulk_upsert(df_prep)
                        st.success(f"{n} baris berhasil di-import.")
                        _reload_after_write()

                elif "kr" in cols_lower and "kecamatan" in cols_lower and "kelurahan" in cols_lower:
                    st.success("Terdeteksi format Data Mentah/Transaksi.")
                    tahun_import = st.selectbox("Data ini untuk tahun:", TAHUN_LIST, key="tahun_import_mentah")
                    df_filt = df_csv[df_csv[cols_lower["kr"]].astype(str).str.strip().str.upper() == "R2"]
                    df_agg = (df_filt.groupby([cols_lower["kecamatan"], cols_lower["kelurahan"]])
                              .size().reset_index(name="jumlah"))
                    df_agg.columns = ["kecamatan", "kelurahan", "jumlah"]
                    df_agg["tahun"] = tahun_import
                    df_agg["kecamatan"] = df_agg["kecamatan"].str.strip().str.upper()
                    df_agg["kelurahan"] = df_agg["kelurahan"].str.strip().str.upper()
                    st.markdown(f"**Hasil agregasi** ({len(df_filt):,} baris R2 dari {len(df_csv):,} total baris):")
                    st.dataframe(df_agg, use_container_width=True, hide_index=True)
                    if st.button("✅ Import Hasil Agregasi ke Database", key="import_mentah"):
                        n = db.bulk_upsert(df_agg[["kecamatan", "kelurahan", "tahun", "jumlah"]])
                        st.success(f"{n} baris berhasil di-import untuk tahun {tahun_import}.")
                        _reload_after_write()
                else:
                    st.error(
                        "Format kolom tidak dikenali. Pastikan CSV punya kolom "
                        "`kecamatan, kelurahan, tahun, jumlah` (data ringkasan) atau "
                        "`KR, Kecamatan, Kelurahan` (data mentah transaksi).")

    # ── EXPORT EXCEL ──────────────────────────────────────────
    with tab4:
        st.markdown("#### Export ke Excel")
        kec_filter = st.multiselect("Filter Kecamatan (kosongkan = semua):", KECAMATAN)
        tahun_filter = st.multiselect("Filter Tahun (kosongkan = semua):", TAHUN_LIST)

        df_export = df_raw.copy()
        if kec_filter:
            df_export = df_export[df_export["kecamatan"].isin(kec_filter)]
        if tahun_filter:
            df_export = df_export[df_export["tahun"].isin(tahun_filter)]

        st.dataframe(df_export, use_container_width=True, hide_index=True)

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False, sheet_name="r2_data")
        st.download_button(
            "⬇️ Unduh Excel (.xlsx)", buf.getvalue(),
            "r2_data_export.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── CENTROID KELURAHAN ────────────────────────────────────
    with tab5:
        st.markdown("#### Kelola Titik Centroid Kelurahan (untuk label di Peta Interaktif)")
        st.caption(
            "Centroid dihitung otomatis dari shapefile lewat `scripts/import_centroid.py`. "
            "Gunakan form ini kalau ada kelurahan yang titiknya perlu digeser manual atau "
            "kelurahan baru yang belum ada di shapefile.")

        df_geo = db.fetch_all_centroid()

        with st.form("form_centroid"):
            c1, c2 = st.columns(2)
            with c1:
                kec_opt_geo = sorted(set(df_geo["kecamatan"]).union(set(KECAMATAN)).union({"(Kecamatan Baru)"}))
                kec_pilih_geo = st.selectbox("Kecamatan:", kec_opt_geo, key="geo_kec")
                kec_baru_geo  = st.text_input("Nama Kecamatan Baru:", key="geo_kec_baru") if kec_pilih_geo == "(Kecamatan Baru)" else None
                kelurahan_geo = st.text_input("Kelurahan:", key="geo_kel")
            with c2:
                lat = st.number_input("Latitude:", value=-6.595, format="%.6f", step=0.0001)
                lon = st.number_input("Longitude:", value=106.800, format="%.6f", step=0.0001)
            submitted_geo = st.form_submit_button("💾 Simpan Centroid")
            if submitted_geo:
                kec_final_geo = (kec_baru_geo or "").strip() if kec_pilih_geo == "(Kecamatan Baru)" else kec_pilih_geo
                if not kec_final_geo or not kelurahan_geo.strip():
                    st.error("Kecamatan dan Kelurahan wajib diisi.")
                else:
                    db.upsert_centroid(kec_final_geo, kelurahan_geo, lat, lon)
                    st.success(f"Centroid tersimpan: {kec_final_geo} / {kelurahan_geo.strip().upper()} = ({lat}, {lon})")
                    _reload_after_write()

        st.markdown("---")
        st.markdown("#### Data Centroid Saat Ini")
        st.dataframe(df_geo, use_container_width=True, hide_index=True)

        if not df_geo.empty:
            df_geo["label"] = (df_geo["kecamatan"] + " / " + df_geo["kelurahan"]
                                + " (" + df_geo["lat"].astype(str) + ", " + df_geo["lon"].astype(str) + ")")
            pilihan_geo = st.multiselect("Pilih centroid yang akan dihapus:", df_geo["id"],
                                          format_func=lambda i: df_geo.loc[df_geo["id"] == i, "label"].iloc[0],
                                          key="hapus_centroid")
            if pilihan_geo and st.button("🗑️ Hapus Centroid Terpilih", type="primary", key="btn_hapus_centroid"):
                for row_id in pilihan_geo:
                    db.delete_centroid(row_id)
                st.success(f"{len(pilihan_geo)} centroid dihapus.")
                _reload_after_write()


# ════════════════════════════════════════════════════════════
# HALAMAN 7 – METODOLOGI
# ════════════════════════════════════════════════════════════
def page_metodologi():
    page_header("📋 Metodologi Penelitian")

    st.markdown("""
    <div class="card">
    <h4>🔄 Alur Kerja</h4>
    <ol>
      <li><b>Pengumpulan Data</b> – File Excel pajak kendaraan R2 per tahun (2022–2025)</li>
      <li><b>Preprocessing</b> – Filter KR=R2, normalisasi nama kecamatan & kelurahan</li>
      <li><b>Agregasi</b> – Penghitungan jumlah R2 per kelurahan & kecamatan per tahun</li>
      <li><b>Analisis Deskriptif</b> – Distribusi, kontribusi, delta per periode</li>
      <li><b>Analisis Temporal</b> – Tren, pertumbuhan, CAGR, anomali</li>
      <li><b>Analisis Spasial</b> – Choropleth map via Folium/GEE</li>
      <li><b>Proyeksi</b> – Regresi linear per kecamatan & kelurahan</li>
      <li><b>Klasifikasi</b> – TINGGI/SEDANG/RENDAH vs rata-rata kota</li>
      <li><b>Analisis Konsentrasi</b> – HHI (Herfindahl-Hirschman Index)</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)

    tab1,tab2,tab3 = st.tabs(["📐 Statistik","🗺️ Spasial","🧮 Formula"])

    with tab1:
        st.markdown("""
        **Statistik Deskriptif** — total, rata-rata, distribusi, kontribusi per wilayah

        **Analisis Pertumbuhan** — delta absolut per periode, pertumbuhan kumulatif, CAGR

        **Klasifikasi Relatif** — bandingkan tumbuh tiap kecamatan vs rata-rata kota (±2%)

        **Analisis Anomali** — deteksi kelurahan dengan delta negatif di minimal 1 periode

        **Indeks Konsentrasi (HHI)** — ukur seberapa merata distribusi R2 antar kelurahan
        dalam satu kecamatan (HHI > 2500 = terkonsentrasi)

        **Korelasi** — hubungan jumlah kelurahan vs total R2 kecamatan
        """)

    with tab2:
        st.markdown("""
        **Data Spasial** — Shapefile kecamatan Kota Bogor (6 polygon)

        **Choropleth Mapping** — warna gradasi merah berdasarkan jumlah R2

        **GeoJSON Enrichment** — data R2 ditanamkan langsung ke properties GeoJSON

        **Centroid Labeling** — label nama + nilai di titik tengah polygon

        **Popup Interaktif** — klik polygon untuk detail lengkap per kecamatan
        """)

    with tab3:
        st.code("""
# Pertumbuhan kumulatif (%)
tumbuh = (R2_2025 - R2_2022) / R2_2022 * 100

# CAGR 3 tahun
CAGR = (R2_2025 / R2_2022) ** (1/3) - 1

# Regresi Linear – Proyeksi 2026
slope     = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
intercept = (Σy - slope*Σx) / n
proj_2026 = slope * 4 + intercept

# Klasifikasi kecamatan
TINGGI = tumbuh_kec - tumbuh_kota > +2%
SEDANG = |tumbuh_kec - tumbuh_kota| <= 2%
RENDAH = tumbuh_kec - tumbuh_kota < -2%

# HHI (Herfindahl-Hirschman Index) per kecamatan
HHI = Σ (share_kelurahan_i * 100)²
# HHI > 2500 → terkonsentrasi
# HHI < 1500 → terdistribusi merata
        """, language="python")


# ════════════════════════════════════════════════════════════
# HALAMAN 8 – TENTANG
# ════════════════════════════════════════════════════════════
def page_tentang():
    page_header("ℹ️ Tentang Aplikasi")
    col1, col2 = st.columns([2,1])

    with col1:
        st.markdown("""
        <div class="card">
        <h4>👨‍🎓 Peneliti</h4>
        <p><b>Nama:</b> AHMAD RAFI PRATAMA</p>
        <p><b>Program Studi:</b> TEKNIK INFORMATIKA – LAB GIT</p>
        <p><b>Kampus:</b> UNIVERSITAS IBN KHALDUN</p>
        <p><b>Tahun:</b> 2025</p>
        </div>

        <div class="card">
        <h4>🔬 Tentang Penelitian</h4>
        <p style="text-align:justify;">
        Aplikasi ini menganalisis distribusi spasial kendaraan roda dua (R2) di Kota Bogor
        pada tingkat kecamatan (6 kecamatan) dan kelurahan (68 kelurahan) berdasarkan
        data riil pajak kendaraan bermotor 2022–2025.
        </p>
        </div>

        <div class="card">
        <h4>🛠️ Teknologi</h4>
        <ul>
          <li><b>Python + Streamlit</b> – Dashboard web</li>
          <li><b>Pandas + NumPy</b> – Pengolahan data</li>
          <li><b>Plotly</b> – Visualisasi interaktif</li>
          <li><b>Folium</b> – Peta interaktif</li>
          <li><b>GeoPandas</b> – Pengolahan data spasial (opsional)</li>
          <li><b>Google Earth Engine</b> – Analisis spasial</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
        <h4>📊 Cakupan Data</h4>
        <ul>
          <li>6 Kecamatan</li>
          <li>68 Kelurahan</li>
          <li>4 Tahun (2022–2025)</li>
          <li>~800.000 record pajak</li>
        </ul>
        </div>
        <div class="card">
        <h4>📞 Kontak</h4>
        <p>📧 ahmadrafipratamaabdulhannan@gmail.com</p>
        <p>📱 081222124906</p>
        </div>
        <div class="card">
        <h4>🤯 Suka Duka</h4>
        <p>"dikerjakan secara kepala panas"</p>
        <p>"dibantu king asep"</p>
        <p>"dikepalai oleh king ridwan"</p>
        <p>"di cintai oleh wawa😱"</p>
        </div>
        <div class="card">
        <h4>📝 Lisensi</h4>
        <p>Penelitian akademik.</p>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()

st.markdown(
    "<hr><div style='text-align:center;color:#999;font-size:12px;'>"
    "© 2025 – Analisis Kendaraan R2 Kota Bogor | Ahmad Rafi Pratama – Universitas Ibn Khaldun"
    "</div>", unsafe_allow_html=True)