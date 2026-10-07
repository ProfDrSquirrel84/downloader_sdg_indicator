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
    "wuerselen", "monheim-am-rhein",
    "frechen", "kleve", "hattingen", "dormagen",
    "ratingen", "remscheid", "herne", "solingen", "hagen",
    "euskirchen", "bonn", "bielefeld", "wuppertal"
]

ALL_INDICATORS = {
    # Steuerung
    "Steuereinnahmen": "steuereinnahmen-pro-einwohner-in",
    "Finanzmittelsaldo": "finanzmittelsaldo",
    "Liquiditaetskredite": "liquiditaetskredite",
    "Breitbandversorgung_Haushalte": "breitbandversorgung-private-haushalte",
    # Handlungsfeld 10: Klimaschutz & Energie
    "Strom_aus_erneuerbaren_Quellen": "strom-aus-erneuerbaren-quellen",
    # Handlungsfeld 11: Ressourcenschutz & Klimafolgenanpassung
    "Naturschutzflaechen": "naturschutzflaechen",
    "Siedlungslast_Ueberschwemmungsgebiet": "siedlungslast-im-ueberschwemmungsgebiet",
    "Landschaftsqualitaet": "landschaftsqualitaet",
    "Abwasserbehandlung": "abwasserbehandlung",
    # Handlungsfeld 12: Nachhaltige Mobilität
    "Ladesaeuleninfrastruktur": "ladesaeuleninfrastruktur",
    "Verunglueckte_im_Verkehr": "verunglueckte-im-verkehr",
    # Handlungsfeld 13: Lebenslanges Lernen & Kultur
    "U3_in_Tageseinrichtungen": "unter-3-jaehrige-in-tageseinrichtungen",
    "Schulabgaenger_ohne_Hauptschulabschluss": "schulabgaenger-ohne-hauptschulabschluss-gesamt",
    "Wohnungsnahe_Grundschule": "wohnungsnahe-grundversorgung-grundschule",
    # Handlungsfeld 14: Soziale Gerechtigkeit
    "Kinderarmut": "kinderarmut",
    "Jugendarmut": "jugendarmut",
    "Altersarmut": "altersarmut",
    "Verhaeltnis_Beschaeftigung_Frauen_Maenner": "verhaeltnis-der-beschaeftigungsquote-von-frauen-und-maennern",
    "SGB_II_XII_Quote": "sgb-ii-sgb-xii-quote",
    "Einbuergerungen": "eingebuergerte-im-jahr",
    # Handlungsfeld 15: Wohnen & nachhaltige Quartiere
    "Naherholungsflaechen": "naherholungsflaechen",
    "Wohnflaeche": "wohnflaeche-pro-person",
    "Wohngebaeude_erneuerbare_Heizenergie": "fertiggestellte-wohngebaeude-mit-erneuerbarer-energie",
    "Flaecheninanspruchnahme": "flaecheninanspruchnahme",
    "Flaechennutzungsintensitaet": "flaechennutzungsintensitaet",
    # Handlungsfeld 16: Gute Arbeit & Wirtschaft
    "Beschaeftigungsquote": "beschaeftigungsquote",
    "Erwerbstaetige_Aufstockende": "aufstocker-gesamt",
    "Hochqualifizierte_am_Arbeitsort": "hochqualifizierte-am-arbeitsort",
    "Langzeitarbeitslosenquote": "langzeitarbeitslosenquote",
    "Existenzgruendungen": "existenzgruendungen",
    # Handlungsfeld 17: Konsum & Gesundheit
    "Luftschadstoffbelastung": "luftschadstoffbelastung",
    "Vorzeitige_Sterblichkeit": "vorzeitige-sterblichkeit-gesamt",
    "Wohnungsnahe_Apotheke": "wohnungsnahe-grundversorgung-apotheke",
    "Wohnungsnaher_Hausarzt": "wohnungsnahe-grundversorgung-hausarzt",
    "Wohnungsnahes_Krankenhaus": "wohnungsnahe-grundversorgung-krankenhaus",
    "Wohnungsnaher_Supermarkt": "wohnungsnahe-grundversorgung-supermarkt",
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
            
            # Text sauber als UTF-8 dekodieren und mit UTF-8-BOM speichern (für Excel & Co.)
            text_content = res.content.decode("utf-8", errors="replace")
            with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(text_content)
                
            kb = round(output_path.stat().st_size / 1024, 1)
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
# STREAMLIT BENUTZEROBERFLÄCHE
# ==============================================================================

st.set_page_config(page_title="Wegweiser Kommune Downloader", layout="wide")

st.title("🏛️ Wegweiser Kommune / SDG-Portal Downloader")
st.markdown("Automatisierter Datenabruf über die REST-Schnittstelle der Bertelsmann Stiftung.")

# Initialisierung des Session-States
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "zip_data" not in st.session_state:
    st.session_state.zip_data = None

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Parameter konfigurieren")

    select_all_communes = st.checkbox("Alle 38 Kommunen auswählen", value=True)
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
            st.caption(f"Hinzugefügt als Slug: `{custom_slug}`")

    if include_nrw and "nordrhein-westfalen" not in selected_communes:
        selected_communes.append("nordrhein-westfalen")

    time_period = st.text_input("Zeitraum (z. B. '2016-2023'):", value="2016-2023")
    out_dir_str = st.text_input("Zielordner (Server-Pfad):", value="./wegweiser_sdg_daten")
    out_base_dir = Path(out_dir_str)

    skip_existing_files = st.checkbox("Bereits heruntergeladene Dateien überspringen", value=True)

with col2:
    st.subheader("2. Indikatoren auswählen")
    select_all_inds = st.checkbox("Alle Indikatoren auswählen", value=True)

    if select_all_inds:
        selected_ind_names = st.multiselect(
            "Aktive Indikatoren:",
            options=list(ALL_INDICATORS.keys()),
            default=list(ALL_INDICATORS.keys())
        )
    else:
        selected_ind_names = st.multiselect(
            "Aktive Indikatoren:",
            options=list(ALL_INDICATORS.keys()),
            default=["Steuereinnahmen", "Strom_aus_erneuerbaren_Quellen", "Naturschutzflaechen"]
        )

st.markdown("---")

btn_placeholder = st.empty()

if not st.session_state.is_running:
    if btn_placeholder.button("🚀 Download starten", type="primary"):
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

    progress_bar = st.progress(0.0)
    status_text = st.empty()
    log_box = st.container(height=350)

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
            st.markdown(f"**Verarbeite:** `{commune}`")

        for ind_name in selected_ind_names:
            if not st.session_state.is_running:
                aborted = True
                break

            ind_slug = ALL_INDICATORS[ind_name]
            current_step += 1

            status_text.text(f"Lade ({current_step}/{total_downloads}): {commune} -> {ind_name}...")

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
        st.success(f"Fertig! {success_total}/{total_downloads} Dateien in {duration} Sekunden verarbeitet.")

    # ZIP-Archiv im Speicher vorbereiten
    st.session_state.zip_data = create_zip_in_memory(out_base_dir)

# Download-Bereich anzeigen, wenn Daten vorhanden sind
if st.session_state.zip_data is not None:
    st.subheader("📦 Daten herunterladen")
    st.download_button(
        label="📥 Alle CSV-Dateien als ZIP herunterladen",
        data=st.session_state.zip_data,
        file_name="wegweiser_sdg_daten.zip",
        mime="application/zip",
        type="primary"
    )
