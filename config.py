"""
Single source of truth for domain, mapped pages, competitor list, country
scope, exclusion vocabulary, and scoring weights. Every fetcher and analysis
module imports from here rather than repeating this data.

Mirrors the sibling `Page Quality Dashboard/config.py` convention; the PAGES
list below is copied from there so "Mapped Page" values in this dashboard's
keyword output line up with that dashboard's page ids.
"""

DOMAIN = "ayurvedichealingvillage.com"

HOSPITAL = {
    "name": "Kairali Ayurvedic Healing Village",
    "domain": DOMAIN,
    "accreditation": "NABH",
    "audience": "HNI",
}

# id: stable slug, shared with Page Quality Dashboard's config.py, used as
# the "Mapped Page" value in keyword output. lang: "en" | "ru" | "de".
PAGES = [
    {"id": "ayurveda-retreat-kerala", "title": "Ayurveda Retreat Kerala", "url": f"https://{DOMAIN}/ayurveda-retreat-kerala.html", "lang": "en"},
    {"id": "ayurveda-treatment-neo-south-india-cities", "title": "Ayurveda Treatment — South India Cities", "url": f"https://{DOMAIN}/Ayurveda_Treatment_Neo_S.India_Cities.html", "lang": "en"},
    {"id": "ayurvedic-treatment-packages", "title": "Ayurvedic Treatment Packages", "url": f"https://{DOMAIN}/ayurvedic-treatment-packages.html", "lang": "en"},
    {"id": "preventive-rejuvenation-detoxification", "title": "Preventive, Rejuvenation & Detoxification", "url": f"https://{DOMAIN}/preventive-rejuvenation-detoxification.html", "lang": "en"},
    {"id": "kairali-brand-and-competition", "title": "Kairali Brand & Competition", "url": f"https://{DOMAIN}/Kairali_Brand_and_Competition_Neo-original.html", "lang": "en"},
    {"id": "kairali-cleansing-centre", "title": "Kairali Cleansing Centre", "url": f"https://{DOMAIN}/kairali-cleansing-centre.html", "lang": "en"},
    {"id": "weight-loss", "title": "Weight Loss", "url": f"https://{DOMAIN}/weight-loss.html", "lang": "en"},
    {"id": "pain-management", "title": "Pain Management", "url": f"https://{DOMAIN}/pain-management.html", "lang": "en"},
    {"id": "panchakarma-treatment", "title": "Panchakarma Treatment", "url": f"https://{DOMAIN}/panchkarma-treatment.html", "lang": "en"},
    {"id": "treatment-in-kerala", "title": "Treatment in Kerala", "url": f"https://{DOMAIN}/treatment-in-kerala.html", "lang": "en"},
    {"id": "treatment-in-kerala-russian", "title": "Treatment in Kerala (Russian)", "url": f"https://{DOMAIN}/treatment-in-kerala-russian.html", "lang": "ru"},
    {"id": "wellness-resort-kerala", "title": "Wellness Resort Kerala", "url": f"https://{DOMAIN}/wellness-resort-kerala.html", "lang": "en"},
    {"id": "treatment-in-kerala-german", "title": "Behandlung in Kerala (German)", "url": f"https://{DOMAIN}/de/behandlung-in-kerala/", "lang": "de"},
]

PAGE_IDS = [p["id"] for p in PAGES]

# Live GSC/GA4/Ads targets -- same Kairali/ayurvedichealingvillage.com
# accounts as the sibling Combined Marketing Dashboard family (shared OAuth
# client, project "erudite-coast-502112-n5"; see fetchers/fetch_gsc.py,
# fetch_ga4.py, fetch_google_ads_search_terms.py and scripts/authenticate_*.py).
GSC_SITE_URLS = [
    f"https://{DOMAIN}/",
    f"https://www.{DOMAIN}/",
]
GA4_PROPERTY_ID = "394301498"
ADS_CUSTOMER_ID = "7129610573"
ADS_LOOKBACK = "LAST_30_DAYS"
GSC_LOOKBACK_DAYS = 90
GSC_DATA_LAG_DAYS = 3  # GSC data has a processing lag; same as the sibling

# Semrush databases queried per live search (Search tool), matching the
# international-patient markets in scope, not just India. Confirmed live
# this session: phrase_related on a real seed yields 30-50 real,
# volume-backed keywords per database -- this is the primary discovery
# source now, not a per-AI-keyword exact-match lookup (see
# api/search.py / fetchers/semrush_client.py).
SEMRUSH_SEARCH_DATABASES = ["in", "us", "uk", "ae"]

# Google Ads Keyword Planner (KeywordPlanIdeaService) geo-target-constant
# resource names, used only as a fallback for AI-suggested keywords Semrush
# has no volume for (see fetchers/keyword_planner_client.py). Standard,
# stable Google Ads IDs -- not verified against a live account in this
# environment, so the caller retries without geo targeting if rejected.
KEYWORD_PLANNER_GEO_TARGETS = [
    "geoTargetConstants/2356",  # India
    "geoTargetConstants/2840",  # United States
    "geoTargetConstants/2826",  # United Kingdom
    "geoTargetConstants/2784",  # United Arab Emirates
]

