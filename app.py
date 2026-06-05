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
# HEADER
# ----------------------------
st.markdown("""
# 🧠 LeadAtlas AI  
### <span style='color:gray'>Geospatial Lead Intelligence & CRM Dashboard</span>
""", unsafe_allow_html=True)

st.markdown("---")


# ----------------------------
# LOAD CITIES
# ----------------------------
@st.cache_data
def load_cities():
    return pd.read_csv("worldcities.csv")


df = load_cities()


# ----------------------------
# SIDEBAR
# ----------------------------
st.sidebar.title("⚙️ CRM Controls")

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
    placeholder="Type city..."
)

score_filter = st.sidebar.slider("Minimum Score", 0, 100, 0)


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
# SMART COMPLETENESS SCORE
# ----------------------------
def completeness_score(l):
    score = 0
    if l.get("name"): score += 2
    if l.get("phone"): score += 2
    if l.get("email"): score += 2
    if l.get("address"): score += 2
    if l.get("website"): score += 2
    return score


# ----------------------------
# SESSION STATE
# ----------------------------
if "leads" not in st.session_state:
    st.session_state.leads = []

if "page" not in st.session_state:
    st.session_state.page = 1


PAGE_SIZE = 100


# ----------------------------
# GENERATE LEADS
# ----------------------------
if st.sidebar.button("🚀 Generate Leads"):

    if not selected_city_name:
        st.warning("Select a city first")
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

    # filter score
    results = [r for r in results if r.get("score", 0) >= score_filter]

    insert_leads(industry, results)

    # ----------------------------
    # SORTING (IMPORTANT FIX)
    # ----------------------------
    results.sort(
        key=lambda x: (x.get("score", 0), completeness_score(x)),
        reverse=True
    )

    st.session_state.leads = results
    st.session_state.page = 1


# ----------------------------
# DATA
# ----------------------------
leads = st.session_state.leads

filtered = [l for l in leads if l.get("score", 0) >= score_filter]


# ----------------------------
# SMART PAGINATION (ONLY 100 INITIALLY)
# ----------------------------
start = 0
end = st.session_state.page * PAGE_SIZE

paged_leads = filtered[start:end]


# ----------------------------
# LOAD MORE BUTTON
# ----------------------------
if len(filtered) > end:
    if st.button("⬇ Load More"):
        st.session_state.page += 1
        st.rerun()


# ----------------------------
# METRICS
# ----------------------------
if paged_leads:

    col1, col2, col3 = st.columns(3)

    col1.metric("📦 Loaded", len(paged_leads))
    col2.metric("🔥 High Quality", len([l for l in paged_leads if l.get("score",0)>=70]))

    avg = round(sum(l.get("score",0) for l in paged_leads)/len(paged_leads),1)
    col3.metric("📊 Avg Score", avg)


st.markdown("---")


# ----------------------------
# TABLE (ORDERED FIELDS FIRST)
# ----------------------------
st.markdown("### 📋 Lead Database")

df_out = pd.DataFrame(paged_leads)

columns = [
    "name",
    "phone",
    "email",
    "address",
    "website",
    "score",
    "lat",
    "lon"
]

for c in columns:
    if c not in df_out.columns:
        df_out[c] = None

df_out = df_out[columns]

st.dataframe(df_out, use_container_width=True)


# ----------------------------
# MAP (LIMITED FOR PERFORMANCE)
# ----------------------------
st.markdown("### 🗺️ Lead Map")

if paged_leads:

    m = folium.Map(
        location=[paged_leads[0]["lat"], paged_leads[0]["lon"]],
        zoom_start=12
    )

    for l in paged_leads[:100]:  # SAFE LIMIT FOR MAP
        if l.get("lat") and l.get("lon"):

            color = "green" if l.get("score", 0) > 70 else "red"

            folium.Marker(
                location=[l["lat"], l["lon"]],
                popup=f"{l['name']} | Score: {l.get('score',0)}",
                icon=folium.Icon(color=color)
            ).add_to(m)

    st_folium(m, width=900, height=500)

else:
    st.info("Generate leads to view dashboard")
