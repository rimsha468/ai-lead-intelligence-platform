import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

from scraper import LeadScraper
from database import init_db, insert_leads


# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="LeadAtlas AI",
    layout="wide"
)


# ----------------------------
# STYLES
# ----------------------------
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background-color: #C9EBFF;
}

html, body, [class*="css"] {
    font-family: "Segoe UI", sans-serif;
}

.block-container {
    padding-top: 1.5rem;
}
</style>
""", unsafe_allow_html=True)


# ----------------------------
# HEADER
# ----------------------------
st.markdown("""
<h1 style="margin-bottom:0;">🧠 LeadAtlas AI</h1>
<p style="color:gray;">Geospatial Lead Intelligence & CRM Dashboard</p>
""", unsafe_allow_html=True)

st.markdown("---")


# ----------------------------
# INIT
# ----------------------------
init_db()


# ----------------------------
# DATA
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


def completeness_score(l):
    return sum([
        1 if l.get("name") else 0,
        1 if l.get("phone") else 0,
        1 if l.get("email") else 0,
        1 if l.get("address") else 0
    ])


# ----------------------------
# OPPORTUNITY ENGINE
# ----------------------------
def opportunity_score(lead):
    score = 0
    if lead.get("website"): score += 30
    if lead.get("phone"): score += 25
    if lead.get("email"): score += 25
    if lead.get("address"): score += 20
    return min(score, 100)


def lead_reasons(lead):
    reasons = []
    if lead.get("website"): reasons.append("Website available")
    if lead.get("phone"): reasons.append("Phone available")
    if lead.get("email"): reasons.append("Email available")
    if lead.get("address"): reasons.append("Address available")
    return reasons


def business_summary(lead):
    reasons = lead_reasons(lead)

    if len(reasons) >= 4:
        quality = "very strong"
    elif len(reasons) == 3:
        quality = "strong"
    elif len(reasons) == 2:
        quality = "moderate"
    else:
        quality = "limited"

    return f"This business is a {quality} lead with {len(reasons)} key data points."


# ----------------------------
# 🧠 EMAIL GENERATOR (NEW)
# ----------------------------
def generate_ai_email(lead, intent):

    name = lead.get("name", "there")
    website = lead.get("website", "")
    phone = lead.get("phone", "")
    address = lead.get("address", "")

    base_context = f"""
Business Name: {name}
Website: {website}
Phone: {phone}
Address: {address}
"""

    if intent == "Business Outreach":

        return f"""
Subject: Collaboration Opportunity with {name}

Hi {name},

I hope you're doing well.

I came across your business and was impressed by your presence in the market.

Based on your profile:
- Website: {website or "Not listed"}
- Contact availability: {phone or "Not listed"}

I believe there may be an opportunity for collaboration that could help improve your visibility and customer reach.

Would you be open to a quick discussion?

Best regards,
LeadAtlas AI
"""

    elif intent == "Job Application":

        return f"""
Subject: Application & Interest in Opportunities at {name}

Hi {name},

I hope you're doing well.

I recently came across your organization and wanted to express my interest in any potential opportunities.

I found your business information and was particularly interested in your work and presence in the industry.

If there are any openings or future opportunities, I would love to be considered.

Thank you for your time.

Best regards,
Applicant
"""

    elif intent == "Partnership":

        return f"""
Subject: Partnership Opportunity with {name}

Hi {name},

I am reaching out regarding a potential partnership opportunity.

Given your business presence and available contact channels, I believe there is room for mutual growth and collaboration.

I would love to explore how we can work together.

Looking forward to your response.

Best regards,
LeadAtlas AI
"""

    else:

        return f"""
Hi {name},

I would like to get in touch regarding your business.

Best regards,
LeadAtlas AI
"""




# ----------------------------
# SESSION
# ----------------------------
if "leads" not in st.session_state:
    st.session_state.leads = []


# ----------------------------
# SIDEBAR
# ----------------------------
st.sidebar.title("Lead Panel")

industry = st.sidebar.selectbox(
    "Industry",
    INDUSTRIES,
    format_func=lambda x: industry_map[x]
)

city_names = df["city"] + ", " + df["country"]

selected_city_name = st.sidebar.selectbox(
    "City",
    city_names,
    index=None,
    placeholder="Search city..."
)

score_filter = st.sidebar.slider("Min Score", 0, 100, 0)


# ----------------------------
# GENERATE
# ----------------------------
if st.sidebar.button("🚀 Generate Leads"):

    city_row = df[(df["city"] + ", " + df["country"]) == selected_city_name].iloc[0]

    lat = city_row["lat"]
    lon = city_row["lng"]

    raw = scraper.search(industry, (lat, lon))

    seen = set()
    results = []

    for r in raw:
        key = (r.get("name"), r.get("lat"), r.get("lon"))
        if key not in seen:
            seen.add(key)
            results.append(r)

    for r in results:
        r["score"] = score_lead(r)

    insert_leads(industry, results)

    results.sort(key=lambda x: (completeness_score(x), x["score"]), reverse=True)

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
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Leads", len(leads))

    col2.metric("High Quality (60+)", len([l for l in leads if l["score"] >= 60]))

    avg = round(sum(l["score"] for l in leads) / len(leads), 1)
    col3.metric("Avg Score", avg)

    col4.metric(
        "Avg Opportunity",
        round(sum(opportunity_score(l) for l in leads) / len(leads), 1)
    )


st.markdown("---")


# ----------------------------
# TABLE
# ----------------------------
st.markdown("### Lead Database")

df_out = pd.DataFrame(filtered)

cols = ["name", "phone", "email", "address", "website", "score"]
for c in cols:
    if c not in df_out:
        df_out[c] = None

st.dataframe(df_out[cols], use_container_width=True)


# ----------------------------
# LEAD INTELLIGENCE
# ----------------------------

st.markdown("---")
st.markdown("### Lead Intelligence")

if filtered:

    lead_name = st.selectbox("Select Lead", [l["name"] for l in filtered])
    lead = next(l for l in filtered if l["name"] == lead_name)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric("Opportunity Score", opportunity_score(lead))

    with col2:
        st.info(business_summary(lead))

    st.markdown("#### Why this lead matters")

    for r in lead_reasons(lead):
        st.success(r)

    # ----------------------------
    # EMAIL GENERATOR UI
    # ----------------------------

    st.markdown("### ✉️ Cold Email Generator")

    if "generated_email" not in st.session_state:
        st.session_state.generated_email = ""
    intent = st.selectbox(
        "Email Purpose",
        ["Business Outreach", "Job Application", "Partnership", "General"]
    )

    if st.button("✉️ Generate AI Email"):
        email = generate_ai_email(lead, intent)
        st.session_state.generated_email = email

    if st.session_state.generated_email:
        st.text_area(
            "Generated Email",
            st.session_state.generated_email,
            height=300
        )


# ----------------------------
# MAP
# ----------------------------
st.markdown("---")
st.markdown("### Lead Map")

if filtered:

    m = folium.Map(location=[filtered[0]["lat"], filtered[0]["lon"]], zoom_start=12)

    for l in filtered[:100]:
        if l.get("lat") and l.get("lon"):
            color = "green" if completeness_score(l) == 4 else "red"

            folium.Marker(
                [l["lat"], l["lon"]],
                popup=f"{l['name']} | {l['score']}",
                icon=folium.Icon(color=color)
            ).add_to(m)

    st_folium(m, width=900, height=500)

else:
    st.info("Generate leads to view dashboard")
