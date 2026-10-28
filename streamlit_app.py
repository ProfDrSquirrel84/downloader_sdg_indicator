import base64
import csv
import io
import random
import re
import shutil
import tempfile
import time
import zipfile
from collections import deque
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import plotly.express as px
import requests
from requests.adapters import HTTPAdapter
import seaborn as sns
import streamlit as st
from urllib3.util.retry import Retry

# ==============================================================================
# SEITENKONFIGURATION & LAG 21 NRW DESIGN (CSS)
# ==============================================================================

st.set_page_config(
    page_title="SDG-Datenportal | LAG 21 NRW",
    page_icon="🌿",
    layout="wide"
)

def apply_lag21_theme():
    """Injiziert Custom CSS im Stil der LAG 21 NRW (www.lag21.de)."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');

        :root {
            --lag-petrol: #004B5A;
            --lag-petrol-light: #00667A;
            --lag-green: #76B82A;
            --lag-green-hover: #629B21;
            --lag-bg: #F4F7F6;
            --lag-card-bg: #FFFFFF;
            --lag-text: #2C3E50;
        }

        .stApp {
            background-color: var(--lag-bg);
            font-family: 'Open Sans', sans-serif;
            color: var(--lag-text);
        }

        h1, h2, h3, h4 {
            color: var(--lag-petrol) !important;
            font-weight: 700 !important;
        }

        .lag21-header {
            background: linear-gradient(135deg, var(--lag-petrol) 0%, var(--lag-petrol-light) 100%);
            color: white;
            padding: 2rem 2.5rem;
            border-radius: 8px;
            border-bottom: 5px solid var(--lag-green);
            margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(0, 75, 90, 0.12);
        }
        .lag21-header-badge {
            background-color: var(--lag-green);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            display: inline-block;
            margin-bottom: 0.75rem;
        }
        .lag21-header h1 {
            color: #FFFFFF !important;
            margin: 0 0 0.5rem 0 !important;
            font-size: 2rem !important;
        }
        .lag21-header p {
            color: #E2ECE9;
            margin: 0;
            font-size: 1.05rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: var(--lag-card-bg);
            border: 1px solid #E0E7E5 !important;
            border-top: 4px solid var(--lag-green) !important;
            border-radius: 8px !important;
            padding: 1.25rem !important;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
        }

        div[data-testid="stExpander"] {
            border: 1px solid #D5E0DD !important;
            border-left: 4px solid var(--lag-petrol) !important;
            border-radius: 6px !important;
            background-color: #FAFDFC !important;
            margin-bottom: 0.6rem !important;
        }
        div[data-testid="stExpander"] summary {
            font-weight: 600 !important;
            color: var(--lag-petrol) !important;
        }
        div[data-testid="stExpander"] summary:hover {
            color: var(--lag-green) !important;
        }

        div.stButton > button[kind="primary"],
        div.stDownloadButton > button[kind="primary"] {
            background-color: var(--lag-green) !important;
            color: white !important;
            border: none !important;
            border-radius: 5px !important;
            padding: 0.6rem 1.5rem !important;
            font-weight: 600 !important;
            transition: all 0.2s ease-in-out !important;
            box-shadow: 0 2px 5px rgba(118, 184, 42, 0.3) !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div.stDownloadButton > button[kind="primary"]:hover {
            background-color: var(--lag-green-hover) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(118, 184, 42, 0.4) !important;
        }

        div.stButton > button[kind="secondary"],
        div.stDownloadButton > button[kind="secondary"] {
            border: 1.5px solid var(--lag-petrol) !important;
            color: var(--lag-petrol) !important;
            background-color: white !important;
            border-radius: 5px !important;
            font-weight: 600 !important;
        }
        div.stButton > button[kind="secondary"]:hover,
        div.stDownloadButton > button[kind="secondary"]:hover {
            background-color: var(--lag-petrol) !important;
            color: white !important;
        }

        span[data-baseweb="tag"] {
            background-color: var(--lag-petrol) !important;
            color: white !important;
            border-radius: 4px !important;
        }

        div[data-testid="stProgressBar"] > div > div > div > div {
            background-color: var(--lag-green) !important;
        }

        hr {
            border-color: #D5E0DD !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

apply_lag21_theme()


# ==============================================================================
# DATENBASIS & FEST DEFINIERTE ZUORDNUNG
# ==============================================================================

BASE_URL = "https://www.wegweiser-kommune.de/data-api/rest/export"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}

DEFAULT_COMMUNES = [
    "westerkappeln", "noervenich", "schermbeck",
    "bad-laasphe", "blomberg", "drensteinfurt", "altena",
    "bad-berleburg", "hoerstel", "lengerich-st",
    "bornheim-su", "wiehl", "overath", "lohmar",
    "monheim-am-rhein",
    "frechen", "kleve", "hattingen", "dormagen",
    "ratingen", "remscheid", "herne", "solingen", "hagen",
    "euskirchen", "bonn", "bielefeld", "wuppertal"
]

INDICATORS_BY_CATEGORY = {
    "7. Haushalt und Finanzen (Steuerungskriterium)": {
        "Steuereinnahmen": "steuereinnahmen-pro-einwohner-in",
        "Finanzmittelsaldo": "finanzmittelsaldo",
        "Liquiditaetskredite": "liquiditaetskredite",
    },
    "8. Digitalisierung, Innovation & Forschung (Steuerungskriterium)": {
        "Breitbandversorgung_Haushalte": "breitbandversorgung-private-haushalte",
    },
    "Handlungsfeld 9: Klimaschutz & Klimaanpassung": {
        "Strom_aus_erneuerbaren_Quellen": "strom-aus-erneuerbaren-quellen",
        "Ladesaeuleninfrastruktur": "ladesaeuleninfrastruktur",
        "Wohngebaeude_erneuerbare_Heizenergie": "fertiggestellte-wohngebaeude-mit-erneuerbarer-energie",
    },
    "Handlungsfeld 10: Kreislaufwirtschaft": {
        "Abfallmenge": "abfallmenge",
    },
    "Handlungsfeld 11: Biodiversitäts- und Umweltschutz": {
        "Landschaftsqualitaet": "landschaftsqualitaet",
        "Naturschutzflaechen": "naturschutzflaechen",
        "Luftschadstoffbelastung": "luftschadstoffbelastung",
        "Siedlungslast_Ueberschwemmungsgebiet": "siedlungslast-im-ueberschwemmungsgebiet",
        "Abwasserbehandlung": "abwasserbehandlung",
    },
    "Handlungsfeld 12: Nachhaltige Flächen- und Raumentwicklung": {
        "Flaechenneuinanspruchnahme": "flaechenneuinanspruchnahme",
        "Flaechennutzungsintensitaet": "flaechennutzungsintensitaet",
        "Flaecheninanspruchnahme": "flaecheninanspruchnahme",
        "Naherholungsflaechen": "naherholungsflaechen",
        "Stickstoffueberschuss-der-Landwirtschaft": "stickstoffueberschuss-der-landwirtschaft",
    },
    "Handlungsfeld 13: Wohnen & nachhaltige Quartiere": {
        "Wohnungslosigkeit": "wohnungslosigkeit",
        "Mietpreise": "mietpreise",
        "Wohnungsnaher_Supermarkt": "wohnungsnahe-grundversorgung-supermarkt",
        "Wohnflaeche": "wohnflaeche-pro-person",
    },
    "Handlungsfeld 14: Nachhaltige Mobilität": {
        "Verunglueckte_im_Verkehr": "verunglueckte-im-verkehr",
        "PKW-Dichte": "pkw-dichte",
        "PKW-mit-Elektroantrieb": "pkw-mit-elektroantrieb",
    },
    "Handlungsfeld 15: Soziale Gerechtigkeit & Gesellschaft": {
        "SGB_II_XII_Quote": "sgb-ii-sgb-xii-quote",
        "Erwerbstaetige_Aufstockende": "aufstocker-gesamt",
        "Kinderarmut": "kinderarmut",
        "Jugendarmut": "jugendarmut",
        "Altersarmut": "altersarmut",
        "Verhaeltnis_Beschaeftigung_Frauen_Maenner": "verhaeltnis-der-beschaeftigungsquote-von-frauen-und-maennern",
        "U3_in_Tageseinrichtungen": "unter-3-jaehrige-in-tageseinrichtungen",
        "Beschaeftigungsquote – Auslaender": "verhaltnis-beschaftigungsquote-von-auslandern-zur-beschaftigungsquote-gesamt",
        "Schulabbrecherquote – Auslaender": "verhaltnis-schulabbrecherquote-von-auslandern-zu-schulabbrecherquote-gesamt",
        "Einbuergerungen": "eingebuergerte-im-jahr",
    },
    "Handlungsfeld 16: Bildung und Kultur": {
        "Wohnungsnahe_Grundschule": "wohnungsnahe-grundversorgung-grundschule",
        "Schulabgaenger_ohne_Hauptschulabschluss": "schulabgaenger-ohne-hauptschulabschluss-gesamt",
    },
    "Handlungsfeld 17: Gesundheit": {
        "Wohnungsnaher_Hausarzt": "wohnungsnahe-grundversorgung-hausarzt",
        "Wohnungsnahe_Apotheke": "wohnungsnahe-grundversorgung-apotheke",
        "Wohnungsnahes_Krankenhaus": "wohnungsnahe-grundversorgung-krankenhaus",
        "Plaetze-in-Pflegeheimen": "plaetze-in-pflegeheimen",
        "Vorzeitige_Sterblichkeit": "vorzeitige-sterblichkeit-gesamt",
    },
    "Handlungsfeld 18: Gute Arbeit & nachhaltiges Wirtschaften": {
        "Existenzgruendungen": "existenzgruendungen",
        "Beschaeftigungsquote": "beschaeftigungsquote",
        "Beschaeftigungsquote_55-64-jaehrige": "beschaeftigungsquote-55-bis-64-jaehrige",
        "Langzeitarbeitslosenquote": "langzeitarbeitslosenquote",
        "Hochqualifizierte_am_Arbeitsort": "hochqualifizierte-am-arbeitsort",
    }
}

ALL_INDICATORS = {
    ind_key: ind_slug
    for cat_dict in INDICATORS_BY_CATEGORY.values()
    for ind_key, ind_slug in cat_dict.items()
}

SLUG_TO_INFO = {}
for cat_name, cat_dict in INDICATORS_BY_CATEGORY.items():
    for ind_name, ind_slug in cat_dict.items():
        SLUG_TO_INFO[ind_slug.lower()] = {
            "handlungsfeld": cat_name,
            "indikator_name": ind_name
        }


# ==============================================================================
# HILFS- & DOWNLOAD-FUNKTIONEN
# ==============================================================================

def slugify_commune(name: str) -> str:
    s = name.strip().lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")


def create_resilient_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    retries = Retry(
        total=5, connect=5, read=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def download_file(
    session: requests.Session,
    commune_slug: str,
    ind_name: str,
    ind_slug: str,
    period: str,
    target_dir: Path
) -> tuple[bool, str, bool]:
    file_name = f"{commune_slug}_{ind_slug}.csv"
    output_path = target_dir / file_name

    if output_path.exists() and output_path.stat().st_size > 0:
        kb = round(output_path.stat().st_size / 1024, 1)
        return True, f"{kb} KB (bereits geladen)", True

    slug = f"{ind_slug}+{commune_slug}+{period}+tabelle"
    url = f"{BASE_URL}/{slug}.csv"
    params = {"charset": "UTF-8"}

    try:
        res = session.get(url, params=params, timeout=30)
        if res.status_code == 200:
            if "text/html" in res.headers.get("Content-Type", ""):
                return False, "Server lieferte HTML (Slug evtl. ungültig)", False
            with open(output_path, "wb") as f:
                f.write(res.content)
            kb = round(len(res.content) / 1024, 1)
            return True, f"{kb} KB", False
        return False, f"HTTP {res.status_code}", False
    except Exception as e:
        return False, str(e), False


# ==============================================================================
# DATENAUFBEREITUNG & PARSING
# ==============================================================================

def fix_mojibake(text: str) -> str:
    if not text:
        return ""
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def parse_wegweiser_file(file_path: Path) -> list[dict]:
    records = []
    content = None
    for enc in ["utf-8-sig", "utf-8", "cp1252", "latin-1"]:
        try:
            content = file_path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue

    if not content:
        return records

    content = fix_mojibake(content)
    first_lines = "\n".join(content.splitlines()[:20])
    delimiter = "\t" if "\t" in first_lines else (";" if ";" in first_lines else ",")

    reader = list(csv.reader(io.StringIO(content), delimiter=delimiter, quotechar='"'))
    if not reader:
        return records

    stem = file_path.stem
    parts = stem.split("_", 1)
    commune_slug = parts[0]
    ind_slug_from_filename = parts[1].lower() if len(parts) > 1 else ""

    commune_name = commune_slug.replace("-", " ").strip().title()
    if commune_slug.lower() == "nordrhein-westfalen":
        commune_name = "Nordrhein-Westfalen"

    matched_info = SLUG_TO_INFO.get(ind_slug_from_filename)

    if matched_info:
        handlungsfeld = matched_info["handlungsfeld"]
        default_ind_name = matched_info["indikator_name"]
    else:
        handlungsfeld = "Sonstige Handlungsfelder"
        default_ind_name = ind_slug_from_filename.replace("-", " ").title()

    is_nrw_file = ("nordrhein-westfalen" in commune_slug.lower() or commune_slug.lower() == "nrw")

    header_idx = None
    year_columns = {}

    for idx, row in enumerate(reader[:15]):
        years = {}
        for col_idx, cell in enumerate(row):
            match = re.search(r"\b(19\d\d|20[0-3]\d)\b", cell)
            if match:
                cell_lower = cell.lower()
                if "benchmark" in cell_lower:
                    continue
                if not is_nrw_file and ("nrw" in cell_lower or "land" in cell_lower or "nordrhein" in cell_lower):
                    continue
                years[col_idx] = int(match.group(1))

        if len(years) >= 2:
            header_idx = idx
            year_columns = years
            break

    if header_idx is None or not year_columns:
        return records

    for row in reader[header_idx + 1:]:
        if not row or not any(cell.strip() for cell in row):
            continue

        label_cell = row[0].strip().strip('"')
        label_lower = label_cell.lower()

        if any(label_lower.startswith(stop) for stop in [
            "k.a. =", "k.a.=", "quelle", "lizenz", "quellenangabe",
            "die indikator", "http", "stand:", "bertelsmann"
        ]):
            break

        if not label_cell:
            continue

        unit_match = re.search(r"\((.*?)\)", label_cell)
        unit = unit_match.group(1).strip() if unit_match else ""
        clean_indicator = re.sub(r"\s*\(.*?\)", "", label_cell).strip()
        if not clean_indicator:
            clean_indicator = default_ind_name

        for col_idx, year in year_columns.items():
            raw_val = row[col_idx].strip().strip('"') if col_idx < len(row) else ""

            if raw_val.lower() in ["k.a.", "k. a.", "-", "", "na", "null", ".", "/", "x"]:
                clean_val = None
            else:
                val_str = raw_val.replace(" ", "").replace("\xa0", "")
                if "," in val_str:
                    val_str = val_str.replace(".", "").replace(",", ".")
                else:
                    val_str = val_str.replace(".", "")
                try:
                    clean_val = float(val_str)
                except ValueError:
                    clean_val = None

            records.append({
                "Kommune": commune_name,
                "Handlungsfeld": handlungsfeld,
                "Indikator": clean_indicator,
                "Einheit": unit,
                "Jahr": year,
                "Wert": clean_val,
                "Dateiname": file_path.name
            })

    return records


def format_df_for_preview(df: pd.DataFrame) -> pd.DataFrame:
    df_prev = df.copy()
    for col in df_prev.columns:
        if col not in ["Kommune", "Handlungsfeld", "Indikator", "Einheit", "Jahr", "Dateiname"]:
            df_prev[col] = df_prev[col].apply(
                lambda x: "k.A." if pd.isna(x) else (
                    f"{int(x)}" if isinstance(x, (int, float)) and x == int(x)
                    else str(x).replace(".", ",")
                )
            )
    return df_prev


def process_temp_files(temp_dir: Path, period_str: str) -> tuple[bool, str, dict]:
    csv_files = list(temp_dir.glob("**/*.csv"))
    if not csv_files:
        return False, "Keine CSV-Dateien gefunden.", {}

    all_records = []
    files_with_data = 0

    for file_path in csv_files:
        records = parse_wegweiser_file(file_path)
        if records:
            files_with_data += 1
            all_records.extend(records)

    if not all_records:
        return False, "Keine gültigen Datensätze extrahiert.", {}

    df_long = pd.DataFrame(all_records)
    df_long["Wert"] = pd.to_numeric(df_long["Wert"], errors="coerce")

    df_long = df_long.drop_duplicates(subset=["Kommune", "Handlungsfeld", "Indikator", "Einheit", "Jahr"])
    df_long = df_long.sort_values(by=["Kommune", "Indikator", "Jahr"]).reset_index(drop=True)

    years_match = re.findall(r"\b(20[0-3]\d|19\d\d)\b", period_str)
    if len(years_match) >= 2:
        start_yr, end_yr = int(years_match[0]), int(years_match[1])
        all_years = list(range(start_yr, end_yr + 1))
    else:
        all_years = sorted(df_long["Jahr"].dropna().unique().astype(int).tolist())

    # --- 1. Long-Format Export ---
    long_buffer = io.BytesIO()
    df_long.to_csv(long_buffer, sep=";", decimal=",", na_rep="k.A.", index=False, encoding="utf-8-sig")
    long_bytes = long_buffer.getvalue()

    # --- 2. Wide-Format Jahre ---
    df_wide = df_long.pivot(
        index=["Kommune", "Handlungsfeld", "Indikator", "Einheit"],
        columns="Jahr",
        values="Wert"
    )
    df_wide = df_wide.reindex(columns=all_years).reset_index()
    df_wide.columns = [
        f"Wert_{col}" if isinstance(col, (int, float)) or (isinstance(col, str) and str(col).isdigit())
        else col
        for col in df_wide.columns
    ]
    df_wide.columns.name = None
    df_wide = df_wide.sort_values(by=["Kommune", "Indikator"]).reset_index(drop=True)

    wide_buffer = io.BytesIO()
    df_wide.to_csv(wide_buffer, sep=";", decimal=",", na_rep="k.A.", index=False, encoding="utf-8-sig")
    wide_bytes = wide_buffer.getvalue()

    # --- 3. Kommune-Wide-Format ---
    df_long_unique = df_long.drop_duplicates(subset=["Kommune", "Indikator", "Jahr"])
    df_commune_wide = df_long_unique.pivot(
        index="Kommune",
        columns=["Indikator", "Jahr"],
        values="Wert"
    )
    unique_inds = sorted(df_long_unique["Indikator"].dropna().unique())
    all_cols_multi = pd.MultiIndex.from_product([unique_inds, all_years], names=["Indikator", "Jahr"])
    df_commune_wide = df_commune_wide.reindex(columns=all_cols_multi)
    df_commune_wide.columns = [f"{col[0]}_{col[1]}" for col in df_commune_wide.columns]
    df_commune_wide = df_commune_wide.reindex(sorted(df_commune_wide.columns), axis=1)
    df_commune_wide = df_commune_wide.reset_index().sort_values(by="Kommune").reset_index(drop=True)

    commune_buffer = io.BytesIO()
    df_commune_wide.to_csv(commune_buffer, sep=";", decimal=",", na_rep="k.A.", index=False, encoding="utf-8-sig")
    commune_bytes = commune_buffer.getvalue()

    results = {
        "df_long_numeric": df_long,
        "df_long": format_df_for_preview(df_long),
        "df_wide": format_df_for_preview(df_wide),
        "df_commune_wide": format_df_for_preview(df_commune_wide),
        "long_bytes": long_bytes,
        "wide_bytes": wide_bytes,
        "commune_bytes": commune_bytes,
        "files_parsed": files_with_data,
        "total_files": len(csv_files),
    }

    msg = f"Erfolgreich! {files_with_data} Dateien aufbereitet (Lückenlose Jahre von {all_years[0]} bis {all_years[-1]})."
    return True, msg, results


# ==============================================================================
# MATPLOTLIB PLOTTING & EXPORT-HILFSFUNKTIONEN
# ==============================================================================

PRIMARY_COLOR = "#004B87"
ACCENT_COLOR = "#D9531E"
BENCHMARK_COLOR = "#718096"
GRID_COLOR = "#E2E8F0"

plt.rcParams.update({
    "font.sans-serif": "DejaVu Sans",
    "font.family": "sans-serif",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#CCCCCC",
    "axes.linewidth": 0.8,
    "grid.color": GRID_COLOR,
    "grid.linestyle": "--",
    "grid.linewidth": 0.7,
    "xtick.color": "#333333",
    "ytick.color": "#333333",
})

def plot_indicator_with_benchmark(
    df_commune_ind: pd.DataFrame,
    df_nrw_ind: pd.DataFrame,
    commune: str,
    indicator: str,
    unit: str,
    start_year: int = 2016,
    end_year: int = 2023,
    dpi: int = 300
) -> plt.Figure:
    fixed_years = list(range(start_year, end_year + 1))
    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=dpi)

    df_com_win = df_commune_ind[df_commune_ind["Jahr"].between(start_year, end_year)]
    df_com_valid = df_com_win.dropna(subset=["Wert"]).sort_values("Jahr")

    df_nrw_win = df_nrw_ind[df_nrw_ind["Jahr"].between(start_year, end_year)] if not df_nrw_ind.empty else pd.DataFrame()
    df_nrw_valid = df_nrw_win.dropna(subset=["Wert"]).sort_values("Jahr") if not df_nrw_win.empty else pd.DataFrame()

    ax.set_xlim(start_year - 0.5, end_year + 0.5)
    ax.set_xticks(fixed_years)
    ax.set_xticklabels([str(y) for y in fixed_years])

    if df_com_valid.empty:
        ax.text(
            0.5, 0.5,
            f"Keine Daten für {commune} im Zeitraum {start_year}–{end_year} verfügbar (k.A.)",
            ha="center", va="center", color="#718096", fontsize=11, style="italic",
            transform=ax.transAxes
        )
        ax.set_yticks([])
    else:
        com_years = df_com_valid["Jahr"].astype(int).tolist()
        com_values = df_com_valid["Wert"].astype(float).tolist()
        all_plotted_values = list(com_values)

        if not df_nrw_valid.empty:
            nrw_years = df_nrw_valid["Jahr"].astype(int).tolist()
            nrw_values = df_nrw_valid["Wert"].astype(float).tolist()
            all_plotted_values.extend(nrw_values)

            ax.plot(
                nrw_years, nrw_values,
                color=BENCHMARK_COLOR, linestyle="--", linewidth=1.8,
                label="Nordrhein-Westfalen (Landeswert)", zorder=2, alpha=0.85
            )
            ax.scatter(nrw_years, nrw_values, color=BENCHMARK_COLOR, s=25, zorder=3, alpha=0.8)

        ax.plot(
            com_years, com_values,
            color=PRIMARY_COLOR, linewidth=2.5,
            label=f"{commune}", zorder=4, alpha=0.95
        )
        ax.scatter(
            com_years, com_values,
            color=ACCENT_COLOR, s=45, edgecolor="white", linewidth=1.0, zorder=5
        )

        y_min_val = min(all_plotted_values)
        y_max_val = max(all_plotted_values)
        y_range = (y_max_val - y_min_val) if y_max_val != y_min_val else (abs(y_max_val) if y_max_val != 0 else 1.0)
        offset = y_range * 0.04

        for x, y in zip(com_years, com_values):
            if float(y).is_integer():
                val_text = f"{int(y):,}".replace(",", ".")
            else:
                val_text = f"{y:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            ax.annotate(
                val_text, (x, y),
                textcoords="offset points", xytext=(0, 7),
                ha="center", fontsize=8.5, weight="bold", color="#2D3748"
            )

        ax.grid(True, axis="y", zorder=1)
        ax.set_axisbelow(True)

        y_bottom = 0.0 if y_min_val >= 0 else y_min_val - offset * 2.5
        y_top = y_max_val + offset * 4.0
        ax.set_ylim(y_bottom, y_top)

        ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#E2E8F0", fontsize=8.5)

    unit_str = f" in {unit}" if unit else ""
    ax.set_title(f"{indicator}{unit_str}", fontsize=12.5, weight="bold", color="#1A202C", pad=14, loc="left")
    ax.set_xlabel("Jahr", fontsize=9.5, color="#4A5568", labelpad=8)
    ax.set_ylabel(unit if unit else "Wert", fontsize=9.5, color="#4A5568", labelpad=8)

    plt.figtext(
        0.01, 0.01,
        f"Kommune: {commune} | Benchmark: NRW | Zeitraum: {start_year}–{end_year} | Quelle: Wegweiser Kommune",
        ha="left", fontsize=7.5, color="#718096"
    )

    sns.despine(top=True, right=True)
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    return fig


def fig_to_bytes(fig: plt.Figure, fmt: str = "png", dpi: int = 300) -> bytes:
    buf = io.BytesIO()
    save_kwargs = {"format": fmt, "bbox_inches": "tight", "facecolor": "white"}
    if fmt in ["png", "jpg", "jpeg", "pdf"]:
        save_kwargs["dpi"] = dpi
    fig.savefig(buf, **save_kwargs)
    buf.seek(0)
    return buf.getvalue()


def generate_commune_pdf_bytes(df_num: pd.DataFrame, commune: str, start_year: int, end_year: int, dpi: int = 300) -> bytes:
    buf = io.BytesIO()
    nrw_mask = df_num["Kommune"].str.lower().str.contains("nordrhein-westfalen", na=False)
    df_nrw = df_num[nrw_mask]
    df_com = df_num[df_num["Kommune"] == commune]
    indicators = sorted(df_com["Indikator"].dropna().unique())

    with PdfPages(buf) as pdf:
        for ind in indicators:
            df_ind_com = df_com[df_com["Indikator"] == ind]
            df_ind_nrw = df_nrw[df_nrw["Indikator"] == ind] if not df_nrw.empty else pd.DataFrame()
            unit_series = df_ind_com["Einheit"].dropna()
            unit = unit_series.iloc[0] if not unit_series.empty else (
                df_ind_nrw["Einheit"].dropna().iloc[0] if not df_ind_nrw.empty and not df_ind_nrw["Einheit"].dropna().empty else ""
            )

            fig = plot_indicator_with_benchmark(df_ind_com, df_ind_nrw, commune, ind, unit, start_year, end_year, dpi)
            pdf.savefig(fig, bbox_inches="tight", facecolor="white")
            plt.close(fig)

    buf.seek(0)
    return buf.getvalue()


def generate_all_plots_zip_bytes(df_num: pd.DataFrame, commune: str, fmt: str, start_year: int, end_year: int, dpi: int = 300) -> bytes:
    buf = io.BytesIO()
    nrw_mask = df_num["Kommune"].str.lower().str.contains("nordrhein-westfalen", na=False)
    df_nrw = df_num[nrw_mask]
    df_com = df_num[df_num["Kommune"] == commune]
    indicators = sorted(df_com["Indikator"].dropna().unique())

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for ind in indicators:
            df_ind_com = df_com[df_com["Indikator"] == ind]
            df_ind_nrw = df_nrw[df_nrw["Indikator"] == ind] if not df_nrw.empty else pd.DataFrame()
            unit_series = df_ind_com["Einheit"].dropna()
            unit = unit_series.iloc[0] if not unit_series.empty else (
                df_ind_nrw["Einheit"].dropna().iloc[0] if not df_ind_nrw.empty and not df_ind_nrw["Einheit"].dropna().empty else ""
            )

            fig = plot_indicator_with_benchmark(df_ind_com, df_ind_nrw, commune, ind, unit, start_year, end_year, dpi)
            img_bytes = fig_to_bytes(fig, fmt=fmt, dpi=dpi)
            plt.close(fig)

            clean_ind = re.sub(r"[^a-zA-Z0-9_\-]", "_", ind.lower())
            zf.writestr(f"{commune.lower()}_{clean_ind}_{start_year}_{end_year}.{fmt}", img_bytes)

    buf.seek(0)
    return buf.getvalue()


# ==============================================================================
# JAVASCRIPT „SPEICHERN UNTER“-DIALOG HELFER
# ==============================================================================

def render_save_dialog_button(file_bytes: bytes, file_name: str, label: str, button_type: str = "primary"):
    b64_data = base64.b64encode(file_bytes).decode()
    ext = Path(file_name).suffix.lower()

    mime_map = {
        ".csv": ("text/csv;charset=utf-8;", "CSV-Datei", "text/csv"),
        ".png": ("image/png", "PNG-Grafik", "image/png"),
        ".jpg": ("image/jpeg", "JPEG-Grafik", "image/jpeg"),
        ".jpeg": ("image/jpeg", "JPEG-Grafik", "image/jpeg"),
        ".svg": ("image/svg+xml;charset=utf-8", "SVG-Vektorgrafik", "image/svg+xml"),
        ".pdf": ("application/pdf", "PDF-Dokument", "application/pdf"),
        ".zip": ("application/zip", "ZIP-Archiv", "application/zip"),
    }
    blob_mime, desc, accept_mime = mime_map.get(ext, ("application/octet-stream", "Datei", "application/octet-stream"))

    custom_html = f"""
    <html>
    <head>
    <style>
      .save-btn {{
        background-color: {"#76B82A" if button_type == "primary" else "#FFFFFF"};
        color: {"white" if button_type == "primary" else "#004B5A"};
        border: {"none" if button_type == "primary" else "1.5px solid #004B5A"};
        padding: 0.6rem 1rem;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 14px;
        font-weight: 600;
        font-family: 'Open Sans', sans-serif;
        border-radius: 5px;
        cursor: pointer;
        width: 100%;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: 0.2s;
      }}
      .save-btn:hover {{
        background-color: {"#629B21" if button_type == "primary" else "#004B5A"};
        color: white;
      }}
    </style>
    </head>
    <body>
      <button class="save-btn" onclick="saveFile()">💾 {label}</button>
      <script>
        function saveFile() {{
          const b64 = "{b64_data}";
          const filename = "{file_name}";
          const byteCharacters = atob(b64);
          const byteNumbers = new Array(byteCharacters.length);
          for (let i = 0; i < byteCharacters.length; i++) {{
            byteNumbers[i] = byteCharacters.charCodeAt(i);
          }}
          const byteArray = new Uint8Array(byteNumbers);
          const blob = new Blob([byteArray], {{ type: "{blob_mime}" }});
          
          if (window.showSaveFilePicker) {{
            window.showSaveFilePicker({{
              suggestedName: filename,
              types: [{{
                description: '{desc}',
                accept: {{ '{accept_mime}': ['{ext}'] }}
              }}]
            }}).then(async (handle) => {{
              const writable = await handle.createWritable();
              await writable.write(blob);
              await writable.close();
            }}).catch((err) => {{
              if (err.name !== 'AbortError') {{
                fallbackDownload(blob, filename);
              }}
            }});
          }} else {{
            fallbackDownload(blob, filename);
          }}
        }}
        
        function fallbackDownload(blob, filename) {{
          const link = document.createElement('a');
          link.href = URL.createObjectURL(blob);
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }}
      </script>
    </body>
    </html>
    """
    st.components.v1.html(custom_html, height=55)


# ==============================================================================
# CALLBACKS & CACHE CLEANUP
# ==============================================================================

def init_indicator_state():
    for idx, (cat_name, inds) in enumerate(INDICATORS_BY_CATEGORY.items()):
        chk_key = f"cat_chk_{idx}"
        ms_key = f"cat_ms_{idx}"
        if chk_key not in st.session_state:
            st.session_state[chk_key] = True
        if ms_key not in st.session_state:
            st.session_state[ms_key] = list(inds.keys())


def on_cat_checkbox_change(idx: int, ind_keys: list[str]):
    if st.session_state[f"cat_chk_{idx}"]:
        st.session_state[f"cat_ms_{idx}"] = ind_keys
    else:
        st.session_state[f"cat_ms_{idx}"] = []


def on_cat_multiselect_change(idx: int, total_count: int):
    current_selection = st.session_state[f"cat_ms_{idx}"]
    st.session_state[f"cat_chk_{idx}"] = (len(current_selection) == total_count)


def set_all_indicators(select_all: bool):
    for idx, inds in enumerate(INDICATORS_BY_CATEGORY.values()):
        st.session_state[f"cat_chk_{idx}"] = select_all
        st.session_state[f"cat_ms_{idx}"] = list(inds.keys()) if select_all else []


def cleanup_cache_dir():
    if st.session_state.get("cache_dir"):
        p = Path(st.session_state.cache_dir)
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
        st.session_state.cache_dir = None


# ==============================================================================
# STREAMLIT BENUTZEROBERFLÄCHE
# ==============================================================================

st.markdown(
    """
    <div class="lag21-header">
        <span class="lag21-header-badge">Prozesskette N – NKNRW 2026-2029</span>
        <h1>🏛️ Wegweiser Kommune / SDG-Portal Downloader & Aufbereitung</h1>
        <p>Automatisierter Datenabruf, lückenlose Jahresabdeckung, interaktives Plotly-Dashboard & Matplotlib-Export.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "processed_results" not in st.session_state:
    st.session_state.processed_results = None
