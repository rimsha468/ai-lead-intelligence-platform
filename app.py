import streamlit as st
import pandas as pd
import threading
import folium
from streamlit_folium import st_folium

from scraper import LeadScraper
from enricher_wikidata import WikidataEnricher
from database import init_db, insert_leads


# ----------------------------
# INIT DB
# ----------------------------
init_db()


# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="AI Lead Intelligence Platform",
    layout="wide"
)


# ----------------------------
# CLEAN UI THEME (LIGHT SAAS STYLE)
# ----------------------------
st.markdown("""
<style>
body {
    background-color: #f7f9fc;
}

h1, h2, h3 {
    color: #2d2d2d;
}

.block-container {
    padding-top: 2rem;
}

/* buttons */
.stButton>button {
    background-color: #4f46e5;
    color: white;
    border-radius: 10px;
    padding: 0.5rem 1rem;
    font-weight: 500;
}

/* metric cards */
div[data-testid="stMetric"] {
    background-color: white;
    border-radius: 12px;
    padding: 10px;
    box-shadow: 0px 2px 10px rgba(0,0,0,0.05);
}

</style>
""", unsafe_allow_html=True)


# ----------------------------
# TITLE
# ----------------------------
st.title("AI Lead Intelligence Platform")
st.caption("Discover, enrich and analyze real-world business leads")


# ----------------------------
# LOAD DATA
# ----------------------------
@st.cache_data
def load_cities():
    return pd.read_csv("worldcities.csv")


df = load_cities()


# ----------------------------
# SIDEBAR (CLEAN CONTROL PANEL)
# ----------------------------
st.sidebar.header("Search Controls")

INDUSTRIES = [
    "restaurant", "cafe", "fast_food", "bakery", "hotel",
    "dentist", "clinic", "hospital", "pharmacy",
    "gym", "school", "college", "university",
    "bank", "atm",
    "car_dealer", "car_repair", "gas_station"
]

industry = st.sidebar.selectbox("Industry", INDUSTRIES)

city_names = df["city"] + ", " + df["country"]

selected_city_name = st.sidebar.selectbox(
    "City",
    options=city_names,
    index=None,
    placeholder="Type to search..."
)


# ----------------------------
# INIT CLASSES
# ----------------------------
scraper = LeadScraper()
wikidata = WikidataEnricher()


# ----------------------------
# SCORING
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

    return min(score, 100)


def apply_scoring(leads):
    for l in leads:
        l["score"] = score_lead(l)
    return leads


# ----------------------------
# MAP
# ----------------------------
def create_map(leads):
    if not leads:
        return None

    m = folium.Map(location=[leads[0]["lat"], leads[0]["lon"]], zoom_start=12)

    for l in leads:
        if l.get("lat") and l.get("lon"):

            color = "green" if l.get("score", 0) > 70 else "red"

            folium.Marker(
                location=[l["lat"], l["lon"]],
                popup=f"{l['name']} | Score: {l.get('score',0)}",
                icon=folium.Icon(color=color)
            ).add_to(m)

    return m


# ----------------------------
# SESSION STATE
# ----------------------------
if "results" not in st.session_state:
    st.session_state.results = []


# ----------------------------
# GENERATE
# ----------------------------
if st.sidebar.button("Generate Leads"):

    if not selected_city_name:
        st.warning("Select a city")
        st.stop()

    city_row = df[(df["city"] + ", " + df["country"]) == selected_city_name].iloc[0]

    lat = city_row["lat"]
    lon = city_row["lng"]

    raw = scraper.search(industry, (lat, lon))

    # dedupe
    seen = set()
    results = []

    for r in raw:
        key = (r.get("name"), r.get("lat"), r.get("lon"))
        if key not in seen:
            seen.add(key)
            results.append(r)

    results = apply_scoring(results)

    insert_leads(industry, results)

    st.session_state.results = results


# ----------------------------
# DASHBOARD METRICS
# ----------------------------
if st.session_state.results:

    leads = st.session_state.results

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Leads", len(leads))
    col2.metric("High Score", len([l for l in leads if l.get("score",0) > 70]))
    col3.metric("Avg Score",
                round(sum(l.get("score",0) for l in leads)/len(leads),1)
                if leads else 0)

    st.divider()

    # ----------------------------
    # TABLE
    # ----------------------------
    st.subheader("Lead Results")

    df_out = pd.DataFrame(leads)[
        ["name", "website", "phone", "email", "address", "score"]
    ]

    st.dataframe(df_out, use_container_width=True)

    # ----------------------------
    # MAP
    # ----------------------------
    st.subheader("Map View")

    map_obj = create_map(leads)

    if map_obj:
        st_folium(map_obj, width=900, height=500)

else:
    st.info("Generate leads to view dashboard")
