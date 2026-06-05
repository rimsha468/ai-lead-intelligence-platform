import streamlit as st
import pandas as pd
import threading
import folium
from streamlit_folium import st_folium

from scraper import LeadScraper
from enricher_wikidata import WikidataEnricher
from database import init_db, insert_leads


# ----------------------------
# INIT
# ----------------------------
init_db()


# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="AI Lead CRM Dashboard",
    layout="wide"
)


# ----------------------------
# CLEAN CRM STYLE UI
# ----------------------------
st.markdown("""
<style>

body {
    background-color: #f6f7fb;
}

/* Title */
h1 {
    color: #111827;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e5e7eb;
}

/* Buttons */
.stButton>button {
    background-color: #4f46e5;
    color: white;
    border-radius: 10px;
    padding: 0.5rem 1rem;
    font-weight: 500;
}

/* DataFrame */
div[data-testid="stDataFrame"] {
    border-radius: 12px;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background-color: white;
    padding: 10px;
    border-radius: 12px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.08);
}

</style>
""", unsafe_allow_html=True)


# ----------------------------
# TITLE
# ----------------------------
st.title("🧠 AI Lead CRM Dashboard")
st.caption("Discover, score, and manage business leads like a CRM system")


# ----------------------------
# LOAD DATA
# ----------------------------
@st.cache_data
def load_cities():
    return pd.read_csv("worldcities.csv")


df = load_cities()


# ----------------------------
# SIDEBAR (CRM CONTROLS)
# ----------------------------
st.sidebar.header("CRM Controls")

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
    "City Search",
    options=city_names,
    index=None,
    placeholder="Type city name..."
)

score_filter = st.sidebar.slider("Minimum Lead Score", 0, 100, 0)


# ----------------------------
# INIT SERVICES
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
    if lead.get("name"):
        score += 5

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

            color = "green" if l.get("score", 0) >= 70 else "red"

            folium.Marker(
                location=[l["lat"], l["lon"]],
                popup=f"{l['name']} | Score: {l.get('score',0)}",
                icon=folium.Icon(color=color)
            ).add_to(m)

    return m


# ----------------------------
# SESSION STATE
# ----------------------------
if "leads" not in st.session_state:
    st.session_state.leads = []


# ----------------------------
# GENERATE LEADS
# ----------------------------
if st.sidebar.button("Generate Leads"):

    if not selected_city_name:
        st.warning("Please select a city")
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

    st.session_state.leads = results


# ----------------------------
# FILTER LEADS (CRM CORE)
# ----------------------------
leads = st.session_state.leads

filtered_leads = [
    l for l in leads
    if l.get("score", 0) >= score_filter
]


# ----------------------------
# DASHBOARD METRICS
# ----------------------------
if filtered_leads:

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Leads", len(filtered_leads))
    col2.metric("High Quality", len([l for l in filtered_leads if l.get("score",0) >= 70]))
    col3.metric("Avg Score",
                round(sum(l.get("score",0) for l in filtered_leads)/len(filtered_leads),1))

    st.divider()


    # ----------------------------
    # CRM TABLE SAFE FIX
    # ----------------------------
    df_out = pd.DataFrame(filtered_leads)

    columns = ["name", "website", "phone", "email", "address", "score"]

    for c in columns:
        if c not in df_out.columns:
            df_out[c] = None

    df_out = df_out[columns]


    st.subheader("📋 Leads Database (CRM View)")
    st.dataframe(df_out, use_container_width=True)


    # ----------------------------
    # LEAD DETAIL VIEW (CRM STYLE)
    # ----------------------------
    st.subheader("🔎 Lead Inspector")

    selected = st.selectbox(
        "Select a lead to view details",
        df_out["name"].tolist()
    )

    lead = next((l for l in filtered_leads if l["name"] == selected), None)

    if lead:
        st.json(lead)


    # ----------------------------
    # MAP VIEW
    # ----------------------------
    st.subheader("🗺️ Map View")

    map_obj = create_map(filtered_leads)

    if map_obj:
        st_folium(map_obj, width=900, height=500)

else:
    st.info("No leads match the selected filter. Generate leads first.")