if "cache_dir" not in st.session_state:
    st.session_state.cache_dir = None

init_indicator_state()

col1, col2 = st.columns([1, 1.8], gap="large")

# --- LINKE SPALTE: PARAMETER ---
with col1:
    with st.container(border=True):
        st.subheader("1. Parameter & Abruf")

        select_all_communes = st.checkbox("Alle 28 Kommunen auswählen", value=True)
        if select_all_communes:
            default_selection = DEFAULT_COMMUNES.copy()
        else:
            default_selection = ["bonn", "bielefeld", "wuppertal"]

        selected_communes = st.multiselect(
            "Kommunen / Referenzgebiete auswählen:",
            options=DEFAULT_COMMUNES,
            default=default_selection
        )

        include_nrw = st.checkbox("Landesdaten für Nordrhein-Westfalen (NRW) einbeziehen", value=True)

        custom_commune = st.text_input("Weitere Kommune hinzufügen:", placeholder="z. B. Aachen oder Gelsenkirchen")
        if custom_commune:
            custom_slug = slugify_commune(custom_commune)
            if custom_slug and custom_slug not in selected_communes:
                selected_communes.append(custom_slug)
                st.caption(f"➕ Hinzugefügt als Slug: `{custom_slug}`")

        if include_nrw and "nordrhein-westfalen" not in selected_communes:
            selected_communes.append("nordrhein-westfalen")

        st.markdown("---")
        time_period = st.text_input("Zeitraum (z. B. '2014-2023'):", value="2014-2023")

        st.info(
            "ℹ️ **Hinweis zum Speicherort:**\n\n"
            "Alle Jahre des Zeitraums werden lückenlos als Spalten ausgegeben. "
            "Über den Speichern-Dialog legst du Tabellen und Grafiken direkt im Zielordner ab."
        )

