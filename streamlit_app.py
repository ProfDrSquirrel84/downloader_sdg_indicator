import io
import random
import re
import shutil
import time
import zipfile
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
import streamlit as st
from urllib3.util.retry import Retry

# ==============================================================================
# SEITENKONFIGURATION & LAG 21 NRW DESIGN (CSS)
# ==============================================================================

st.set_page_config(
    page_title="SDG-Datenportal | LAG 21 NRW Stil",
    page_icon="🌿",
    layout="wide"
)

def apply_lag21_theme():
    """Injiziert Custom CSS im Stil der LAG 21 NRW (www.lag21.de)."""
    st.markdown(
        """
        <style>
        /* Google Font 'Open Sans' laden (typisch für moderne NGO/Verwaltungs-Websites) */
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

        /* Grundlegende Typografie & Hintergrund */
        .stApp {
            background-color: var(--lag-bg);
            font-family: 'Open Sans', sans-serif;
            color: var(--lag-text);
        }

        /* Überschriften im LAG-Petrol */
        h1, h2, h3, h4 {
            color: var(--lag-petrol) !important;
            font-weight: 700 !important;
        }

        /* Custom Header Banner im Stil der LAG 21 NRW */
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

        /* Styling der Karten/Container (st.container mit border=True) */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: var(--lag-card-bg);
            border: 1px solid #E0E7E5 !important;
            border-top: 4px solid var(--lag-green) !important;
            border-radius: 8px !important;
            padding: 1.25rem !important;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
        }

        /* Primäre Buttons (Grün wie auf lag21.de) */
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

        /* Sekundäre Buttons (Abbruch-Button in Petrol/Rot-Akzent) */
        div.stButton > button[kind="secondary"] {
            border: 2px solid var(--lag-petrol) !important;
            color: var(--lag-petrol) !important;
            background-color: transparent !important;
            border-radius: 5px !important;
            font-weight: 600 !important;
        }
        div.stButton > button[kind="secondary"]:hover {
            background-color: var(--lag-petrol) !important;
            color: white !important;
        }

        /* Multiselect-Tags (Ausgewählte Kommunen & Indikatoren) */
        span[data-baseweb="tag"] {
            background-color: var(--lag-petrol) !important;
            color: white !important;
            border-radius: 4px !important;
        }

        /* Fortschrittsbalken in LAG-Grün */
        div[data-testid="stProgressBar"] > div > div > div > div {
            background-color: var(--lag-green) !important;
        }

        /* Trennlinien */
        hr {
            border-color: #D5E0DD !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

apply_lag21_theme()


# ==============================================================================
# DATENBASIS & KONFIGURATION
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

ALL_INDICATORS = {
    # Steuerungskriterium: Haushalt und Finanzen
    "Steuereinnahmen": "steuereinnahmen-pro-einwohner-in",
    "Finanzmittelsaldo": "finanzmittelsaldo",
    "Liquiditaetskredite": "liquiditaetskredite",
    
    # Steuerungskriterium: Digitalisierung, Innovation und Forschung
    "Breitbandversorgung_Haushalte": "breitbandversorgung-private-haushalte",
    
    # Handlungsfeld 9: Klimaschutz & Klimaanpassung
    "Strom_aus_erneuerbaren_Quellen": "strom-aus-erneuerbaren-quellen",
    "Ladesaeuleninfrastruktur": "ladesaeuleninfrastruktur",
    "Wohngebaeude_erneuerbare_Heizenergie": "fertiggestellte-wohngebaeude-mit-erneuerbarer-energie",

    # Handlungsfeld 10: Kreislaufwirtschaft
    "Abfallmenge": "abfallmenge",
    
    # Handlungsfeld 11: Biodiversitäts- und Umweltschutz
    "Landschaftsqualitaet": "landschaftsqualitaet",
    "Naturschutzflaechen": "naturschutzflaechen",
    "Luftschadstoffbelastung": "luftschadstoffbelastung",
    "Siedlungslast_Ueberschwemmungsgebiet": "siedlungslast-im-ueberschwemmungsgebiet",
    "Abwasserbehandlung": "abwasserbehandlung",
    
    # Handlungsfeld 12: Nachhaltige Flächen- und Raumentwicklung
    "Flaechenneuinanspruchnahme": "flaechenneuinanspruchnahme",
    "Flaechennutzungsintensitaet": "flaechennutzungsintensitaet",
    "Flaecheninanspruchnahme": "flaecheninanspruchnahme",
    "Naherholungsflaechen": "naherholungsflaechen",
    "Stickstoffueberschuss-der-Landwirtschaft": "stickstoffueberschuss-der-landwirtschaft",

    # Handlungsfeld 13: Wohnen & nachhaltige Quartiere
    "Wohnungslosigkeit": "wohnungslosigkeit",
    "Mietpreise": "mietpreise",
    "Wohnungsnaher_Supermarkt": "wohnungsnahe-grundversorgung-supermarkt",
    "Wohnflaeche": "wohnflaeche-pro-person",
    
    # Handlungsfeld 14: Nachhaltige Mobilität
    "Verunglueckte_im_Verkehr": "verunglueckte-im-verkehr",
    "PKW-Dichte": "pkw-dichte",
    "PKW-mit-Elektroantrieb": "pkw-mit-elektroantrieb",
    
    # Handlungsfeld 15: Soziale Gerechtigkeit und zukunftsfähige Gesellschaft
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
    
    # Handlungsfeld 16: Bildung und Kultur
    "Wohnungsnahe_Grundschule": "wohnungsnahe-grundversorgung-grundschule",
    "Schulabgaenger_ohne_Hauptschulabschluss": "schulabgaenger-ohne-hauptschulabschluss-gesamt",

    # Handlungsfeld 17: Gesundheit
    "Wohnungsnaher_Hausarzt": "wohnungsnahe-grundversorgung-hausarzt",
    "Wohnungsnahe_Apotheke": "wohnungsnahe-grundversorgung-apotheke",
    "Wohnungsnahes_Krankenhaus": "wohnungsnahe-grundversorgung-krankenhaus",
    "Plaetze-in-Pflegeheimen": "plaetze-in-pflegeheimen",
    "Vorzeitige_Sterblichkeit": "vorzeitige-sterblichkeit-gesamt",
    
    # Handlungsfeld 18: Gute Arbeit und nachhaltiges Wirtschaften
    "Existenzgruendungen": "existenzgruendungen",
    "Beschaeftigungsquote": "beschaeftigungsquote",
    "Beschaeftigungsquote_55-64-jaehrige": "beschaeftigungsquote-55-bis-64-jaehrige",
    "Langzeitarbeitslosenquote": "langzeitarbeitslosenquote",
    "Hochqualifizierte_am_Arbeitsort": "hochqualifizierte-am-arbeitsort"    
}


# ==============================================================================
# HILFS- & DOWNLOAD-FUNKTIONEN
# ==============================================================================

def slugify_commune(name: str) -> str:
    """Wandelt Freitext-Namen in das API-Slug-Format um."""
    s = name.strip().lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")


def create_resilient_session() -> requests.Session:
    """Erstellt eine HTTP-Session mit TCP Keep-Alive und exponentiellem Retry-Backoff."""
    session = requests.Session()
    session.headers.update(HEADERS)

    retries = Retry(
        total=5,
        connect=5,
        read=5,
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


def create_zip_in_memory(directory_path: Path) -> io.BytesIO:
    """Erstellt ein ZIP-Archiv des Ordners im RAM für den direkten Streamlit-Download."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in directory_path.rglob("*.csv"):
            archive_name = file.relative_to(directory_path)
            zip_file.write(file, arcname=archive_name)
    zip_buffer.seek(0)
    return zip_buffer


# ==============================================================================
# STREAMLIT BENUTZEROBERFLÄCHE (IM LAG 21 NRW DESIGN)
# ==============================================================================

# Kopfbereich / Hero-Banner im LAG 21 Stil
st.markdown(
    """
    <div class="lag21-header">
        <span class="lag21-header-badge">Kommunale Nachhaltigkeit NRW</span>
        <h1>🏛️ Wegweiser Kommune / SDG-Portal Downloader</h1>
        <p>Automatisierter Datenabruf von Nachhaltigkeitsindikatoren über die REST-Schnittstelle der Bertelsmann Stiftung.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Initialisierung des Session-States
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "zip_data" not in st.session_state:
    st.session_state.zip_data = None

col1, col2 = st.columns([1, 1.8], gap="large")

with col1:
    with st.container(border=True):
        st.subheader("1. Parameter konfigurieren")

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
        out_dir_str = st.text_input("Zielordner (Server-Pfad):", value="./wegweiser_sdg_daten")
        out_base_dir = Path(out_dir_str)

        skip_existing_files = st.checkbox("Bereits heruntergeladene Dateien überspringen", value=True)

with col2:
    with st.container(border=True):
        st.subheader("2. Indikatoren auswählen")
        select_all_inds = st.checkbox("Alle Indikatoren auswählen", value=True)

        if select_all_inds:
            selected_ind_names = st.multiselect(
                "Aktive Nachhaltigkeitsindikatoren (SDG / Handlungsfelder):",
                options=list(ALL_INDICATORS.keys()),
                default=list(ALL_INDICATORS.keys())
            )
        else:
            selected_ind_names = st.multiselect(
                "Aktive Nachhaltigkeitsindikatoren (SDG / Handlungsfelder):",
                options=list(ALL_INDICATORS.keys()),
                default=["Steuereinnahmen", "Strom_aus_erneuerbaren_Quellen", "Naturschutzflaechen"]
            )

        # Kleine Info-Box zur aktuellen Auswahl
        total_planned = len(selected_communes) * len(selected_ind_names)
        st.info(
            f"**Auswahl-Zusammenfassung:** `{len(selected_communes)}` Gebiete × "
            f"`{len(selected_ind_names)}` Indikatoren = **{total_planned} CSV-Dateien**"
        )

st.write("")  # Kleiner vertikaler Abstand

# ==============================================================================
# DOWNLOAD-STEUERUNG & FORTSCHRITT
# ==============================================================================

btn_placeholder = st.empty()

if not st.session_state.is_running:
    if btn_placeholder.button("🚀 Datenabruf starten", type="primary"):
        if not selected_communes:
            st.error("Bitte mindestens eine Kommune auswählen!")
        elif not selected_ind_names:
            st.error("Bitte mindestens einen Indikator auswählen!")
        else:
            st.session_state.is_running = True
            st.session_state.zip_data = None
            st.rerun()
else:
    if btn_placeholder.button("🛑 Download abbrechen", type="secondary"):
        st.session_state.is_running = False
        st.warning("Download wurde abgebrochen.")
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
        st.warning(f"Abgebrochen! Es wurden {success_total} von {total_downloads} Dateien verarbeitet.")
    else:
        st.success(f"Fertig! {success_total}/{total_downloads} Dateien in {duration} Sekunden erfolgreich verarbeitet.")

    # ZIP-Archiv im Speicher vorbereiten
    st.session_state.zip_data = create_zip_in_memory(out_base_dir)

# Download-Bereich anzeigen, wenn Daten vorhanden sind
if st.session_state.zip_data is not None:
    with st.container(border=True):
        st.subheader("📦 Datenpaket herunterladen")
        st.markdown("Alle abgerufenen CSV-Dateien wurden strukturiert nach Kommunen in einem ZIP-Archiv gebündelt.")
        st.download_button(
            label="📥 Alle CSV-Dateien als ZIP herunterladen",
            data=st.session_state.zip_data,
            file_name="wegweiser_sdg_daten_lag21.zip",
            mime="application/zip",
            type="primary"
        )
