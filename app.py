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
# CLEAN CRM STYLE HEADER
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
# SIDEBAR CONTROLS
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
    placeholder="Type city name..."
)

score_filter = st.sidebar.slider("Minimum Score", 0, 100, 0)


# ----------------------------
# SCRAPER
# ----------------------------
scraper = LeadScraper()


# ----------------------------
# SCORING SYSTEM
# ----------------------------
def score_lead(l):
    score = 0
    if l.get("website"): score += 25
    if l.get("phone"): score += 20
    if l.get("email"): score += 25
    if l.get("address"): score += 10
    return min(score, 100)


def apply_scoring(leads):
    for l in leads:
        l["score"] = score_lead(l)
    return leads


# ----------------------------
# SESSION STATE
# ----------------------------
if "leads" not in st.session_state:
    st.session_state.leads = []


# ----------------------------
# GENERATE BUTTON
# ----------------------------
if st.sidebar.button("🚀 Generate Leads"):

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

    # filter
    results = [r for r in results if r.get("score", 0) >= score_filter]

    insert_leads(industry, results)

    st.session_state.leads = results


# ----------------------------
# DATA
# ----------------------------
leads = st.session_state.leads


# ----------------------------
# FILTERED LEADS
# ----------------------------
filtered = [l for l in leads if l.get("score", 0) >= score_filter]


# ----------------------------
# METRICS (SAAS CARDS)
# ----------------------------
if filtered:

    col1, col2, col3 = st.columns(3)

    col1.markdown(f"""
    <div style="background:white;padding:15px;border-radius:12px;
    box-shadow:0 2px 10px rgba(0,0,0,0.05);text-align:center;">
    <h4>📦 Total Leads</h4>
    <h2 style="color:#4f46e5">{len(filtered)}</h2>
    </div>
    """, unsafe_allow_html=True)

    col2.markdown(f"""
    <div style="background:white;padding:15px;border-radius:12px;
    box-shadow:0 2px 10px rgba(0,0,0,0.05);text-align:center;">
    <h4>🔥 High Quality</h4>
    <h2 style="color:#16a34a">{len([l for l in filtered if l.get('score',0)>=70])}</h2>
    </div>
    """, unsafe_allow_html=True)

    avg = round(sum(l.get("score",0) for l in filtered)/len(filtered),1)

    col3.markdown(f"""
    <div style="background:white;padding:15px;border-radius:12px;
    box-shadow:0 2px 10px rgba(0,0,0,0.05);text-align:center;">
    <h4>📊 Avg Score</h4>
    <h2 style="color:#f59e0b">{avg}</h2>
    </div>
    """, unsafe_allow_html=True)


st.markdown("---")


# ----------------------------
# TABLE
# ----------------------------
st.markdown("### 📋 Lead Database")

df_out = pd.DataFrame(filtered)

cols = ["name", "website", "phone", "email", "address", "score"]

for c in cols:
    if c not in df_out.columns:
        df_out[c] = None

df_out = df_out[cols]

st.dataframe(df_out, use_container_width=True)


# ----------------------------
# MAP
# ----------------------------
st.markdown("### 🗺️ Lead Map")

if filtered:

    m = folium.Map(
        location=[filtered[0]["lat"], filtered[0]["lon"]],
        zoom_start=12
    )

    for l in filtered[:500]:  # performance safe limit
        if l.get("lat") and l.get("lon"):

            color = "green" if l.get("score", 0) > 70 else "red"

            folium.Marker(
                location=[l["lat"], l["lon"]],
                popup=f"{l['name']} | Score: {l.get('score',0)}",
                icon=folium.Icon(color=color)
            ).add_to(m)

    st_folium(m, width=900, height=500)

else:
    st.info("Generate leads to view CRM dashboard")