# --- RECHTE SPALTE: HANDLUNGSFELDER & INDIKATOREN ---
with col2:
    with st.container(border=True):
        st.subheader("2. Handlungsfelder & Indikatoren auswählen")
        st.caption("Klappe ein Handlungsfeld auf, um das gesamte Themenfeld oder gezielt einzelne Indikatoren an-/abzuwählen.")

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            st.button(
                "✅ Alle 40 Indikatoren auswählen",
                on_click=set_all_indicators,
                args=(True,),
                use_container_width=True,
                type="secondary"
            )
        with btn_col2:
            st.button(
                "🗑️ Gesamte Auswahl aufheben",
                on_click=set_all_indicators,
                args=(False,),
                use_container_width=True,
                type="secondary"
            )

        st.write("")

        selected_ind_names = []

        with st.container(height=450, border=False):
            for idx, (cat_name, inds_dict) in enumerate(INDICATORS_BY_CATEGORY.items()):
                ind_keys = list(inds_dict.keys())
                current_selected = st.session_state.get(f"cat_ms_{idx}", ind_keys)
                sel_count = len(current_selected)
                total_cat_count = len(ind_keys)

                if sel_count == total_cat_count:
                    status_icon = "🟢"
                elif sel_count > 0:
                    status_icon = "🟡"
                else:
                    status_icon = "⚪"

                expander_label = f"{status_icon} {cat_name} ({sel_count}/{total_cat_count} ausgewählt)"

                with st.expander(expander_label, expanded=False):
                    st.checkbox(
                        f"Alle Indikatoren in '{cat_name}' auswählen",
                        key=f"cat_chk_{idx}",
                        on_change=on_cat_checkbox_change,
                        args=(idx, ind_keys)
                    )

                    chosen = st.multiselect(
                        "Einzelne Indikatoren in diesem Handlungsfeld:",
                        options=ind_keys,
                        key=f"cat_ms_{idx}",
                        on_change=on_cat_multiselect_change,
                        args=(idx, total_cat_count),
                        label_visibility="collapsed"
                    )
                    selected_ind_names.extend(chosen)

        total_planned = len(selected_communes) * len(selected_ind_names)
        active_cats = sum(
            1 for idx in range(len(INDICATORS_BY_CATEGORY))
            if len(st.session_state.get(f"cat_ms_{idx}", [])) > 0
        )
        st.info(
            f"**Auswahl-Zusammenfassung:** `{len(selected_communes)}` Gebiete × "
            f"`{len(selected_ind_names)}` Indikatoren (aus `{active_cats}` Handlungsfeldern) = "
            f"**{total_planned} Abrufe**"
        )

