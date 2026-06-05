import streamlit as st
import pandas as pd
import threading
import folium
from streamlit_folium import st_folium

from scraper import LeadScraper
from enricher_wikidata import WikidataEnricher
from database import init_db, insert_leads, get_project_leads


# ----------------------------
# INIT DB
# ----------------------------
init_db()


# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="🌸 AI Lead Intelligence Platform",
    layout="wide"
)


# ----------------------------
# 🌸 CUTE UI THEME
# ----------------------------
st.markdown("""
<style>

/* background */
body {
    background-color: #fff7fb;
}

/* main title */
h1 {
    color: #ff4da6;
    text-align: center;
}

/* buttons */
.stButton>button {
    background-color: #ff66b2;
    color: white;
    border-radius: 12px;
    height: 3em;
    font-size: 16px;
}

/* dataframe */
div[data-testid="stDataFrame"] {
    border-radius: 12px;
}

/* sidebar */
section[data-testid="stSidebar"] {
    background-color: #ffe6f2;
}

</style>
""", unsafe_allow_html=True)


# ----------------------------
# TITLE
# ----------------------------
st.title("🌸 AI Lead Intelligence Platform")
st.write("Find, analyze, and visualize real-world business leads ✨")


# ----------------------------
# LOAD DATA
# ----------------------------
@st.cache_data
def load_cities():
    return pd.read_csv("worldcities.csv")


df = load_cities()


# ----------------------------
# INDUSTRIES
# ----------------------------
INDUSTRIES = [
    "restaurant", "cafe", "fast_food", "bakery", "hotel",
    "supermarket", "convenience_store", "clothing_store",
    "dentist", "clinic", "hospital", "pharmacy",
    "gym", "school", "college", "university",
    "bank", "atm",
    "car_dealer", "car_repair", "gas_station"
]

industry = st.selectbox("🌸 Select Industry", INDUSTRIES)


# ----------------------------
# 🌍 SMART CITY SEARCH (AUTOCOMPLETE STYLE)
# ----------------------------
city_names = df["city"] + ", " + df["country"]

selected_city_name = st.selectbox(
    "🌍 Search City (type to filter)",
    options=city_names,
    index=None,
    placeholder="Start typing city name..."
)

selected_city = None

if selected_city_name:
    selected_city = df[
        (df["city"] + ", " + df["country"]) == selected_city_name
    ].iloc[0]


# ----------------------------
# INIT CLASSES
# ----------------------------
scraper = LeadScraper()
wikidata = WikidataEnricher()


# ----------------------------
# SCORING FUNCTION
# ----------------------------
def score_lead(lead):
    score = 0

    if lead.get("website"):
        score += 25
    if lead.get("phone"):
        score += 20
    if lead.get("email"):
        score += 25
    if lead.get("address"):
        score += 10
    if lead.get("name"):
        score += 5

    return min(score, 100)


def apply_scoring(leads):
    for lead in leads:
        lead["score"] = score_lead(lead)
    return leads


# ----------------------------
# MAP FUNCTION
# ----------------------------
def create_map(leads):

    if not leads:
        return None

    m = folium.Map(
        location=[leads[0]["lat"], leads[0]["lon"]],
        zoom_start=12
    )

    for lead in leads:
        if lead.get("lat") and lead.get("lon"):

            color = "red" if lead.get("score", 0) > 70 else "blue"

            folium.Marker(
                location=[lead["lat"], lead["lon"]],
                popup=f"{lead['name']} (Score: {lead.get('score',0)})",
                tooltip=lead["name"],
                icon=folium.Icon(color=color)
            ).add_to(m)

    return m


# ----------------------------
# SESSION STATE
# ----------------------------
if "results" not in st.session_state:
    st.session_state.results = []

if "enriching" not in st.session_state:
    st.session_state.enriching = False


# ----------------------------
# BACKGROUND ENRICHMENT
# ----------------------------
def enrich_worker(leads, wikidata):

    for lead in leads:
        enriched = wikidata.enrich(lead)
        lead.update(enriched)
        lead["score"] = score_lead(lead)

        st.session_state.results = leads

    st.session_state.enriching = False


# ----------------------------
# GENERATE BUTTON
# ----------------------------
if st.button("🚀 Generate Leads"):

    if not selected_city_name:
        st.warning("Please select a city 🌍")
        st.stop()

    lat = selected_city["lat"]
    lon = selected_city["lng"]

    st.info("Fetching beautiful leads ✨")

    raw = scraper.search(industry, (lat, lon))

    # dedupe
    seen = set()
    results = []

    for r in raw:
        key = (r.get("name"), r.get("lat"), r.get("lon"))
        if key not in seen:
            seen.add(key)
            results.append(r)

    # scoring
    results = apply_scoring(results)

    # save to DB (default project)
    insert_leads(f"{industry.title()} Leads", results)

    st.session_state.results = results

    # enrichment
    st.session_state.enriching = True

    thread = threading.Thread(
        target=enrich_worker,
        args=(results, wikidata),
        daemon=True
    )
    thread.start()


# ----------------------------
# LOAD FROM DATABASE (PROJECT STYLE)
# ----------------------------
if selected_city_name:
    st.session_state.results = st.session_state.results


# ----------------------------
# RESULTS SECTION
# ----------------------------
if st.session_state.results:

    st.subheader("🏆 Leads")

    df_out = pd.DataFrame(st.session_state.results)

    preferred_cols = [
        "name", "website", "phone", "email",
        "address", "score", "lat", "lon"
    ]

    df_out = df_out[[c for c in preferred_cols if c in df_out.columns]]

    st.dataframe(df_out, use_container_width=True)

    # ----------------------------
    # DOWNLOAD
    # ----------------------------
    csv = df_out.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇ Download CSV",
        csv,
        "leads.csv",
        "text/csv"
    )

    # ----------------------------
    # MAP
    # ----------------------------
    st.subheader("🗺️ Map View")

    map_obj = create_map(st.session_state.results)

    if map_obj:
        st_folium(map_obj, width=900, height=500)

else:
    st.info("🌸 Start by selecting industry + city and generate leads")