# Tier A: Kerala/South India direct competitors -- same list as Page Quality
# Dashboard's config.TIER_A_COMPETITORS, live-scrapable (not Cloudflare-blocked).
TIER_A_COMPETITORS = [
    {"name": "Somatheeram Ayurveda Village", "url": "https://www.somatheeram.in/"},
    {"name": "Kalari Kovilakom", "url": "https://www.cghearth.com/kalari-kovilakom"},
    {"name": "Vaidyagrama", "url": "https://vaidyagrama.com/"},
    {"name": "Neeleshwar Hermitage", "url": "https://www.neeleshwarhermitage.com/"},
    {"name": "Kairali Heritage Resort", "url": "https://www.kairaliheritageresort.com/"},
]

# Countries in scope for Core Search Metrics volume-by-country. Semrush
# country codes (ISO 3166-1 alpha-2).
COUNTRIES = {
    "in": "India",
    "us": "USA",
    "uk": "UK",
    "ae": "UAE",
    "sa": "Saudi Arabia",
    "qa": "Qatar",
    "kw": "Kuwait",
    "de": "Germany",
    "fr": "France",
    "au": "Australia",
}

# Spam/low-quality-intent vocabulary -- any keyword containing one of these
# terms is auto-excluded to the Avoid List regardless of volume. Deliberately
# broad; false positives land on the Avoid List for manual review rather than
# silently dropping (see analysis/intent_and_audience.py).
SPAM_TERMS = [
    "massage near me", "escort", "happy ending", "body to body", "spa near me",
    "erotic", "sensual massage", "massage parlour", "call girl",
]

# DIY/home-remedy terms push intent toward "Low-Quality" (they're genuine
# searches, just not commercial-fit for a hospital's paid landing pages).
DIY_HOME_REMEDY_TERMS = [
    "at home", "diy", "home remedy", "home remedies", "how to make",
    "recipe", "self treatment", "without doctor",
]

# Job-seeker terms -- also Low-Quality intent, not spam.
JOB_SEEKER_TERMS = [
    "job", "jobs", "vacancy", "career", "hiring", "salary", "internship",
]

# Medical/therapeutic specificity vocabulary -- presence raises
# Medical Specificity Score and Audience-Fit Score.
MEDICAL_SPECIFICITY_TERMS = [
    "panchakarma", "ayurvedic treatment", "ayurveda hospital", "nabh",
    "physician", "clinical", "therapy for", "treatment for", "chronic",
    "rejuvenation therapy", "detoxification", "diagnosis",
]

# Terms that read as luxury without saying the word "luxury" -- used only as
# a *positive* Audience-Fit signal, never surfaced as literal copy.
QUALITY_CONSCIOUS_TERMS = [
    "best ayurveda hospital", "authentic ayurveda", "world class",
    "internationally accredited", "expert physicians", "private villa",
    "personalized treatment", "premier", "renowned",
]

# Medical/health compliance-risk vocabulary -- terms that read as medical
# claims (cure/guarantee language) trigger Compliance Check flags per
# Google Ads Healthcare & Medicines policy + YMYL guidance.
COMPLIANCE_RISK_TERMS = [
    "cure", "guaranteed", "permanent cure", "miracle", "100% effective",
    "no side effects", "instant relief", "overnight cure",
]

# "patient(s)" directly paired with a specific nationality/country name
# reads as a targeted medical claim about that population and is excluded
# from the live Search tool's suggestions entirely (see
# analysis/compliance.py::is_patient_nationality_pattern). Deliberately
# does NOT include generic terms already treated as legitimate commercial
# keywords elsewhere in this dataset -- "international", "foreigners",
# "nri" are fine; naming a specific country next to "patients" is not.
NATIONALITY_COUNTRY_TERMS = [
    "uk", "united kingdom", "britain", "british",
    "usa", "america", "american", "united states",
    "gulf", "uae", "dubai", "abu dhabi", "emirati",
    "saudi", "qatar", "kuwait", "bahrain", "oman",
    "german", "germany", "french", "france",
    "australian", "australia", "russian", "russia", "canadian", "canada",
]

# Question-starter words used for Type classification (Question-type) and
# Answerability scoring.
QUESTION_STARTERS = ["what", "why", "how", "when", "where", "which", "who", "can", "does", "is"]

# Cross-Source Confidence weights -- how much each source contributes when
# it has data for a keyword. Renormalized over whichever sources are present
# (see analysis/confidence.py), same renormalization pattern as Page Quality
# Dashboard's tier2 weights.
CONFIDENCE_WEIGHTS = {
    "gsc": 0.35,
    "ga4": 0.25,
    "ads": 0.20,
    "semrush": 0.20,
}

# AI & Voice Search Readiness sub-weights.
AI_VOICE_WEIGHTS = {
    "aeoScore": 0.35,
    "answerabilityScore": 0.35,
    "geoVisibilityScore": 0.30,
}

CONFIDENCE_BANDS = [("High", 75), ("Medium", 45), ("Low", 0)]


def band_for_score(score, bands=CONFIDENCE_BANDS):
    for label, floor in bands:
        if score >= floor:
            return label
    return bands[-1][0]
