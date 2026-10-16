import csv
import io
import random
import re
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
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
            --lag-petrol: #004B5A;       /* Dunkles Petrol/Blau für Header & Textfokus */
            --lag-petrol-light: #00667A; /* Helleres Petrol für Hover-Effekte */
            --lag-green: #76B82A;        /* Nachhaltigkeits-Grün für Akzente & Buttons */
            --lag-green-hover: #629B21;  /* Dunkleres Grün für Button-Hover */
            --lag-bg: #F4F7F6;           /* Sanftes Grau-Grün für den Seitenhintergrund */
            --lag-card-bg: #FFFFFF;      /* Weiß für Inhalts-Container */
            --lag-text: #2C3E50;         /* Dunkles Schiefergrau für Fließtext */
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
# DATENBASIS & GRUPPIERTE INDIKATOREN
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
    "Connection": "close",
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

INDICATOR_TO_CATEGORY = {
    ind_key: cat_name
    for cat_name, cat_dict in INDICATORS_BY_CATEGORY.items()
    for ind_key in cat_dict.keys()
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
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def download_file(
    session: requests.Session,
    commune_slug: str,
    ind_name: str,
    ind_slug: str,
    period: str,
    target_dir: Path,
    skip_existing: bool = True
) -> tuple[bool, str]:
    file_name = f"{commune_slug}_{ind_name}.csv"
    output_path = target_dir / file_name

    if skip_existing and output_path.exists() and output_path.stat().st_size > 0:
        kb = round(output_path.stat().st_size / 1024, 1)
        return True, f"Bereits vorhanden ({kb} KB, übersprungen)"

    slug = f"{ind_slug}+{commune_slug}+{period}+tabelle"
    url = f"{BASE_URL}/{slug}.csv"
    params = {"charset": "UTF-8"}

    try:
        res = session.get(url, params=params, timeout=30)
        if res.status_code == 200:
            if "text/html" in res.headers.get("Content-Type", ""):
                return False, "Server lieferte HTML (Slug evtl. ungültig)"
            with open(output_path, "wb") as f:
                f.write(res.content)
            kb = round(len(res.content) / 1024, 1)
            return True, f"{kb} KB"
        return False, f"HTTP {res.status_code}"
    except Exception as e:
        return False, str(e)


# ==============================================================================
# DATENAUFBEREITUNG (PARSING & TRANSFORMATION)
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

    if file_path.parent.name and file_path.parent.name != file_path.anchor:
        commune_slug = file_path.parent.name
        prefix = f"{commune_slug}_"
        ind_key = file_path.stem[len(prefix):] if file_path.stem.startswith(prefix) else file_path.stem
    else:
        parts = file_path.stem.split("_", 1)
        commune_slug = parts[0]
        ind_key = parts[1] if len(parts) > 1 else file_path.stem

    commune_name = commune_slug.replace("-", " ").strip().title()
    if commune_slug == "nordrhein-westfalen":
        commune_name = "Nordrhein-Westfalen"

    handlungsfeld = INDICATOR_TO_CATEGORY.get(ind_key, "Sonstige")
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

        for col_idx, year in year_columns.items():
            raw_val = row[col_idx].strip().strip('"') if col_idx < len(row) else ""

            if raw_val.lower() in ["k.a.", "k. a.", "-", "", "na", "null", ".", "/", "x"]:
                clean_val = None
            else:
                val_str = raw_val.replace(" ", "").replace("\xa0", "")
                if "," in val_str:
                    val_str = val_str.replace(".", "").replace(",", ".")
                try:
                    clean_val = float(val_str)
                except ValueError:
                    clean_val = None

            records.append({
                "Kommune": commune_name,
                "Handlungsfeld": handlungsfeld,
                "Indikator_Key": ind_key,
                "Indikator": clean_indicator,
                "Indikator_Original": label_cell,
                "Einheit": unit,
                "Jahr": year,
                "Wert": clean_val,
                "Dateiname": file_path.name
            })

    return records


def process_all_files(input_dir: Path, output_dir: Path) -> tuple[bool, str, dict]:
    if not input_dir.exists():
        return False, f"Der Eingabeordner '{input_dir.resolve()}' wurde nicht gefunden.", {}

    csv_files = list(input_dir.glob("**/*.csv"))
    if not csv_files:
        return False, f"Keine CSV-Dateien im Verzeichnis '{input_dir}' gefunden.", {}

    all_records = []
    files_with_data = 0

    for file_path in csv_files:
        records = parse_wegweiser_file(file_path)
        if records:
            files_with_data += 1
            all_records.extend(records)

    if not all_records:
        return False, "Keine gültigen Datensätze aus den CSV-Dateien extrahiert.", {}

    output_dir.mkdir(parents=True, exist_ok=True)

    df_long = pd.DataFrame(all_records)
    df_long = df_long.drop_duplicates(subset=["Kommune", "Indikator", "Einheit", "Jahr"])
    df_long = df_long.sort_values(by=["Kommune", "Indikator", "Jahr"]).reset_index(drop=True)

    long_path = output_dir / "wegweiser_sdg_panel_long.csv"
    df_long.to_csv(long_path, sep=";", decimal=",", index=False, encoding="utf-8-sig")

    df_wide = df_long.pivot_table(
        index=["Kommune", "Handlungsfeld", "Indikator", "Einheit"],
        columns="Jahr",
        values="Wert",
        aggfunc="first",
        dropna=False
    ).reset_index()

    df_wide.columns = [
        f"Wert_{col}" if isinstance(col, (int, float)) or (isinstance(col, str) and str(col).isdigit())
        else col
        for col in df_wide.columns
    ]
    df_wide.columns.name = None
    df_wide = df_wide.sort_values(by=["Kommune", "Indikator"]).reset_index(drop=True)

    wide_path = output_dir / "wegweiser_sdg_panel_wide.csv"
    df_wide.to_csv(wide_path, sep=";", decimal=",", index=False, encoding="utf-8-sig")

    df_commune_wide = df_long.pivot_table(
        index="Kommune",
        columns=["Indikator", "Jahr"],
        values="Wert",
        aggfunc="first",
        dropna=False
    )

    df_commune_wide.columns = [f"{col[0]}_{col[1]}" for col in df_commune_wide.columns]
    df_commune_wide = df_commune_wide.reindex(sorted(df_commune_wide.columns), axis=1)
    df_commune_wide = df_commune_wide.reset_index().sort_values(by="Kommune").reset_index(drop=True)

    commune_wide_path = output_dir / "wegweiser_sdg_panel_commune_wide.csv"
    df_commune_wide.to_csv(commune_wide_path, sep=";", decimal=",", index=False, encoding="utf-8-sig")

    results = {
        "df_long": df_long,
        "df_wide": df_wide,
        "df_commune_wide": df_commune_wide,
        "long_bytes": long_path.read_bytes(),
        "wide_bytes": wide_path.read_bytes(),
        "commune_wide_bytes": commune_wide_path.read_bytes(),
        "files_parsed": files_with_data,
        "total_files": len(csv_files),
    }

    msg = f"Erfolgreich! {files_with_data} von {len(csv_files)} CSVs geparst ({len(df_long):,} Datenpunkte)."
    return True, msg, results


def create_bundle_zip_in_memory(raw_dir: Path, processed_dir: Path | None = None) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if raw_dir.exists():
            for file in raw_dir.rglob("*.csv"):
                archive_name = Path("01_rohdaten") / file.relative_to(raw_dir)
                zip_file.write(file, arcname=archive_name)
        if processed_dir and processed_dir.exists():
            for file in processed_dir.glob("*.csv"):
                archive_name = Path("02_aufbereitet") / file.name
                zip_file.write(file, arcname=archive_name)
    zip_buffer.seek(0)
    return zip_buffer


# ==============================================================================
# CALLBACKS FÜR DIE INDIKATOREN-STEUERUNG
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


# ==============================================================================
# STREAMLIT BENUTZEROBERFLÄCHE
# ==============================================================================

st.markdown(
    """
    <div class="lag21-header">
        <span class="lag21-header-badge">Prozesskette N – NKNRW 2026-2029</span>
        <h1>🏛️ Wegweiser Kommune / SDG-Portal (Mit flexiblem Speicherort)</h1>
        <p>Automatisierter Datenabruf inkl. Panel-Aufbereitung. Passe den Speicherort flexibel an deinen lokalen Rechner oder SharePoint an.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "zip_data" not in st.session_state:
    st.session_state.zip_data = None
if "processed_results" not in st.session_state:
    st.session_state.processed_results = None

init_indicator_state()

col1, col2 = st.columns([1, 1.8], gap="large")

# --- LINKE SPALTE: FLEXIBLE PFAD-AUSWAHL & ERKLÄRUNG ---
with col1:
    with st.container(border=True):
        st.subheader("1. Speicherort & Parameter")

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

        # Dynamischer Standardpfad basierend auf dem aktuellen Windows-Benutzer
        default_sharepoint_base = (
            Path.home()
            / "LAG 21 NRW"
            / "Prozesskette N - NKNRW 2026-2029"
            / "02_Durchführung"
            / "00_Material allgemein"
            / "Daten_Webweiser_Kommune"
        )
        
        # Eingabefelder für manuelle Pfad-Wahl
        out_dir_str = st.text_input(
            "Zielordner für Rohdaten:", 
            value=str(default_sharepoint_base / "01_rohdaten")
        )
        out_base_dir = Path(out_dir_str)

        processed_dir_str = st.text_input(
            "Zielordner für aufbereitete Daten:", 
            value=str(default_sharepoint_base / "02_aufbereitet")
        )
        processed_base_dir = Path(processed_dir_str)

        # ℹ️ Erläuterung zum Speicherort direkt darunter anzeigen
        st.info(
            "📂 **Erläuterung zum Speicherort:**\n\n"
            "Die App speichert alle Daten direkt in den angegebenen Ordner auf deiner Festplatte. "
            "Wenn du den Standard-Pfad (synchronisierter SharePoint-Ordner) beibehältst, synchronisiert "
            "OneDrive die neuen CSV- und Panel-Dateien **vollautomatisch im Hintergrund für das gesamte Projektteam** in SharePoint."
        )

        skip_existing_files = st.checkbox("Bereits heruntergeladene Rohdateien überspringen", value=True)
        auto_process = st.checkbox("Nach Download automatisch Panel-Tabellen generieren", value=True)

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
            f"**{total_planned} CSV-Dateien**"
        )

st.write("")

# ==============================================================================
# AKTIONS-BUTTONS
# ==============================================================================

action_col1, action_col2 = st.columns([1.5, 1])

if not st.session_state.is_running:
    with action_col1:
        start_download = st.button(
            "🚀 Download & Aufbereitung in Zielordner starten",
            type="primary",
            use_container_width=True
        )
    with action_col2:
        only_process = st.button(
            "⚙️ Nur Zielordner neu aufbereiten",
            type="secondary",
            use_container_width=True
        )

    if start_download:
        if not selected_communes:
            st.error("Bitte mindestens eine Kommune auswählen!")
        elif not selected_ind_names:
            st.error("Bitte mindestens einen Indikator auswählen!")
        else:
            st.session_state.is_running = True
            st.session_state.zip_data = None
            st.rerun()

    if only_process:
        with st.spinner("Verarbeite lokale CSVs im gewählten Ordner..."):
            ok_proc, msg_proc, proc_res = process_all_files(out_base_dir, processed_base_dir)
            if ok_proc:
                st.session_state.processed_results = proc_res
                st.session_state.zip_data = create_bundle_zip_in_memory(out_base_dir, processed_base_dir)
                st.success(f"✅ Ordner erfolgreich aktualisiert: {msg_proc}")
            else:
                st.error(msg_proc)

else:
    if st.button("🛑 Abbrechen", type="secondary"):
        st.session_state.is_running = False
        st.warning("Vorgang abgebrochen.")
        st.stop()

    out_base_dir.mkdir(parents=True, exist_ok=True)
    total_downloads = len(selected_communes) * len(selected_ind_names)

    with st.container(border=True):
        st.subheader("⏳ Status des Datenabrufs")
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        log_box = st.container(height=320)

    current_step = 0
    success_total = 0

    start_time = time.time()
    session = create_resilient_session()
    aborted = False

    for commune in selected_communes:
        if not st.session_state.is_running:
            aborted = True
            break

        commune_dir = out_base_dir / commune
        commune_dir.mkdir(parents=True, exist_ok=True)

        with log_box:
            st.markdown(f"**🏙️ Verarbeite Kommune:** `{commune}`")

        for ind_name in selected_ind_names:
            if not st.session_state.is_running:
                aborted = True
                break

            ind_slug = ALL_INDICATORS[ind_name]
            current_step += 1

            status_text.markdown(f"**Lade ({current_step}/{total_downloads}):** `{commune}` ➔ *{ind_name}* ...")

            ok, msg = download_file(
                session=session,
                commune_slug=commune,
                ind_name=ind_name,
                ind_slug=ind_slug,
                period=time_period,
                target_dir=commune_dir,
                skip_existing=skip_existing_files
            )

            with log_box:
                if ok:
                    if "übersprungen" in msg:
                        st.caption(f"⏩ {commune} | {ind_name} ({msg})")
                    else:
                        st.caption(f"✅ {commune} | {ind_name} ({msg})")
                        time.sleep(random.uniform(1.2, 2.8))
                    success_total += 1
                else:
                    st.caption(f"❌ {commune} | {ind_name} – Fehler: {msg}")
                    time.sleep(random.uniform(2.0, 3.5))

            progress_bar.progress(current_step / total_downloads)

    duration = round(time.time() - start_time, 1)
    status_text.empty()
    st.session_state.is_running = False

    if aborted:
        st.warning(f"Abgebrochen! {success_total} von {total_downloads} Dateien verarbeitet.")
    else:
        st.success(f"Download fertig! {success_total}/{total_downloads} Dateien in {duration} Sekunden verarbeitet.")

    if auto_process and success_total > 0:
        with st.spinner("Erstelle aufbereitete Panel-Tabellen im Zielordner..."):
            ok_proc, msg_proc, proc_res = process_all_files(out_base_dir, processed_base_dir)
            if ok_proc:
                st.session_state.processed_results = proc_res
                st.success(f"📊 {msg_proc}")
            else:
                st.warning(f"Hinweis zur Aufbereitung: {msg_proc}")

    st.session_state.zip_data = create_bundle_zip_in_memory(
        out_base_dir,
        processed_base_dir if auto_process else None
    )


# ==============================================================================
# DATEN-VORSCHAU & DOWNLOAD
# ==============================================================================

if st.session_state.processed_results is not None or st.session_state.zip_data is not None:
    st.write("")
    with st.container(border=True):
        st.subheader("📦 3. Aufbereitete Datensätze & Downloads")

        if st.session_state.processed_results is not None:
            res = st.session_state.processed_results
            df_long = res["df_long"]
            df_wide = res["df_wide"]
            df_commune_wide = res["df_commune_wide"]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Geparste CSVs", f"{res['files_parsed']} / {res['total_files']}")
            m2.metric("Kommunen / Gebiete", df_long["Kommune"].nunique())
            m3.metric("Erfasste Indikatoren", df_long["Indikator"].nunique())
            m4.metric("Datenpunkte (Long)", f"{len(df_long):,}".replace(",", "."))

            st.markdown("#### Dateien im Zielordner aktualisiert & zusätzlich direkt herunterladbar")
            dl_col1, dl_col2, dl_col3, dl_col4 = st.columns(4)

            with dl_col1:
                st.download_button(
                    label="📄 Long-Format (.csv)",
                    data=res["long_bytes"],
                    file_name="wegweiser_sdg_panel_long.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )
            with dl_col2:
                st.download_button(
                    label="📊 Wide-Format (.csv)",
                    data=res["wide_bytes"],
                    file_name="wegweiser_sdg_panel_wide.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )
            with dl_col3:
                st.download_button(
                    label="🏙️ Kommune-Wide (.csv)",
                    data=res["commune_wide_bytes"],
                    file_name="wegweiser_sdg_panel_commune_wide.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )
            with dl_col4:
                if st.session_state.zip_data is not None:
                    st.download_button(
                        label="📦 Komplettpaket (.zip)",
                        data=st.session_state.zip_data,
                        file_name="nknrw_sdg_datenpaket.zip",
                        mime="application/zip",
                        type="secondary",
                        use_container_width=True
                    )

            st.markdown("---")
            st.markdown("#### 🔍 Interaktive Datenvorschau")
            tab1, tab2, tab3 = st.tabs([
                "📄 Long-Format (Kommune × Indikator × Jahr)",
                "📊 Wide-Format (Jahre als Spalten)",
                "🏙️ Gemeinde-Wide-Format (1 Zeile pro Kommune)"
            ])

            with tab1:
                st.dataframe(df_long, use_container_width=True, height=320)
            with tab2:
                st.dataframe(df_wide, use_container_width=True, height=320)
            with tab3:
                st.dataframe(df_commune_wide, use_container_width=True, height=320)