st.write("")

# ==============================================================================
# AKTIONS-BUTTON & CHECKPOINT-DOWNLOADER
# ==============================================================================

if not st.session_state.is_running:
    start_download = st.button("🚀 Datenabruf & Panel-Aufbereitung starten", type="primary", use_container_width=True)

    if start_download:
        if not selected_communes:
            st.error("Bitte mindestens eine Kommune auswählen!")
        elif not selected_ind_names:
            st.error("Bitte mindestens einen Indikator auswählen!")
        else:
            cleanup_cache_dir()
            st.session_state.cache_dir = tempfile.mkdtemp(prefix="wegweiser_sdg_")
            st.session_state.is_running = True
            st.session_state.processed_results = None
            st.session_state["batch_commune_ready"] = None
            st.rerun()

else:
    if st.button("🛑 Abbrechen", type="secondary"):
        st.session_state.is_running = False
        cleanup_cache_dir()
        st.warning("Vorgang abgebrochen.")
        st.stop()

    if not st.session_state.cache_dir or not Path(st.session_state.cache_dir).exists():
        st.session_state.cache_dir = tempfile.mkdtemp(prefix="wegweiser_sdg_")

    temp_dir = Path(st.session_state.cache_dir)
    total_downloads = len(selected_communes) * len(selected_ind_names)

    with st.container(border=True):
        st.subheader("⏳ Status des Datenabrufs")
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        log_placeholder = st.empty()

    recent_logs = deque(maxlen=15)
    current_step = 0
    success_total = 0

    start_time = time.time()
    session = create_resilient_session()
    aborted = False

    for commune in selected_communes:
        if not st.session_state.is_running:
            aborted = True
            break

        commune_dir = temp_dir / commune
        commune_dir.mkdir(parents=True, exist_ok=True)

        for ind_name in selected_ind_names:
            if not st.session_state.is_running:
                aborted = True
                break

            ind_slug = ALL_INDICATORS[ind_name]
            current_step += 1

            status_text.markdown(f"**Lade ({current_step}/{total_downloads}):** `{commune}` ➔ *{ind_name}* ...")

            ok, msg, was_cached = download_file(
                session=session,
                commune_slug=commune,
                ind_name=ind_name,
                ind_slug=ind_slug,
                period=time_period,
                target_dir=commune_dir
            )

            if ok:
                icon = "⏭️" if was_cached else "✅"
                recent_logs.append(f"{icon} `{commune}` | {ind_name} ({msg})")
                success_total += 1
                if not was_cached:
                    time.sleep(random.uniform(0.2, 0.5))
            else:
                recent_logs.append(f"❌ `{commune}` | {ind_name} – Fehler: {msg}")
                time.sleep(random.uniform(0.5, 1.0))

            log_placeholder.markdown("  \n".join(recent_logs))
            progress_bar.progress(current_step / total_downloads)

    duration = round(time.time() - start_time, 1)
    status_text.empty()
    st.session_state.is_running = False

    if aborted:
        st.warning(f"Abgebrochen! {success_total} von {total_downloads} Dateien verarbeitet.")
        cleanup_cache_dir()
    else:
        st.success(f"Datenabruf beendet! {success_total}/{total_downloads} Dateien in {duration} Sekunden geladen.")

        if success_total > 0:
            with st.spinner("Bereite Panel-Tabellen mit lückenlosen Jahren auf..."):
                ok_proc, msg_proc, proc_res = process_temp_files(temp_dir, time_period)
                if ok_proc:
                    st.session_state.processed_results = proc_res
                    st.success(f"📊 {msg_proc}")
                else:
                    st.warning(f"Hinweis zur Aufbereitung: {msg_proc}")

        cleanup_cache_dir()


