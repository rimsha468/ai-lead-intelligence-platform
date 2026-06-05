import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

from scraper import LeadScraper
from database import init_db, insert_leads


# ----------------------------
# INIT
# ----------------------------
init_db()

st.set_page_config(
    page_title="LeadAtlas AI",
    layout="wide"
)


# ----------------------------
# SIDEBAR STYLE (LIGHT BLUE)
# ----------------------------
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background-color: #C9EBFF;
}

section[data-testid="stSidebar"] * {
    color: #0f172a !important;
    font-family: "Segoe UI", sans-serif;
}
</style>
""", unsafe_allow_html=True)


# ----------------------------
# HEADER
# ----------------------------
st.markdown("""
# 🧠 LeadAtlas AI  
### <span style='color:gray'>Geospatial Lead Intelligence & CRM Dashboard</span>
""", unsafe_allow_html=True)

st.markdown("---")


# ----------------------------
# LOAD DATA
# ----------------------------
@st.cache_data
def load_cities():
    return pd.read_csv("worldcities.csv")


df = load_cities()


# ----------------------------
# INDUSTRIES (FULL LIST)
# ----------------------------
INDUSTRIES = [
    "restaurant", "cafe", "fast_food", "bakery", "hotel",
    "supermarket", "convenience_store", "clothing_store",
    "leather_goods", "shoe_store", "electronics_store",
    "furniture_store", "bookstore", "jewelry_store",
    "dentist", "clinic", "hospital", "pharmacy", "veterinary",
    "gym", "school", "college", "university",
    "bank", "atm",
    "car_dealer", "car_repair", "gas_station",
    "church", "mosque"
]


def format_industry(name):
    return name.replace("_", " ").title()


industry_map = {i: format_industry(i) for i in INDUSTRIES}


# ----------------------------
# SIDEBAR CONTROLS
# ----------------------------
st.sidebar.title("Lead Panel")

industry = st.sidebar.selectbox(
    "Industry",
    options=INDUSTRIES,
    format_func=lambda x: industry_map[x]
)

city_names = df["city"] + ", " + df["country"]

selected_city_name = st.sidebar.selectbox(
    "City",
    options=city_names,
    index=None,
    placeholder="Search city..."
)

score_filter = st.sidebar.slider("Min Score", 0, 100, 0)


# ----------------------------
# SCRAPER
# ----------------------------
scraper = LeadScraper()


# ----------------------------
# SCORING
# ----------------------------
def score_lead(l):
    score = 0
    if l.get("website"): score += 25
    if l.get("phone"): score += 20
    if l.get("email"): score += 25
    if l.get("address"): score += 10
    if l.get("name"): score += 5
    return min(score, 100)


def apply_scoring(leads):
    for l in leads:
        l["score"] = score_lead(l)
    return leads


# ----------------------------
# COMPLETENESS SCORE (IMPORTANT FOR SORTING)
# ----------------------------
def completeness_score(l):
    return sum([
        1 if l.get("name") else 0,
        1 if l.get("phone") else 0,
        1 if l.get("email") else 0,
        1 if l.get("address") else 0
    ])


# ----------------------------
# SESSION STATE
# ----------------------------
if "leads" not in st.session_state:
    st.session_state.leads = []


# ----------------------------
# GENERATE LEADS
# ----------------------------
if st.sidebar.button("🚀 Generate Leads"):

    if not selected_city_name:
        st.warning("Please select a city first")
        st.stop()

    city_row = df[(df["city"] + ", " + df["country"]) == selected_city_name].iloc[0]

    lat = city_row["lat"]
    lon = city_row["lng"]

    raw = scraper.search(industry, (lat, lon))

    # ----------------------------
    # DEDUPLICATION
    # ----------------------------
    seen = set()
    results = []

    for r in raw:
        key = (r.get("name"), r.get("lat"), r.get("lon"))
        if key not in seen:
            seen.add(key)
            results.append(r)

    # ----------------------------
    # SCORING
    # ----------------------------
    results = apply_scoring(results)

    # filter by score slider
    results = [r for r in results if r.get("score", 0) >= score_filter]

    insert_leads(industry, results)

    # ----------------------------
    # SORTING (CRITICAL FIX YOU WANTED)
    # ----------------------------
    results.sort(
        key=lambda x: (
            completeness_score(x),   # 4 → 3 → 2 → 1 → 0 fields first
            x.get("score", 0)        # then score
        ),
        reverse=True
    )

    st.session_state.leads = results


# ----------------------------
# DATA
# ----------------------------
leads = st.session_state.leads
filtered = [l for l in leads if l.get("score", 0) >= score_filter]


# ----------------------------
# METRICS
# ----------------------------
if leads:

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Leads", len(leads))

    col2.metric(
        "High Quality (60+)",
        len([l for l in leads if l.get("score", 0) >= 60])
    )

    avg_score = round(
        sum(l.get("score", 0) for l in leads) / len(leads),
        1
    )

    col3.metric("Avg Score", avg_score)


st.markdown("---")


# ----------------------------
# TABLE
# ----------------------------
st.markdown("### Lead Database")

df_out = pd.DataFrame(filtered)

columns = ["name", "phone", "email", "address", "website", "score"]

for c in columns:
    if c not in df_out.columns:
        df_out[c] = None

df_out = df_out[columns]

st.dataframe(df_out, use_container_width=True)


# ----------------------------
# MAP
# ----------------------------
st.markdown("### Lead Map")

if filtered:

    m = folium.Map(
        location=[filtered[0]["lat"], filtered[0]["lon"]],
        zoom_start=12
    )

    for l in filtered[:100]:
        if l.get("lat") and l.get("lon"):

            color = "green" if completeness_score(l) == 4 else "red"

            folium.Marker(
                location=[l["lat"], l["lon"]],
                popup=f"{l['name']} | Score: {l.get('score',0)}",
                icon=folium.Icon(color=color)
            ).add_to(m)

    st_folium(m, width=900, height=500)

else:
    st.info("Generate leads to view dashboard")

st.markdown("""
<style>
[data-testid="collapsedControl"] {
    font-size: 0 !important;
}

[data-testid="collapsedControl"]::before {
    content: "☰";
    font-size: 20px;
}
</style>
""", unsafe_allow_html=True)
