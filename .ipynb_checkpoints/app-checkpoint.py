"""
R2 Analytics – Kota Bogor
Analisis Spasial Kendaraan Roda Dua (R2) Kota Bogor 2022-2025
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from folium.plugins import Fullscreen
import os

# ── opsional: geopandas & rasterio hanya dipakai kalau file tersedia ──
try:
    import geopandas as gpd
    HAS_GPD = True
except ImportError:
    HAS_GPD = False

try:
    import rasterio
    from rasterio.mask import mask as rio_mask
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    from PIL import Image
    import base64
    from io import BytesIO
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

# ════════════════════════════════════════════════
# KONFIGURASI HALAMAN
# ════════════════════════════════════════════════
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
    margin-bottom: 20px; color: #fff;
    text-align: center;
}
.card {
    background-color: #f8f9fa;
    padding: 18px; border-radius: 10px;
    margin: 10px 0;
    border: 1px solid #e0e0e0;
    color: #333;
}
.stat-box {
    background-color: #fff3f3;
    border-left: 4px solid #e53935;
    padding: 10px 14px; border-radius: 4px;
    margin: 5px 0; color: #333;
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════
# DATA HARDCODED (sama persis dengan kode GEE)
# ════════════════════════════════════════════════
DATA_R2 = {
    "BOGOR BARAT":   {"r2022": 46874, "r2023": 46645, "r2024": 46651, "r2025": 52593},
    "TANAH SAREAL":  {"r2022": 43983, "r2023": 43819, "r2024": 44029, "r2025": 50241},
    "BOGOR UTARA":   {"r2022": 38223, "r2023": 38047, "r2024": 38479, "r2025": 43972},
    "BOGOR SELATAN": {"r2022": 33695, "r2023": 33597, "r2024": 34014, "r2025": 39867},
    "BOGOR TIMUR":   {"r2022": 19849, "r2023": 19519, "r2024": 19515, "r2025": 22148},
    "BOGOR TENGAH":  {"r2022": 20121, "r2023": 19705, "r2024": 19401, "r2025": 21510},
}

TOTAL_KOTA = {2022: 202745, 2023: 201332, 2024: 202089, 2025: 230331}
KECAMATAN  = list(DATA_R2.keys())

CENTROID = {
    "BOGOR BARAT":   (-6.5771, 106.7459),
    "TANAH SAREAL":  (-6.5664, 106.7798),
    "BOGOR UTARA":   (-6.5495, 106.8017),
    "BOGOR SELATAN": (-6.6404, 106.8003),
    "BOGOR TENGAH":  (-6.5982, 106.7910),
    "BOGOR TIMUR":   (-6.6022, 106.8278),
}

COLORS = ["#bd0026", "#e31a1c", "#fc4e2a", "#fd8d3c", "#feb24c", "#fed976"]
SHP_PATH = "data/Kecamatan_KotaBogor.shp"


# ════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════
def get_val(nama: str, year: int) -> int:
    return DATA_R2[nama][f"r{year}"]


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


def linear_proj(values: list) -> int:
    n   = len(values)
    xs  = list(range(n))
    sx  = sum(xs)
    sy  = sum(values)
    sxy = sum(xs[i] * values[i] for i in range(n))
    sx2 = sum(x ** 2 for x in xs)
    denom = n * sx2 - sx ** 2
    if denom == 0:
        return values[-1]
    slope     = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return int(round(intercept + slope * n))


def calc_cagr(start: int, end: int, years: int = 3) -> float:
    if start == 0:
        return 0.0
    return ((end / start) ** (1 / years) - 1) * 100


def build_df() -> pd.DataFrame:
    avg_kota = (TOTAL_KOTA[2025] - TOTAL_KOTA[2022]) / TOTAL_KOTA[2022] * 100
    rows = []
    for nama, d in DATA_R2.items():
        arr      = [d["r2022"], d["r2023"], d["r2024"], d["r2025"]]
        t2225    = (d["r2025"] - d["r2022"]) / d["r2022"] * 100
        proj2026 = linear_proj(arr)
        selisih  = t2225 - avg_kota
        kelas    = "TINGGI" if selisih > 2 else ("RENDAH" if selisih < -2 else "SEDANG")
        rows.append({
            "Kecamatan":       nama,
            "2022":            d["r2022"],
            "2023":            d["r2023"],
            "2024":            d["r2024"],
            "2025":            d["r2025"],
            "Delta 22-23":     d["r2023"] - d["r2022"],
            "Delta 23-24":     d["r2024"] - d["r2023"],
            "Delta 24-25":     d["r2025"] - d["r2024"],
            "Tumbuh (%)":      round(t2225, 2),
            "CAGR (%)":        round(calc_cagr(d["r2022"], d["r2025"]), 2),
            "Proyeksi 2026":   proj2026,
            "Delta Proj":      proj2026 - d["r2025"],
            "Klasifikasi":     kelas,
            "Kontribusi (%)":  round(d["r2025"] / TOTAL_KOTA[2025] * 100, 2),
        })
    return pd.DataFrame(rows)


def page_header(title: str, subtitle: str = "") -> None:
    sub = f"<p style='margin:4px 0 0;'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="main-header"><h2 style="margin:0;">{title}</h2>{sub}</div>',
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════
# NAVIGASI
# ════════════════════════════════════════════════
def main():
    st.sidebar.markdown(
        '<div style="background:#b71c1c;color:#fff;padding:12px;border-radius:6px;'
        'text-align:center;margin-bottom:14px;"><b>🏍️ R2 Analytics – Kota Bogor</b></div>',
        unsafe_allow_html=True,
    )
    menu = st.sidebar.radio(
        "Pilih Halaman:",
        [
            "🏠 Beranda",
            "🗺️ Peta Interaktif",
            "📊 Analisis Data",
            "📈 Proyeksi 2026",
            "📋 Metodologi",
            "ℹ️ Tentang",
        ],
    )

    if   menu == "🏠 Beranda":          page_beranda()
    elif menu == "🗺️ Peta Interaktif":  page_peta()
    elif menu == "📊 Analisis Data":     page_analisis()
    elif menu == "📈 Proyeksi 2026":     page_proyeksi()
    elif menu == "📋 Metodologi":        page_metodologi()
    elif menu == "ℹ️ Tentang":           page_tentang()


# ════════════════════════════════════════════════
# HALAMAN 1 – BERANDA
# ════════════════════════════════════════════════
def page_beranda():
    page_header(
        "🏍️ R2 Analytics – Kota Bogor",
        "Analisis Spasial Kendaraan Roda Dua (R2) Kota Bogor 2022–2025",
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        <div class="card">
        <h4>🎯 Tujuan Penelitian</h4>
        <p style="text-align:justify;">
        Penelitian ini menganalisis distribusi spasial dan tren temporal kendaraan roda dua (R2)
        di Kota Bogor berdasarkan data pajak kendaraan bermotor tahun 2022–2025 menggunakan
        pendekatan GIS dan statistik deskriptif untuk mendukung perencanaan transportasi
        dan kebijakan pajak daerah.
        </p>
        </div>
        """, unsafe_allow_html=True)

        df_sum = pd.DataFrame({
            "No":              range(1, len(KECAMATAN) + 1),
            "Kecamatan":       KECAMATAN,
            "R2 (2025)":       [get_val(k, 2025) for k in KECAMATAN],
            "Pertumbuhan (%)": [
                round((get_val(k, 2025) - get_val(k, 2022)) / get_val(k, 2022) * 100, 2)
                for k in KECAMATAN
            ],
        })
        st.markdown('<div class="card"><h4>📋 Ringkasan per Kecamatan (2025)</h4>', unsafe_allow_html=True)
        st.dataframe(df_sum, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
        <h4>📍 Lokasi Penelitian</h4>
        <ul>
          <li><b>Kota:</b> Bogor</li>
          <li><b>Provinsi:</b> Jawa Barat</li>
          <li><b>Kecamatan:</b> 6</li>
          <li><b>Periode:</b> 2022–2025</li>
          <li><b>Sumber:</b> Pajak Kendaraan Bermotor</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div class='card'><h4>📈 Total R2 Kota Bogor</h4>", unsafe_allow_html=True)
        prev_total = None
        for year, total in TOTAL_KOTA.items():
            delta_str = ""
            if prev_total is not None:
                pct = (total - prev_total) / prev_total * 100
                delta_str = f"<span style='color:#888;font-size:12px;'>({pct:+.2f}%)</span>"
            st.markdown(
                f'<div class="stat-box"><b>{year}</b> — {total:,} unit {delta_str}</div>',
                unsafe_allow_html=True,
            )
            prev_total = total
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### 📊 Distribusi R2 per Kecamatan (2025)")
    fig = px.pie(
        names=KECAMATAN,
        values=[get_val(k, 2025) for k in KECAMATAN],
        color_discrete_sequence=COLORS,
        title="Distribusi Kendaraan R2 per Kecamatan (2025)",
    )
    st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════
# HALAMAN 2 – PETA INTERAKTIF
# ════════════════════════════════════════════════
def page_peta():
    page_header("🗺️ Peta Interaktif Kendaraan R2 Kota Bogor")

    st.sidebar.markdown("### 🎛️ Kontrol Peta")
    year     = st.sidebar.selectbox("Pilih Tahun:", [2022, 2023, 2024, 2025], index=3)
    opacity  = st.sidebar.slider("Transparansi", 0.1, 1.0, 0.75, 0.05)
    show_lbl = st.sidebar.checkbox("Tampilkan Label", value=True)

    # Legenda sidebar
    st.sidebar.markdown("### 🎨 Legenda")
    legend_items = (
        [("≥ 50.000", "#bd0026"), ("40.000–49.999", "#e31a1c"),
         ("35.000–39.999", "#fc4e2a"), ("25.000–34.999", "#fd8d3c"),
         ("20.000–24.999", "#feb24c"), ("< 20.000", "#fed976")]
        if year == 2025 else
        [("≥ 40.000", "#bd0026"), ("35.000–39.999", "#e31a1c"),
         ("30.000–34.999", "#fc4e2a"), ("25.000–29.999", "#fd8d3c"),
         ("20.000–24.999", "#feb24c"), ("< 20.000", "#fed976")]
    )
    for lbl, col in legend_items:
        st.sidebar.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;">'
            f'<span style="background:{col};width:16px;height:16px;'
            f'display:inline-block;border-radius:3px;"></span>'
            f'<span style="font-size:13px;">{lbl}</span></div>',
            unsafe_allow_html=True,
        )

    col_map, col_stat = st.columns([3, 1])

    with col_map:
        m = folium.Map(location=[-6.595, 106.816], zoom_start=13)
        Fullscreen().add_to(m)

        total_tahun = TOTAL_KOTA[year]

        # Load shapefile jika tersedia
        if HAS_GPD and os.path.exists(SHP_PATH):
            try:
                gdf = gpd.read_file(SHP_PATH)
                if gdf.crs and gdf.crs.to_epsg() != 4326:
                    gdf = gdf.to_crs(epsg=4326)

                # Cari kolom nama
                name_col = None
                for candidate in ("NAMOBJ", "NAMA", "KECAMATAN", "NAME"):
                    if candidate in gdf.columns:
                        name_col = candidate
                        break

                def style_fn(feature):
                    raw  = feature["properties"].get(name_col, "") if name_col else ""
                    nama = str(raw).upper().strip()
                    val  = DATA_R2.get(nama, {}).get(f"r{year}", 0)
                    return {
                        "fillColor":   choropleth_color(val, year),
                        "color":       "black",
                        "weight":      1.5,
                        "fillOpacity": opacity,
                    }

                tooltip_fields   = [name_col] if name_col else list(gdf.columns[:1])
                tooltip_aliases  = ["Kecamatan:"]

                folium.GeoJson(
                    gdf,
                    name="Choropleth Kecamatan",
                    style_function=style_fn,
                    tooltip=folium.GeoJsonTooltip(
                        fields=tooltip_fields,
                        aliases=tooltip_aliases,
                    ),
                ).add_to(m)

            except Exception as e:
                st.warning(f"Shapefile tidak dapat dimuat ({e}). Menampilkan circle marker.")

        # Circle marker – selalu ditampilkan
        for nama, coords in CENTROID.items():
            val     = get_val(nama, year)
            pct     = val / total_tahun * 100
            col_hex = choropleth_color(val, year)
            d       = DATA_R2[nama]

            popup_html = (
                f"<div style='font-family:monospace;font-size:12px;min-width:210px;'>"
                f"<b style='color:#b71c1c;font-size:14px;'>{nama}</b><br>"
                f"<hr style='margin:4px 0;'>"
                f"<b>Tahun:</b> {year}<br>"
                f"<b>Jumlah R2:</b> {val:,} unit<br>"
                f"<b>Kontribusi:</b> {pct:.2f}%<br>"
                f"<hr style='margin:4px 0;'>"
                f"<b>2022:</b> {d['r2022']:,}<br>"
                f"<b>2023:</b> {d['r2023']:,}<br>"
                f"<b>2024:</b> {d['r2024']:,}<br>"
                f"<b>2025:</b> {d['r2025']:,}<br>"
                f"<hr style='margin:4px 0;'>"
                f"<b>Pertumbuhan 2022–2025:</b> "
                f"{(d['r2025'] - d['r2022']) / d['r2022'] * 100:.2f}%"
                f"</div>"
            )

            folium.CircleMarker(
                location=coords,
                radius=max(14, val // 2800),
                color="black",
                weight=1.5,
                fill=True,
                fill_color=col_hex,
                fill_opacity=opacity,
                popup=folium.Popup(popup_html, max_width=260),
                tooltip=f"{nama}: {val:,} unit",
            ).add_to(m)

            if show_lbl:
                folium.Marker(
                    location=coords,
                    icon=folium.DivIcon(
                        html=(
                            f'<div style="font-size:9px;font-weight:bold;color:#fff;'
                            f'text-shadow:1px 1px 2px #000;text-align:center;'
                            f'line-height:1.3;pointer-events:none;">'
                            f'{nama.replace(" ", "<br>")}<br>{val:,}</div>'
                        ),
                        icon_size=(90, 40),
                        icon_anchor=(45, 20),
                    ),
                ).add_to(m)

        folium.LayerControl().add_to(m)
        map_data = st_folium(m, width="100%", height=580)

        if map_data and map_data.get("last_clicked"):
            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]
            st.info(f"📍 Koordinat diklik: {lat:.5f}°, {lon:.5f}°")

    with col_stat:
        st.markdown(f"### 📊 Ranking {year}")
        sorted_kec = sorted(KECAMATAN, key=lambda k: get_val(k, year), reverse=True)
        for rank, nama in enumerate(sorted_kec, 1):
            val     = get_val(nama, year)
            pct     = val / total_tahun * 100
            col_hex = choropleth_color(val, year)
            st.markdown(
                f'<div class="stat-box">'
                f'<span style="color:{col_hex};font-weight:bold;">#{rank} {nama}</span><br>'
                f'{val:,} unit ({pct:.1f}%)</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div class="card" style="margin-top:10px;">'
            f'<b>Total {year}:</b><br>'
            f'<span style="font-size:20px;font-weight:bold;color:#b71c1c;">'
            f'{total_tahun:,}</span> unit</div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════
# HALAMAN 3 – ANALISIS DATA
# ════════════════════════════════════════════════
def page_analisis():
    page_header("📊 Analisis Data Kendaraan R2 Kota Bogor")

    df       = build_df()
    avg_kota = (TOTAL_KOTA[2025] - TOTAL_KOTA[2022]) / TOTAL_KOTA[2022] * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total R2 (2025)",        f"{TOTAL_KOTA[2025]:,}")
    c2.metric("Pertumbuhan 2022–2025",  f"+{avg_kota:.2f}%")
    c3.metric("Kecamatan Tertinggi",    "Bogor Barat")
    c4.metric("Pertumbuhan Tertinggi",  "Bogor Selatan +18.32%")

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📈 Tren Temporal", "📊 Perbandingan", "🔼 Pertumbuhan & CAGR", "📋 Tabel Lengkap"]
    )

    with tab1:
        fig_line = go.Figure()
        for i, nama in enumerate(KECAMATAN):
            d = DATA_R2[nama]
            fig_line.add_trace(go.Scatter(
                x=[2022, 2023, 2024, 2025],
                y=[d["r2022"], d["r2023"], d["r2024"], d["r2025"]],
                mode="lines+markers",
                name=nama,
                line=dict(color=COLORS[i], width=2),
                marker=dict(size=7),
            ))
        fig_line.update_layout(
            title="Tren R2 per Kecamatan (2022–2025)",
            xaxis_title="Tahun",
            yaxis_title="Jumlah R2",
            xaxis=dict(tickvals=[2022, 2023, 2024, 2025]),
            legend=dict(orientation="h", y=-0.25),
        )
        st.plotly_chart(fig_line, use_container_width=True)

        years_list = [2022, 2023, 2024, 2025]
        totals     = [TOTAL_KOTA[y] for y in years_list]
        fig_tot = go.Figure(go.Bar(
            x=years_list,
            y=totals,
            marker_color="#e31a1c",
            text=[f"{t:,}" for t in totals],
            textposition="outside",
        ))
        fig_tot.update_layout(
            title="Total R2 Kota Bogor (2022–2025)",
            xaxis_title="Tahun",
            yaxis_title="Total R2",
            xaxis=dict(tickvals=years_list),
        )
        st.plotly_chart(fig_tot, use_container_width=True)

    with tab2:
        year_sel = st.selectbox("Pilih Tahun:", [2022, 2023, 2024, 2025], index=3, key="tab2_year")
        vals     = [get_val(k, year_sel) for k in KECAMATAN]
        pairs    = sorted(zip(vals, KECAMATAN), reverse=True)
        v_s, n_s = zip(*pairs)

        fig_bar = go.Figure(go.Bar(
            x=list(n_s),
            y=list(v_s),
            marker_color=COLORS,
            text=[f"{v:,}" for v in v_s],
            textposition="outside",
        ))
        fig_bar.update_layout(
            title=f"Jumlah R2 per Kecamatan ({year_sel})",
            xaxis_title="Kecamatan",
            yaxis_title="Jumlah R2",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        fig_pie = px.pie(
            names=list(n_s),
            values=list(v_s),
            color_discrete_sequence=COLORS,
            title=f"Distribusi R2 per Kecamatan ({year_sel})",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with tab3:
        tumbuh = [
            round((get_val(k, 2025) - get_val(k, 2022)) / get_val(k, 2022) * 100, 2)
            for k in KECAMATAN
        ]
        bar_colors = ["#1a9641" if t > avg_kota else "#e31a1c" for t in tumbuh]

        fig_grow = go.Figure(go.Bar(
            x=KECAMATAN,
            y=tumbuh,
            marker_color=bar_colors,
            text=[f"{t}%" for t in tumbuh],
            textposition="outside",
        ))
        fig_grow.add_hline(
            y=avg_kota,
            line_dash="dash",
            line_color="black",
            annotation_text=f"Rata-rata kota: {avg_kota:.2f}%",
        )
        fig_grow.update_layout(
            title="Pertumbuhan R2 per Kecamatan 2022–2025 (%)",
            xaxis_title="Kecamatan",
            yaxis_title="Pertumbuhan (%)",
        )
        st.plotly_chart(fig_grow, use_container_width=True)

        cagr_vals = [
            round(calc_cagr(get_val(k, 2022), get_val(k, 2025)), 2)
            for k in KECAMATAN
        ]
        fig_cagr = go.Figure(go.Bar(
            y=KECAMATAN,
            x=cagr_vals,
            orientation="h",
            marker_color="#fd8d3c",
            text=[f"{c}%" for c in cagr_vals],
            textposition="outside",
        ))
        fig_cagr.update_layout(
            title="CAGR (Compound Annual Growth Rate) 2022–2025",
            xaxis_title="CAGR (%)",
            yaxis_title="Kecamatan",
        )
        st.plotly_chart(fig_cagr, use_container_width=True)

    with tab4:
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Unduh CSV",
            data=csv,
            file_name="analisis_r2_kota_bogor.csv",
            mime="text/csv",
        )


# ════════════════════════════════════════════════
# HALAMAN 4 – PROYEKSI 2026
# ════════════════════════════════════════════════
def page_proyeksi():
    page_header("📈 Proyeksi Kendaraan R2 Kota Bogor 2026", "Metode: Regresi Linear")

    df         = build_df()
    total_2026 = int(df["Proyeksi 2026"].sum())
    delta_proj = total_2026 - TOTAL_KOTA[2025]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total R2 Aktual (2025)", f"{TOTAL_KOTA[2025]:,}")
    c2.metric("Proyeksi 2026",          f"{total_2026:,}", f"+{delta_proj:,}")
    c3.metric("Kenaikan Proyeksi",      f"+{delta_proj / TOTAL_KOTA[2025] * 100:.2f}%")

    st.markdown("---")

    fig_proj = go.Figure()
    for i, (_, row) in enumerate(df.iterrows()):
        fig_proj.add_trace(go.Bar(
            name=row["Kecamatan"],
            x=["Aktual 2025", "Proyeksi 2026"],
            y=[int(row["2025"]), int(row["Proyeksi 2026"])],
            marker_color=COLORS[i % len(COLORS)],
        ))
    fig_proj.update_layout(
        barmode="group",
        title="Aktual 2025 vs Proyeksi 2026 per Kecamatan",
        xaxis_title="Periode",
        yaxis_title="Jumlah R2",
    )
    st.plotly_chart(fig_proj, use_container_width=True)

    st.markdown("### 📋 Tabel Detail Proyeksi & Klasifikasi")

    cols_show = [
        "Kecamatan", "2025", "Proyeksi 2026", "Delta Proj",
        "Tumbuh (%)", "CAGR (%)", "Klasifikasi", "Kontribusi (%)",
    ]

    def color_klas(val):
        if val == "TINGGI": return "background-color:#d4edda;color:#155724"
        if val == "RENDAH": return "background-color:#f8d7da;color:#721c24"
        return "background-color:#fff3cd;color:#856404"

    styled = df[cols_show].style.applymap(color_klas, subset=["Klasifikasi"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.markdown("""
    <div class="card">
    <b>⚠️ Catatan Metode</b><br>
    Proyeksi menggunakan regresi linear dari 4 titik data (2022–2025).
    Hasilnya bersifat indikatif – kondisi kebijakan transportasi dan ekonomi
    dapat mempengaruhi realisasi aktual.
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════
# HALAMAN 5 – METODOLOGI
# ════════════════════════════════════════════════
def page_metodologi():
    page_header("📋 Metodologi Penelitian")

    st.markdown("""
    <div class="card">
    <h4>🔄 Alur Kerja</h4>
    <ol>
      <li><b>Pengumpulan Data</b> – Data pajak kendaraan R2 per kecamatan 2022–2025</li>
      <li><b>Preprocessing</b> – Validasi dan normalisasi data tabular</li>
      <li><b>Analisis Deskriptif</b> – Distribusi, kontribusi, delta per tahun</li>
      <li><b>Analisis Temporal</b> – Tren pertumbuhan, CAGR 3 tahun</li>
      <li><b>Analisis Spasial</b> – Choropleth map via GEE + Folium</li>
      <li><b>Proyeksi</b> – Regresi linear untuk estimasi 2026</li>
      <li><b>Klasifikasi</b> – Tinggi / Sedang / Rendah vs rata-rata kota</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(
        ["📐 Analisis Statistik", "🗺️ Analisis Spasial", "🧮 Formula"]
    )

    with tab1:
        st.markdown("""
        **Analisis Deskriptif**
        - Total, rata-rata, dan distribusi R2 per kecamatan
        - Kontribusi persentase tiap kecamatan terhadap total kota

        **Analisis Pertumbuhan**
        - Delta per periode: selisih absolut antar tahun
        - Pertumbuhan total (%): (R2025 − R2022) / R2022 × 100
        - CAGR: (R2025 / R2022)^(1/3) − 1

        **Klasifikasi Relatif**
        - **TINGGI:** pertumbuhan > rata-rata kota + 2%
        - **SEDANG:** dalam rentang ± 2% dari rata-rata kota
        - **RENDAH:** pertumbuhan < rata-rata kota − 2%
        """)

    with tab2:
        st.markdown("""
        **Spatial Join**
        Join data atribut R2 ke polygon kecamatan berdasarkan kolom NAMOBJ
        menggunakan Google Earth Engine (GEE).

        **Choropleth Mapping**
        Visualisasi distribusi spasial dengan gradasi warna merah berdasarkan
        jumlah R2 per kecamatan.

        **Centroid Labeling**
        Penempatan label teks di titik centroid masing-masing kecamatan.

        **Inspector Tool (GEE)**
        Klik interaktif pada peta untuk menampilkan detail data R2 per kecamatan.

        **Analisis Spasial Potensial (Pengembangan)**
        - Moran's I – Autocorrelation spasial
        - Getis-Ord Gi* – Hotspot analysis
        - KDE – Kernel Density Estimation
        """)

    with tab3:
        st.code("""
# Pertumbuhan (%)
tumbuh = (R2_akhir - R2_awal) / R2_awal * 100

# CAGR (Compound Annual Growth Rate)
CAGR = (R2_2025 / R2_2022) ** (1/3) - 1

# Regresi Linear (Proyeksi 2026)
slope     = (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x**2)
intercept = (sum_y - slope*sum_x) / n
proj_2026 = slope * 4 + intercept   # x=4 → indeks tahun ke-5

# Klasifikasi vs Rata-rata Kota
selisih = tumbuh_kecamatan - tumbuh_kota
TINGGI  = selisih > +2%
SEDANG  = -2% <= selisih <= +2%
RENDAH  = selisih < -2%

# Kontribusi (%)
kontribusi = R2_kecamatan / Total_kota * 100
        """, language="python")


# ════════════════════════════════════════════════
# HALAMAN 6 – TENTANG
# ════════════════════════════════════════════════
def page_tentang():
    page_header("ℹ️ Tentang Aplikasi")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        <div class="card">
        <h4>👨‍🎓 Peneliti</h4>
        <p><b>Nama:</b> [Nama Peneliti]</p>
        <p><b>Program Studi:</b> [Program Studi]</p>
        <p><b>Institusi:</b> [Nama Institusi]</p>
        <p><b>Tahun:</b> 2025</p>
        </div>

        <div class="card">
        <h4>🔬 Tentang Penelitian</h4>
        <p style="text-align:justify;">
        Aplikasi ini merupakan dashboard analisis spasial kendaraan roda dua (R2) di Kota Bogor
        berbasis data pajak kendaraan bermotor tahun 2022–2025. Menggunakan pendekatan GIS dan
        statistik untuk mendukung perencanaan transportasi dan kebijakan fiskal daerah.
        </p>
        </div>

        <div class="card">
        <h4>🛠️ Teknologi</h4>
        <ul>
          <li><b>Python</b> – Bahasa pemrograman utama</li>
          <li><b>Streamlit</b> – Framework web dashboard</li>
          <li><b>Google Earth Engine</b> – Platform analisis spasial</li>
          <li><b>GeoPandas / Rasterio</b> – Pengolahan data spasial (opsional)</li>
          <li><b>Folium</b> – Visualisasi peta interaktif</li>
          <li><b>Plotly</b> – Visualisasi data interaktif</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
        <h4>📊 Sumber Data</h4>
        <ul>
          <li>Data Pajak Kendaraan Bermotor Kota Bogor (2022–2025)</li>
          <li>Shapefile Kecamatan Kota Bogor (GEE Asset)</li>
        </ul>
        </div>

        <div class="card">
        <h4>📞 Kontak</h4>
        <p>📧 Email: [email@domain.com]</p>
        <p>📱 WhatsApp: [Nomor WA]</p>
        </div>

        <div class="card">
        <h4>📝 Lisensi</h4>
        <p>Dibuat untuk keperluan penelitian akademik.</p>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════
if __name__ == "__main__":
    main()

st.markdown(
    "<hr><div style='text-align:center;color:#999;font-size:12px;'>"
    "© 2025 – Analisis Kendaraan R2 Kota Bogor | Penelitian Akademik"
    "</div>",
    unsafe_allow_html=True,
)