# ==============================================================================
# DATEN-VORSCHAU, PLOTLY-DASHBOARD & MATPLOTLIB-EXPORT
# ==============================================================================

if st.session_state.processed_results is not None:
    st.write("")
    with st.container(border=True):
        res = st.session_state.processed_results
        df_long = res["df_long"]
        df_wide = res["df_wide"]
        df_commune_wide = res["df_commune_wide"]

        st.subheader("📦 Aufbereitete Datensätze & Dashboards (Vorschau & Export)")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Geparste Indikatoren", f"{res['files_parsed']} / {res['total_files']}")
        m2.metric("Kommunen / Gebiete", df_long["Kommune"].nunique())
        m3.metric("Erfasste Indikatoren", df_long["Indikator"].nunique())
        m4.metric("Datenpunkte (Long)", f"{len(df_long):,}".replace(",", "."))

        st.markdown("Klicke auf einen Button, um im Browser den **„Speichern unter“-Dialog** für die Tabellen zu öffnen:")

        dl_col1, dl_col2, dl_col3 = st.columns(3)
        with dl_col1:
            render_save_dialog_button(res["long_bytes"], "wegweiser_sdg_panel_long.csv", "Long-Format speichern", "primary")
        with dl_col2:
            render_save_dialog_button(res["wide_bytes"], "wegweiser_sdg_panel_wide.csv", "Wide-Format speichern", "primary")
        with dl_col3:
            render_save_dialog_button(res["commune_bytes"], "wegweiser_sdg_panel_commune_wide.csv", "Kommune-Wide speichern", "primary")

        st.markdown("---")
        st.markdown("#### 🔍 Interaktive Datenvorschau & Dashboards")
        tab1, tab2, tab3, tab4 = st.tabs([
            "📄 Long-Format (Kommune × Indikator × Jahr)",
            "📊 Wide-Format (Jahre als Spalten)",
            "🏙️ Gemeinde-Wide-Format (1 Zeile pro Kommune)",
            "📈 Interaktives Plotly-Dashboard & Export"
        ])

        with tab1:
            st.dataframe(df_long, use_container_width=True, height=320)
        with tab2:
            st.dataframe(df_wide, use_container_width=True, height=320)
        with tab3:
            st.dataframe(df_commune_wide, use_container_width=True, height=320)

        with tab4:
            df_num = res["df_long_numeric"]

            available_communes = sorted(df_num["Kommune"].dropna().unique().tolist())
            available_indicators = sorted(df_num["Indikator"].dropna().unique().tolist())
            min_yr = int(df_num["Jahr"].min()) if not df_num["Jahr"].dropna().empty else 2014
            max_yr = int(df_num["Jahr"].max()) if not df_num["Jahr"].dropna().empty else 2023

            if not available_communes or not available_indicators:
                st.warning("Nicht genügend Daten für eine Grafik-Darstellung vorhanden.")
            else:
                ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1.5, 1.8, 1.2, 1])
                with ctrl1:
                    default_com = [c for c in ["Nordrhein-Westfalen"] if c in available_communes]
                    if not default_com and available_communes:
                        default_com = [available_communes[0]]
                    selected_communes = st.multiselect(
                        "Kommunen / Benchmark:",
                        options=available_communes,
                        default=default_com,
                        key="plotly_coms"
                    )
                with ctrl2:
                    selected_indicator = st.selectbox(
                        "Indikator:",
                        options=available_indicators,
                        key="plotly_ind"
                    )
                with ctrl3:
                    year_range = st.slider(
                        "Zeitraum:",
                        min_value=min_yr,
                        max_value=max_yr,
                        value=(max(min_yr, 2016), max_yr),
                        key="plotly_yr"
                    )
                with ctrl4:
                    img_format = st.selectbox(
                        "Export-Format:",
                        options=["png", "svg", "jpg", "pdf"],
                        format_func=lambda x: x.upper(),
                        key="plot_fmt"
                    )

                df_filtered = df_num[
                    (df_num["Kommune"].isin(selected_communes))
                    & (df_num["Indikator"] == selected_indicator)
                    & (df_num["Jahr"].between(year_range[0], year_range[1]))
                ].dropna(subset=["Wert"])

                unit = ""
                if not df_filtered.empty:
                    valid_units = df_filtered["Einheit"].dropna()
                    if not valid_units.empty:
                        unit = valid_units.iloc[0]

                st.write("")

                if not df_filtered.empty:
                    # 1. Interaktiver Plotly-Graph für die Browser-Ansicht
                    fig_plotly = px.line(
                        df_filtered,
                        x="Jahr",
                        y="Wert",
                        color="Kommune",
                        markers=True,
                        title=f"{selected_indicator}{f' ({unit})' if unit else ''}",
                        labels={"Wert": f"Wert in {unit}" if unit else "Wert", "Jahr": "Erhebungsjahr"},
                    )
                    fig_plotly.update_xaxes(dtick=1, range=[year_range[0] - 0.5, year_range[1] + 0.5])
                    fig_plotly.update_layout(
                        template="plotly_white",
                        hovermode="x unified",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )

                    plot_col, export_col = st.columns([2.2, 1], gap="large")
                    with plot_col:
                        st.plotly_chart(fig_plotly, use_container_width=True)

                    # 2. Exakter Matplotlib-Export im Hintergrund (für Einzelbild, PDF & ZIP)
                    single_com_for_matpl = selected_communes[0] if selected_communes else "Nordrhein-Westfalen"
                    nrw_mask = df_num["Kommune"].str.lower().str.contains("nordrhein-westfalen", na=False)
                    df_ind_com = df_num[(df_num["Kommune"] == single_com_for_matpl) & (df_num["Indikator"] == selected_indicator)]
                    df_ind_nrw = df_num[nrw_mask & (df_num["Indikator"] == selected_indicator)]

                    fig_matpl = plot_indicator_with_benchmark(
                        df_commune_ind=df_ind_com,
                        df_nrw_ind=df_ind_nrw,
                        commune=single_com_for_matpl,
                        indicator=selected_indicator,
                        unit=unit,
                        start_year=year_range[0],
                        end_year=year_range[1],
                        dpi=300
                    )

                    single_plot_bytes = fig_to_bytes(fig_matpl, fmt=img_format, dpi=300)
                    plt.close(fig_matpl)

                    clean_com = re.sub(r"[^a-zA-Z0-9_\-]", "_", single_com_for_matpl.lower())
                    clean_ind = re.sub(r"[^a-zA-Z0-9_\-]", "_", selected_indicator.lower())
                    single_filename = f"{clean_com}_{clean_ind}_{year_range[0]}_{year_range[1]}.{img_format}"

                    with export_col:
                        st.markdown("##### 📥 Einzelgrafik exportieren")
                        st.caption(f"Speichert Grafik für *{single_com_for_matpl}* als .{img_format.upper()}:")
                        render_save_dialog_button(
                            file_bytes=single_plot_bytes,
                            file_name=single_filename,
                            label=f"Aktuellen Plot speichern",
                            button_type="primary"
                        )

                        st.markdown("---")
                        st.markdown(f"##### 📚 Gesamtexport für *{single_com_for_matpl}*")
                        st.caption("Alle Indikatoren dieser Kommune generieren:")

                        batch_fmt = "png" if img_format == "pdf" else img_format
                        if st.button(f"⚙️ Sammel-PDF & {batch_fmt.upper()}-ZIP erzeugen", use_container_width=True, type="secondary"):
                            with st.spinner(f"Generiere Grafiken für {single_com_for_matpl}..."):
                                st.session_state["batch_pdf_bytes"] = generate_commune_pdf_bytes(
                                    df_num, single_com_for_matpl, year_range[0], year_range[1]
                                )
                                st.session_state["batch_pdf_name"] = f"{clean_com}_sdg_datenblatt_{year_range[0]}_{year_range[1]}.pdf"

                                st.session_state["batch_zip_bytes"] = generate_all_plots_zip_bytes(
                                    df_num, single_com_for_matpl, batch_fmt, year_range[0], year_range[1]
                                )
                                st.session_state["batch_zip_name"] = f"{clean_com}_alle_grafiken_{year_range[0]}_{year_range[1]}_{batch_fmt}.zip"
                                st.session_state["batch_commune_ready"] = f"{single_com_for_matpl}_{year_range[0]}_{year_range[1]}_{batch_fmt}"

                        if st.session_state.get("batch_commune_ready") == f"{single_com_for_matpl}_{year_range[0]}_{year_range[1]}_{batch_fmt}":
                            render_save_dialog_button(
                                file_bytes=st.session_state["batch_pdf_bytes"],
                                file_name=st.session_state["batch_pdf_name"],
                                label="Sammel-Datenblatt (.PDF) speichern",
                                button_type="secondary"
                            )
                            render_save_dialog_button(
                                file_bytes=st.session_state["batch_zip_bytes"],
                                file_name=st.session_state["batch_zip_name"],
                                label=f"Alle Grafiken (.{batch_fmt.upper()}-ZIP) speichern",
                                button_type="secondary"
                            )

                    with st.expander("📄 Zugehörige Tabellenwerte anzeigen"):
                        st.dataframe(
                            df_filtered[["Kommune", "Jahr", "Wert", "Einheit"]].sort_values(["Kommune", "Jahr"]),
                            use_container_width=True,
                        )
                else:
                    st.info("Keine Daten für die gewählte Kombination im angegebenen Zeitraum vorhanden.")
