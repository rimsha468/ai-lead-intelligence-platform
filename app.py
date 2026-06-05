import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

from scraper import LeadScraper
from database import init_db, insert_leads



import streamlit as st
from streamlit_extras.let_it_rain import rain
import time

st.set_page_config(
    page_title="LeadAtlas AI",
    layout="wide"
)

# ----------------------------
# SESSION STATE
# ----------------------------
if "started" not in st.session_state:
    st.session_state.started = False


# ----------------------------
# START SCREEN LOGIC
# ----------------------------
if not st.session_state.started:

    # 🌈 Gradient Background
    st.markdown("""
    <style>
    .hero {
        text-align: center;
        padding: 80px 20px;
        background: linear-gradient(135deg, #f8fafc, #eef2ff);
        border-radius: 20px;
        margin-bottom: 30px;
    }

    .logo {
        font-size: 18px;
        font-weight: 600;
        color: #4f46e5;
        letter-spacing: 2px;
    }

    .title {
        font-size: 54px;
        font-weight: 800;
        margin-bottom: 10px;
        color: #111827;
    }

    .subtitle {
        font-size: 20px;
        color: #6b7280;
    }

    </style>
    """, unsafe_allow_html=True)


    # ----------------------------
    # BRAND BLOCK
    # ----------------------------
    st.markdown("""
    <div class="hero">
        <div class="logo">🌍 LEADATLAS AI</div>
        <div class="title">Intelligent Lead Discovery System</div>
        <div class="subtitle">Geospatial AI + CRM + Data Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)


    # ----------------------------
    # ANIMATED TYPING TAGLINE
    # ----------------------------
    tagline = [
        "Discover real-world business leads...",
        "Enrich data using AI intelligence...",
        "Score and prioritize opportunities...",
        "Manage leads like a modern CRM..."
    ]

    placeholder = st.empty()

    for text in tagline:
        placeholder.markdown(f"### ✨ {text}")
        time.sleep(1.2)

    st.markdown("---")


    # ----------------------------
    # FEATURE BLOCKS
    # ----------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🧠 AI Lead Scoring")
        st.write("Automatically rank business opportunities using smart signals.")

    with col2:
        st.markdown("### 🌍 Geo Intelligence")
        st.write("Extract and visualize real-world businesses globally.")

    with col3:
        st.markdown("### 📊 CRM Dashboard")
        st.write("Filter, search, and manage leads like a SaaS platform.")


    st.markdown("---")


    # ----------------------------
    # ENTER BUTTON
    # ----------------------------
    if st.button("🚀 Launch LeadAtlas AI"):
        st.session_state.started = True
        st.rerun()

    st.stop()


# ----------------------------
# INIT
# ----------------------------
init_db()

st.title("LeadAtlas AI")
st.markdown(
    "<p style='font-size:18px; color:gray;'>AI-powered geospatial lead intelligence & CRM system</p>",
    unsafe_allow_html=True
)


# ----------------------------
# CLEAN UI
# ----------------------------
st.markdown("""
<style>
body { background-color: #f6f7fb; }

h1 { color: #111827; }

.stButton>button {
    background-color: #4f46e5;
    color: white;
    border-radius: 10px;
    padding: 0.5rem 1rem;
}

div[data-testid="stMetric"] {
    background-color: white;
    padding: 10px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)



# ----------------------------
# LOAD DATA
# ----------------------------
@st.cache_data
def load_cities():
    return pd.read_csv("worldcities.csv")


df = load_cities()


# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("Filters")

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
    placeholder="Search city..."
)

min_score = st.sidebar.slider("Minimum Score", 0, 100, 0)


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
    return score


def apply_scoring(leads):
    for l in leads:
        l["score"] = score_lead(l)
    return leads


# ----------------------------
# SESSION STATE
# ----------------------------
if "all_leads" not in st.session_state:
    st.session_state.all_leads = []

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

    # filter by score
    results = [r for r in results if r.get("score", 0) >= min_score]

    insert_leads(industry, results)

    st.session_state.all_leads = results
    st.session_state.page = 1


# ----------------------------
# SMART PAGINATION (LOAD MORE SYSTEM)
# ----------------------------
leads = st.session_state.all_leads

start = 0
end = st.session_state.page * PAGE_SIZE

paged_leads = leads[start:end]


# ----------------------------
# METRICS
# ----------------------------
if paged_leads:

    col1, col2, col3 = st.columns(3)

    col1.metric("Loaded Leads", len(paged_leads))
    col2.metric("Total Available", len(leads))
    col3.metric("Avg Score",
                round(sum(l.get("score",0) for l in paged_leads)/len(paged_leads),1))


# ----------------------------
# LOAD MORE BUTTON
# ----------------------------
if len(leads) > end:
    if st.button("⬇ Load More"):
        st.session_state.page += 1


# ----------------------------
# TABLE VIEW
# ----------------------------
st.subheader("📋 Leads")

df_out = pd.DataFrame(paged_leads)

columns = ["name", "website", "phone", "email", "address", "score"]

for c in columns:
    if c not in df_out.columns:
        df_out[c] = None

df_out = df_out[columns]

st.dataframe(df_out, use_container_width=True)


# ----------------------------
# MAP (CLUSTERED - NO LAG)
# ----------------------------
st.subheader("🗺️ Map View )")

if paged_leads:

    m = folium.Map(location=[paged_leads[0]["lat"], paged_leads[0]["lon"]], zoom_start=12)

    cluster = MarkerCluster().add_to(m)

    for l in paged_leads[:500]:  # safety limit for browser
        if l.get("lat") and l.get("lon"):

            color = "green" if l.get("score",0) > 70 else "red"

            folium.Marker(
                location=[l["lat"], l["lon"]],
                popup=f"{l['name']} | Score: {l.get('score',0)}",
                icon=folium.Icon(color=color)
            ).add_to(cluster)

    st_folium(m, width=900, height=500)

else:
    st.info("Generate leads to see map")
