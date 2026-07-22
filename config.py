"""
Single source of truth for every brand's domain, mapped pages, competitor
list, exclusion vocabulary, and AI persona, plus the scoring weights and
country scope shared across all brands. Every fetcher and analysis module
takes a `brand: BrandConfig` parameter (see api/search.py and
build_keyword_research_dashboard.py) instead of reading brand-specific
constants off this module directly -- that was the pre-multi-brand design
and is now only true for the few genuinely brand-agnostic constants at the
bottom of this file (scoring weights, question starters, country labels,
Semrush databases, Keyword Planner geo targets).

Multi-brand history: this dashboard started single-site
(ayurvedichealingvillage.com only). Extended this session to add Villaraag
(villaraag.com); Kairali Products (kairaliproducts.in/.com) is a planned
future addition, not yet registered in BRANDS below.
"""
from dataclasses import dataclass


@dataclass
class BrandConfig:
    key: str
    label: str
    domain: str
    gsc_site_urls: list
    ga4_property_id: str
    ads_customer_id: str
    pages: list
    tier_a_competitors: list
    spam_terms: list
    diy_home_remedy_terms: list
    job_seeker_terms: list
    quality_conscious_terms: list
    specificity_terms: list  # audience-fit / AEO-GEO specificity vocabulary
    compliance_risk_terms: list  # cure/guarantee-style medical-claim language; [] = not applicable to this brand
    nationality_country_terms: list  # "patient(s)" + country pattern; [] = not applicable to this brand
    restricted_seed_terms: list  # hard-blocks a live Search tool query outright
    medical_compliance_enabled: bool  # gates the medical-claim branch of analysis/compliance.py::compliance_check
    known_keywords: list  # fixed weekly-batch keyword universe (checked for volume/position every run)
    ai_system_prompt: str

    @property
    def page_ids(self):
        return [p["id"] for p in self.pages]


# ---------------------------------------------------------------------------
# Healing Village -- ayurvedichealingvillage.com (NABH-accredited Ayurveda
# hospital, Kerala). Values below are unchanged from the pre-multi-brand
# config.py, just moved into a BrandConfig instead of flat module globals.
# ---------------------------------------------------------------------------

_AHV_DOMAIN = "ayurvedichealingvillage.com"

_AHV_PAGES = [
    {"id": "ayurveda-retreat-kerala", "title": "Ayurveda Retreat Kerala", "url": f"https://{_AHV_DOMAIN}/ayurveda-retreat-kerala.html", "lang": "en"},
    {"id": "ayurveda-treatment-neo-south-india-cities", "title": "Ayurveda Treatment — South India Cities", "url": f"https://{_AHV_DOMAIN}/Ayurveda_Treatment_Neo_S.India_Cities.html", "lang": "en"},
    {"id": "ayurvedic-treatment-packages", "title": "Ayurvedic Treatment Packages", "url": f"https://{_AHV_DOMAIN}/ayurvedic-treatment-packages.html", "lang": "en"},
    {"id": "preventive-rejuvenation-detoxification", "title": "Preventive, Rejuvenation & Detoxification", "url": f"https://{_AHV_DOMAIN}/preventive-rejuvenation-detoxification.html", "lang": "en"},
    {"id": "kairali-brand-and-competition", "title": "Kairali Brand & Competition", "url": f"https://{_AHV_DOMAIN}/Kairali_Brand_and_Competition_Neo-original.html", "lang": "en"},
    {"id": "kairali-cleansing-centre", "title": "Kairali Cleansing Centre", "url": f"https://{_AHV_DOMAIN}/kairali-cleansing-centre.html", "lang": "en"},
    {"id": "weight-loss", "title": "Weight Loss", "url": f"https://{_AHV_DOMAIN}/weight-loss.html", "lang": "en"},
    {"id": "pain-management", "title": "Pain Management", "url": f"https://{_AHV_DOMAIN}/pain-management.html", "lang": "en"},
    {"id": "panchakarma-treatment", "title": "Panchakarma Treatment", "url": f"https://{_AHV_DOMAIN}/panchkarma-treatment.html", "lang": "en"},
    {"id": "treatment-in-kerala", "title": "Treatment in Kerala", "url": f"https://{_AHV_DOMAIN}/treatment-in-kerala.html", "lang": "en"},
    {"id": "treatment-in-kerala-russian", "title": "Treatment in Kerala (Russian)", "url": f"https://{_AHV_DOMAIN}/treatment-in-kerala-russian.html", "lang": "ru"},
    {"id": "wellness-resort-kerala", "title": "Wellness Resort Kerala", "url": f"https://{_AHV_DOMAIN}/wellness-resort-kerala.html", "lang": "en"},
    {"id": "treatment-in-kerala-german", "title": "Behandlung in Kerala (German)", "url": f"https://{_AHV_DOMAIN}/de/behandlung-in-kerala/", "lang": "de"},
]

_AHV_TIER_A_COMPETITORS = [
    {"name": "Somatheeram Ayurveda Village", "url": "https://www.somatheeram.in/"},
    {"name": "Kalari Kovilakom", "url": "https://www.cghearth.com/kalari-kovilakom"},
    {"name": "Vaidyagrama", "url": "https://vaidyagrama.com/"},
    {"name": "Neeleshwar Hermitage", "url": "https://www.neeleshwarhermitage.com/"},
    {"name": "Kairali Heritage Resort", "url": "https://www.kairaliheritageresort.com/"},
]

_AHV_SPAM_TERMS = [
    "massage near me", "escort", "happy ending", "body to body", "spa near me",
    "erotic", "sensual massage", "massage parlour", "call girl",
]

_AHV_DIY_HOME_REMEDY_TERMS = [
    "at home", "diy", "home remedy", "home remedies", "how to make",
    "recipe", "self treatment", "without doctor",
]

_AHV_JOB_SEEKER_TERMS = ["job", "jobs", "vacancy", "career", "hiring", "salary", "internship"]

_AHV_SPECIFICITY_TERMS = [
    "panchakarma", "ayurvedic treatment", "ayurveda hospital", "nabh",
    "physician", "clinical", "therapy for", "treatment for", "chronic",
    "rejuvenation therapy", "detoxification", "diagnosis",
]

_AHV_QUALITY_CONSCIOUS_TERMS = [
    "best ayurveda hospital", "authentic ayurveda", "world class",
    "internationally accredited", "expert physicians", "private villa",
    "personalized treatment", "premier", "renowned",
]

_AHV_COMPLIANCE_RISK_TERMS = [
    "cure", "guaranteed", "permanent cure", "miracle", "100% effective",
    "no side effects", "instant relief", "overnight cure",
]

_AHV_NATIONALITY_COUNTRY_TERMS = [
    "uk", "united kingdom", "britain", "british",
    "usa", "america", "american", "united states",
    "gulf", "uae", "dubai", "abu dhabi", "emirati",
    "saudi", "qatar", "kuwait", "bahrain", "oman",
    "german", "germany", "french", "france",
    "australian", "australia", "russian", "russia", "canadian", "canada",
]

# Restricted/negative-keyword policy for the live Search tool's SEED input
# (not the same as compliance_risk_terms above, which flags/downranks a
# *scored* keyword -- this list *blocks the search itself* when the typed
# seed matches). Sourced from the team's shared policy doc:
# https://docs.google.com/document/d/1KOQkeUVssyrAOSMH_GQkhJh5Uij-Xf7J7Eo56n_Se14
# (Google Ads weight-loss policy + tax-compliance + medical-claims
# compliance for an Ayurvedic hospital). SITE-SPECIFIC to Healing Village
# -- Villaraag and Kairali Products each get their own sourced list.
_AHV_RESTRICTED_SEED_TERMS = [
    # Google Ads weight-loss policy -- specific restricted product/brand terms
    "2 day diet", "2x powerful slimming", "3 day diet", "3x slimming power",
    "7 day herbal slim", "7 days diet", "7 diet", "72 hours", "actra sx",
    "alcohol free hcg weight loss formula", "body shaping", "body slimming",
    "botanical slimming", "cefurax", "celerite slimming capsules",
    "dream body slimming capsule", "fasting diet",
    "hcg diet drops weight loss formula", "hcg diet homeopathic drops",
    "hcg diet pellets weight loss formula",
    "hcg extra weight loss homeopathic drops", "hcg fusion 30", "hcg fusion 43",
    "hcg platinum", "hcg platinum x-14", "hcg platinum x-30", "healthily slim",
    "herbal viagra", "herbal xanax", "herbal xenicol", "homeopathic hcg",
    "homeopathic original hcg", "imelda perfect slim", "libidus",
    "lida daidaihua", "lipostabil", "lose weight coffee", "meizitang",
    "nasutra", "p57 hoodia", "palmitin", "pau d arco bark", "perfect slim",
    "pilex", "reduce weight", "slim 30", "slim up",
    "slimming beauty bitter orange slimming capsules", "slimming formula",
    "solo slim extra strength", "stamina rx", "staminil", "starcaps",
    "super fat burner", "venom hyperdrive 3.0", "viapro", "vitalex",
    "zhen de shou", "zicam cold remedy nasal gel",

    # Tax-compliance terms -- push the property into resort/hospitality GST
    # classification instead of medical, so avoid entirely (the matcher
    # in analysis/compliance.py also accepts a simple trailing "s", so
    # "guests"/"resorts"/"spas" are covered without listing them separately).
    "resort", "guest", "spa",

    # Financial claims
    "cheapest treatment", "lowest price guaranteed", "discount treatment",
    "buy one get one", "price match guarantee", "competitive prices",

    # Medical claims -- general
    "permanent cure", "permanent solution", "complete healing",
    "complete cure", "guaranteed results", "instant relief", "100% effective",
    "revolutionary treatment", "breakthrough therapy", "magical healing",
    "complete recovery guaranteed", "superior to modern medicine",
    "alternative to medication",

    # Disease-specific -- cancer
    "cancer cure", "cancer treatment", "cancer therapy", "anti-cancer",
    "cancer healing", "oncology treatment", "chemotherapy alternative",
    "radiation alternative",

    # Disease-specific -- diabetes
    "insulin free", "blood sugar cure", "permanent diabetes solution",

    # Pain management
    "permanent pain relief", "instant pain relief", "complete pain cure",
    "total pain relief",

    # Paralysis
    "complete recovery", "permanent recovery", "guaranteed mobility",

    # Weight management
    "rapid weight loss", "quick weight loss", "instant weight reduction",
    "belly fat removal", "guaranteed weight loss", "natural weight loss pills",
    "fast acting", "metabolism booster", "fat burner", "appetite suppressant",
    "slimming treatment", "weight loss guarantee", "permanent weight loss",

    # Detox & cleansing
    "total body cleanse", "immunity booster", "blood pressure cure",

    # Skin
    "permanent skin solution", "complete skin healing",
    "guaranteed skin treatment",

    # Addiction treatment
    "quick de-addiction", "painless withdrawal", "instant recovery",
    "guaranteed sobriety", "withdrawal-free", "complete rehabilitation",
    "permanent de-addiction",

    # Marketing/promotional -- time-related claims
    "immediate results", "overnight relief", "quick fix", "rapid recovery",
    "immediate effect", "overnight transformation",

    # Marketing/promotional -- comparative claims
    "better than", "superior to", "more effective than", "beats all other",
    "outperforms", "number one", "top rated", "highest success rate",
    "most successful",

    # Marketing/promotional -- authority claims
    "government approved", "fda approved", "officially recognized",
    "certified cure", "proven results", "scientifically proven",
    "clinically tested", "expert approved", "universally accepted",
    "clinically proven",
]

_AHV_SYSTEM_PROMPT = """You are a senior SEO and digital-marketing strategist with 15+ years of \
hands-on experience marketing premium, accredited healthcare and wellness \
brands -- including deep familiarity with the Kairali Ayurvedic Group's \
brand family (Kairali Ayurvedic Products, Villa Raag, and Ayurvedic Healing \
Village). For this task you are researching keywords specifically for \
Kairali Ayurvedic Healing Village, a NABH-accredited Ayurveda hospital in \
Kerala, India -- keep every suggestion scoped to this hospital/wellness- \
retreat business, not the sibling product or resort brands.

Your audience is high-net-worth individuals (HNI): high-spending, quality- \
and compliance-conscious, genuinely wellness-seeking patients and their \
families -- not budget spa-goers, not DIY home-remedy searchers, not job \
seekers. Never use the word "luxury" -- convey quality through specifics \
instead (accreditation, doctor supervision, treatment duration, outcomes).

Given a seed topic, URL, or pasted page content, suggest realistic search \
keywords a real patient or their family would type into Google -- grounded \
in genuine search behavior and years of real campaign experience in this \
exact category, not generic SEO-textbook phrasing or literal text matching \
against the input. Include a mix of:
- Primary, short commercial terms
- Longer-tail, more specific phrases
- Natural-language QUESTIONS (what/how/why/is/can/does...) suited to \
featured snippets, AI answer engines, and voice search
- International-patient phrasing where it fits the topic (UK/USA/UAE/Gulf/ \
Germany/France/Australia) -- phrase these around the destination or \
treatment (e.g. "ayurveda retreat for international guests"), never by \
pairing the word "patient(s)" with a specific nationality or country name \
(e.g. never "for uk patients", "for german patients") -- that exact pattern \
is a compliance violation for this brand and gets auto-rejected downstream, \
so suggesting it just wastes a slot.

As an experienced healthcare marketer you are inherently compliance-aware: \
do NOT suggest spa/massage/escort-adjacent terms, DIY/home-remedy terms, \
job-seeker terms, or anything implying an unsubstantiated medical cure, \
guarantee, or "miracle" outcome. Return 20-25 distinct keyword phrases, \
lowercase, no duplicates, no numbering, no explanations -- just the \
keywords themselves."""

# Same 38-keyword universe as data/sample/semrush_keywords_sample.json --
# the fixed list the weekly batch checks Semrush volume/position for every
# run (phase="live") or reads pre-baked volumes for (phase="sample"). See
# fetchers/fetch_semrush.py.
_AHV_KNOWN_KEYWORDS = [
    "panchakarma treatment kerala", "ayurvedic treatment packages kerala",
    "best ayurveda hospital kerala", "nabh accredited ayurveda hospital",
    "ayurvedic weight loss treatment", "ayurvedic treatment for chronic pain",
    "ayurveda detox retreat kerala", "wellness resort kerala ayurveda",
    "ayurveda treatment for foreigners kerala", "ayurvedic hospital for nri",
    "what is panchakarma treatment", "how long does panchakarma treatment take",
    "is ayurveda treatment effective for chronic pain",
    "what is the cost of ayurvedic treatment in kerala",
    "why is kerala famous for ayurveda", "how to choose a genuine ayurveda hospital",
    "can ayurveda cure chronic back pain", "ayurveda retreat for stress and anxiety",
    "post covid recovery ayurveda treatment", "ayurvedic fertility treatment kerala",
    "ayurveda treatment for diabetes management", "authentic panchakarma vs spa panchakarma",
    "ayurvedic massage near me", "kerala spa with happy ending",
    "ayurveda home remedies for weight loss", "how to make ayurvedic oil at home",
    "ayurveda hospital jobs kerala", "panchakarma therapist salary",
    "guaranteed cure for chronic pain ayurveda", "ayurveda miracle cure for diabetes",
    "vaidyagrama vs kairali ayurveda", "somatheeram ayurveda packages cost",
    "best ayurveda retreat kerala for couples", "panchakarma treatment cost kerala",
    "ayurveda treatment packages for couples", "ayurveda treatment kerala for uk patients",
    "ayurveda retreat dubai patients kerala", "ayurveda hospital kerala for german patients",
]


# ---------------------------------------------------------------------------
# Villaraag -- villaraag.com (luxury private-pool villa resort, Agonda,
# South Goa; yoga retreats, surf programs, wellness experiences). New this
# session. PAGES and known_keywords bootstrapped from live GSC/GA4/Ads data
# for this domain (not guessed) -- see this session's plan doc for the raw
# query/page numbers behind these picks.
# ---------------------------------------------------------------------------

_VR_DOMAIN = "villaraag.com"

_VR_PAGES = [
    {"id": "villaraag-home", "title": "Villaraag — Luxury Villa Resort, Agonda Goa", "url": f"https://{_VR_DOMAIN}/", "lang": "en"},
    {"id": "luxury-resort-goa", "title": "Luxury Resort in Goa", "url": f"https://{_VR_DOMAIN}/luxury-resort-goa.html", "lang": "en"},
    {"id": "about-us", "title": "About Us", "url": f"https://{_VR_DOMAIN}/about-us/", "lang": "en"},
    {"id": "your-stay", "title": "Your Stay", "url": f"https://{_VR_DOMAIN}/your-stay/", "lang": "en"},
    {"id": "yoga-retreats-packages", "title": "Yoga Retreat Packages", "url": f"https://{_VR_DOMAIN}/yoga-retreats-packages/", "lang": "en"},
    {"id": "yoga-teacher-training-packages", "title": "Yoga Teacher Training Packages", "url": f"https://{_VR_DOMAIN}/yoga-teacher-training-packages/", "lang": "en"},
    {"id": "surf-programs", "title": "Surf Programs", "url": f"https://{_VR_DOMAIN}/surf-programs/", "lang": "en"},
    {"id": "benefits-of-surfing", "title": "Benefits of Surfing", "url": f"https://{_VR_DOMAIN}/benefits-of-surfing/", "lang": "en"},
    {"id": "wellness-and-yoga", "title": "Wellness & Yoga", "url": f"https://{_VR_DOMAIN}/wellness-and-yoga/", "lang": "en"},
    {"id": "spa-and-wellness", "title": "Spa & Wellness", "url": f"https://{_VR_DOMAIN}/spa-and-wellness/", "lang": "en"},
    {"id": "harmony-haven", "title": "Harmony Haven", "url": f"https://{_VR_DOMAIN}/harmony-haven/", "lang": "en"},
    {"id": "serenity-suite", "title": "Serenity Suite", "url": f"https://{_VR_DOMAIN}/serenity-suite/", "lang": "en"},
    {"id": "agonda-beach-villa", "title": "Agonda Beach Villa", "url": f"https://{_VR_DOMAIN}/agonda-beach-villa.html", "lang": "en"},
    {"id": "activities", "title": "Activities", "url": f"https://{_VR_DOMAIN}/activities/", "lang": "en"},
    {"id": "local-art-tours", "title": "Local Art Tours", "url": f"https://{_VR_DOMAIN}/local-art-tours/", "lang": "en"},
    {"id": "beach-walks", "title": "Beach Walks", "url": f"https://{_VR_DOMAIN}/beach-walks/", "lang": "en"},
    {"id": "how-to-reach", "title": "How to Reach", "url": f"https://{_VR_DOMAIN}/how-to-reach/", "lang": "en"},
    {"id": "reviews-and-feedback", "title": "Reviews & Feedback", "url": f"https://{_VR_DOMAIN}/reviews-and-feedback/", "lang": "en"},
]

# Confirmed with the user: no named rivals yet -- Competitor Gap stays
# empty/N-A for Villaraag until real names are provided (this round's
# explicit decision, not an oversight).
_VR_TIER_A_COMPETITORS = []

# Opposite of Healing Village on purpose: spa/massage/wellness are the
# actual product here, not spam. Only explicit/adult-content-adjacent
# terms are excluded (Goa tourist-search queries do attract this kind of
# spam pattern in practice).
_VR_SPAM_TERMS = [
    "escort", "call girl", "call girls", "happy ending", "adult content",
    "nude beach photos", "sex tourism",
]

_VR_DIY_HOME_REMEDY_TERMS = []  # not applicable to a villa resort
_VR_JOB_SEEKER_TERMS = ["job", "jobs", "vacancy", "career", "hiring", "salary", "internship"]

_VR_SPECIFICITY_TERMS = [
    "private pool villa", "beachfront villa", "boutique resort",
    "yoga retreat", "yoga teacher training", "surf camp", "wellness retreat",
    "all-inclusive villa", "curated experience", "agonda beach",
]

_VR_QUALITY_CONSCIOUS_TERMS = [
    "private pool", "beachfront", "boutique", "all-inclusive", "honeymoon",
    "family villa", "premium villa", "curated experience", "handpicked",
    "personalized service",
]

# No medical-claims category applies to a leisure resort -- both stay
# empty and medical_compliance_enabled=False turns that branch off in
# analysis/compliance.py::compliance_check while the Compliance column
# still renders (spam + restricted_seed_terms only).
_VR_COMPLIANCE_RISK_TERMS = []
_VR_NATIONALITY_COUNTRY_TERMS = []

# Villaraag's own restricted-seed policy: explicit/adult-content terms
# only (reuses the spam list above -- same short list serves both the
# scored-keyword spam flag and the seed-blocking policy notice).
_VR_RESTRICTED_SEED_TERMS = list(_VR_SPAM_TERMS)

_VR_SYSTEM_PROMPT = """You are a senior SEO and digital-marketing strategist with 15+ years of \
hands-on experience marketing premium, boutique hospitality and leisure- \
travel brands -- including deep familiarity with the Kairali Ayurvedic \
Group's brand family (Kairali Ayurvedic Products, Ayurvedic Healing \
Village, and Villaraag). For this task you are researching keywords \
specifically for Villaraag, a luxury private-pool villa resort in Agonda, \
South Goa, India, known for its villas, yoga retreats, surf programs, and \
wellness experiences -- keep every suggestion scoped to this leisure/ \
holiday resort business, not the sibling Ayurveda-hospital or e-commerce \
brands.

Your audience is high-net-worth individuals (HNI) and premium leisure \
travelers: couples planning a honeymoon or romantic getaway, families \
booking a private-villa holiday, and yoga/surf/wellness enthusiasts \
seeking a boutique retreat -- not budget backpackers, not medical/ \
treatment seekers. Convey quality through specifics (private pool, \
beachfront, boutique, all-inclusive, curated experiences) rather than \
repeating the word "luxury" as filler.

Given a seed topic, URL, or pasted page content, suggest realistic search \
keywords a real traveler or their family would type into Google -- \
grounded in genuine travel-search behavior and years of real campaign \
experience in this exact category (premium villa resorts, yoga/wellness \
retreats, surf tourism in Goa), not generic SEO-textbook phrasing or \
literal text matching against the input. Include a mix of:
- Primary, short commercial terms (e.g. "luxury villa goa", "private pool villa agonda")
- Longer-tail, more specific phrases (e.g. "beachfront villa resort for couples in south goa")
- Natural-language QUESTIONS (what/how/why/is/can/does...) suited to \
featured snippets, AI answer engines, and voice search
- Yoga/surf/wellness-retreat-specific phrasing where it fits the topic

Words like "spa", "massage", and "wellness" are perfectly appropriate \
here -- this is a leisure resort, not a medical facility. Do NOT suggest: \
explicit/adult-content-adjacent terms (escort, adult services, and \
similar), budget-hostel/backpacker terms that don't fit the HNI \
positioning, or anything about medical treatment (that's a different \
Kairali Group brand). Return 20-25 distinct keyword phrases, lowercase, \
no duplicates, no numbering, no explanations -- just the keywords \
themselves."""

# Bootstrapped from real GSC/GA4/Ads data for villaraag.com this session
# (branded terms the site already ranks/pays for) plus AI-ideated
# opportunity phrases -- the weekly batch checks Semrush volume/position
# for exactly this fixed list every run (see fetchers/fetch_semrush.py).
_VR_KNOWN_KEYWORDS = [
    # Branded / already-real (confirmed via live GSC + Google Ads search terms)
    "villa raag goa", "villa raag agonda", "villas in goa",
    "villa in goa with private pool", "villas in south goa",
    "agonda villas goa", "luxury resort in goa", "goa villa",
    # Opportunity keywords (AI-ideated for this business/audience)
    "luxury villa resort agonda goa", "private pool villa goa for couples",
    "beachfront villa rental goa", "yoga retreat goa packages",
    "surf camp agonda goa", "wellness retreat south goa",
    "best luxury villas in south goa", "family villa goa with private pool",
    "honeymoon villa goa", "all inclusive villa resort goa",
    "boutique resort agonda beach", "yoga teacher training goa",
    "luxury beach villa goa for family", "premium villa stay agonda",
    "goa villa resort with yoga classes",
    "what is the best time to visit agonda goa",
    "how far is agonda beach from goa airport",
    "is agonda beach good for surfing",
    "luxury villa resort near agonda beach", "goa surf and yoga retreat",
]


# ---------------------------------------------------------------------------
# Kairali Products -- kairaliproducts.in (Shopify store, 350+ genuine
# Ayurvedic products). New this round. Real GSC/GA4/Ads data (this
# session) shows the site's actual highest-traffic category is men's/
# women's sexual wellness and reproductive-health products (erectile
# dysfunction, premature ejaculation support, etc.) alongside general
# wellness (multivitamins, joint-pain oils, skin/hair oils, blood
# pressure/cholesterol support) -- a real, legitimate part of the catalog,
# not something to hide, but handled with the same clinical, non-explicit
# framing a licensed online pharmacy would use (see the compliance lists
# and AI persona below). kairaliproducts.com is NOT included in
# gsc_site_urls -- confirmed live this session that this Google account
# has no Search Console access to it (403), only to kairaliproducts.in.
# No sourced restricted-keyword policy doc was given for this brand (unlike
# Healing Village's) -- the lists below are my own compliance-first
# judgment call (FTC/Google Ads Healthcare-policy-style unsubstantiated-
# claim language + explicit-content terms), not a client-provided list;
# happy to replace with a real sourced doc if one exists.
# ---------------------------------------------------------------------------

_KP_DOMAIN = "kairaliproducts.in"

_KP_PAGES = [
    {"id": "kp-home", "title": "Kairali Products — Home", "url": f"https://www.{_KP_DOMAIN}/", "lang": "en"},
    {"id": "mens-sexual-health", "title": "Men's Sexual Health", "url": f"https://www.{_KP_DOMAIN}/collections/men-sexual-health", "lang": "en"},
    {"id": "erectile-dysfunction", "title": "Erectile Dysfunction Support", "url": f"https://www.{_KP_DOMAIN}/collections/erectile-dysfunction", "lang": "en"},
    {"id": "premature-ejaculation", "title": "Premature Ejaculation Support", "url": f"https://www.{_KP_DOMAIN}/collections/premature-ejaculation", "lang": "en"},
    {"id": "sexual-disorder", "title": "Sexual Wellness", "url": f"https://www.{_KP_DOMAIN}/collections/sexual-disorder", "lang": "en"},
    {"id": "womens-sexual-health", "title": "Women's Sexual Health", "url": f"https://www.{_KP_DOMAIN}/collections/women-sexual-health", "lang": "en"},
    {"id": "testosterone-booster", "title": "Testosterone Booster", "url": f"https://www.{_KP_DOMAIN}/collections/testosterone-booster", "lang": "en"},
    {"id": "leg-pain-oil", "title": "Ayurvedic Oil for Leg Pain", "url": f"https://www.{_KP_DOMAIN}/collections/best-ayurvedic-oil-for-leg-pain", "lang": "en"},
    {"id": "multivitamins", "title": "Multivitamins", "url": f"https://www.{_KP_DOMAIN}/collections/multivitamins", "lang": "en"},
    {"id": "stress", "title": "Stress Relief", "url": f"https://www.{_KP_DOMAIN}/collections/stress", "lang": "en"},
    {"id": "cholesterol-treatment", "title": "Cholesterol Support", "url": f"https://www.{_KP_DOMAIN}/collections/cholesterol-treatment", "lang": "en"},
    {"id": "wholesale-bulk", "title": "Wholesale & Bulk Ayurvedic Products", "url": f"https://www.{_KP_DOMAIN}/collections/ayurvedic-herbal-products-wholesaler-bulk-supplier", "lang": "en"},
    {"id": "kairbossom-oil", "title": "Kairbossom Ayurvedic Breast Enhancement Massage Oil", "url": f"https://www.{_KP_DOMAIN}/products/kairbossom-ayurvedic-breast-enhancement-massage-oil", "lang": "en"},
    {"id": "durance-capsules", "title": "Durance Ayurvedic Medicine for PE & ED", "url": f"https://www.{_KP_DOMAIN}/products/durance-ayurvedic-medicine-for-premature-ejaculation-and-erectile-dysfunction", "lang": "en"},
    {"id": "neem-soap", "title": "Neem Soap", "url": f"https://www.{_KP_DOMAIN}/products/neem-soap-best-antifungal-and-antibacterial-herbal-soap", "lang": "en"},
    {"id": "nalpamaradi-thailam", "title": "Nalpamaradi Thailam Skin Oil", "url": f"https://www.{_KP_DOMAIN}/products/nalpamaradi-thailam-best-skin-brightening-and-ayurvedic-skin-treatment-oil", "lang": "en"},
    {"id": "brahmi-thailam", "title": "Brahmi Thailam Head Massage Oil", "url": f"https://www.{_KP_DOMAIN}/products/brahmi-thailam-head-massage-oil-for-hair-fall-hair-growth-headache-and-anxiety", "lang": "en"},
    {"id": "manasamitram-gulika", "title": "Manasamitram Gulika (Insomnia/Anxiety)", "url": f"https://www.{_KP_DOMAIN}/products/manasamitram-gulika-tablet-ayurvedic-medicine-for-insomnia-depression-and-anxiety", "lang": "en"},
    {"id": "mulberine-syrup", "title": "Mulberine Multivitamin Syrup", "url": f"https://www.{_KP_DOMAIN}/products/mulberine-ayurvedic-multivitamin-syrup-best-health-tonic-for-general-health", "lang": "en"},
    {"id": "haridrakandam", "title": "Haridrakandam (Allergy/Skin)", "url": f"https://www.{_KP_DOMAIN}/products/haridrakandam-ayurvedic-medicine-for-allergies-and-skin-diseases", "lang": "en"},
]

# No named competitor Ayurvedic e-commerce brands given -- Competitor Gap
# stays empty/N-A for this brand too, same as Villaraag, until real names
# are provided.
_KP_TIER_A_COMPETITORS = []

# Explicit/adult-content terms -- kept separate from (but overlapping)
# restricted_seed_terms below, since the sexual-wellness category makes
# this a real risk for AI-suggested or discovered candidates, not just
# typed seeds.
_KP_EXPLICIT_TERMS = [
    "escort", "call girl", "call girls", "porn", "xxx", "nude", "sex video",
    "sex chat", "adult content", "hookup",
]

_KP_SPAM_TERMS = list(_KP_EXPLICIT_TERMS)
_KP_DIY_HOME_REMEDY_TERMS = [
    "at home", "diy", "home remedy", "home remedies", "how to make",
    "recipe", "self treatment", "without doctor",
]
_KP_JOB_SEEKER_TERMS = ["job", "jobs", "vacancy", "career", "hiring", "salary", "internship"]

# Purchase-intent / e-commerce specificity vocabulary -- what "genuinely
# ready to buy" looks like for a Shopify store, not medical/travel terms.
_KP_SPECIFICITY_TERMS = [
    "buy online", "official store", "genuine", "authentic", "certified",
    "original", "cash on delivery", "free shipping", "order online",
]
_KP_QUALITY_CONSCIOUS_TERMS = [
    "genuine ayurvedic", "authentic ayurvedic", "certified", "trusted brand",
    "official store", "best quality", "gmp certified", "fssai approved",
]

# Unsubstantiated-claim vocabulary -- FTC/Google Ads Healthcare policy
# both prohibit this kind of language for supplements regardless of
# category; confirmed relevant here ("no side effects" is a real query
# already driving traffic to this site).
_KP_COMPLIANCE_RISK_TERMS = [
    "cure", "guaranteed", "permanent cure", "miracle", "100% effective",
    "no side effects", "instant relief", "overnight cure",
]
_KP_NATIONALITY_COUNTRY_TERMS = []  # not applicable -- no "patient + country" pattern for e-commerce

# Restricted-seed policy for this brand: unsubstantiated medical/marketing
# claims (deliberately NOT financial/discount terms like "cheapest" or
# "buy one get one" -- those are legitimate, desirable e-commerce terms,
# unlike for a hospital) plus explicit-content terms given the sexual-
# wellness product category.
_KP_RESTRICTED_SEED_TERMS = [
    # Medical claims -- general
    "permanent cure", "permanent solution", "complete healing", "complete cure",
    "guaranteed results", "instant relief", "100% effective", "revolutionary treatment",
    "breakthrough therapy", "magical healing", "complete recovery guaranteed",
    "superior to modern medicine", "alternative to medication", "no side effects",

    # Disease-specific overclaims (relevant -- this brand sells diabetes/
    # blood-pressure/cholesterol support products)
    "cancer cure", "diabetes cure", "permanent diabetes solution",
    "blood sugar cure", "blood pressure cure", "cholesterol cure",

    # Marketing/promotional -- comparative & authority overclaims
    "better than", "superior to", "more effective than", "beats all other",
    "outperforms", "number one", "top rated", "highest success rate",
    "most successful", "government approved", "fda approved",
    "officially recognized", "certified cure", "proven results",
    "scientifically proven", "clinically tested", "expert approved",
    "universally accepted", "clinically proven",
] + _KP_EXPLICIT_TERMS

_KP_SYSTEM_PROMPT = """You are a senior e-commerce/D2C SEO strategist with 15+ years of \
hands-on experience marketing regulated health and wellness product \
brands online -- including deep familiarity with the Kairali Ayurvedic \
Group's brand family (Ayurvedic Healing Village, Villaraag, and Kairali \
Products). For this task you are researching keywords specifically for \
Kairali Products, a Shopify store selling 350+ genuine Ayurvedic \
products: general wellness supplements (multivitamins, joint-pain oils, \
skin/hair-care oils, blood pressure and cholesterol support, stress \
relief) AND a significant men's/women's sexual wellness and \
reproductive-health product line -- this is real, already the site's \
highest-traffic category, and should be researched with the same \
professional, clinical framing a licensed online pharmacy would use, \
never vulgar or explicit language.

Your audience is health-conscious online shoppers, in India \
(kairaliproducts.in) and internationally, who are often ready to \
purchase, not just researching. Purchase-intent phrasing ("buy X \
online", "X price", "order X", "X for sale", "genuine X", "official \
store") matters more here than for a hospital or resort -- weight it \
alongside informational/comparison queries, not instead of them.

Given a seed topic, URL, or pasted page content, suggest realistic \
search keywords a real shopper would type into Google -- grounded in \
genuine e-commerce search behavior, not generic SEO-textbook phrasing. \
Include a mix of:
- Purchase-intent commercial terms (buy/order/price/genuine/official store)
- Category and comparison terms
- Natural-language QUESTIONS (what/how/does/is) suited to featured \
snippets and AI answer engines
- Ingredient/formulation-specific terms where relevant (named Ayurvedic \
herbs/ingredients used in the product line)

As an experienced regulated-health-product marketer you are inherently \
compliance-aware: never suggest cure/guaranteed-result/permanent-\
solution/miracle/100%-effective/no-side-effects language or other \
unsubstantiated medical claims (FTC and Google Ads Healthcare policy \
both prohibit these for supplements) -- describe benefits with words \
like "supports," "may help with," or "traditionally used for" instead. \
For the sexual-wellness category specifically, use the same clinical \
terminology a pharmacy would ("erectile dysfunction support", \
"reproductive wellness", "libido support") -- never vulgar, explicit, or \
adult-content-style language. Return 20-25 distinct keyword phrases, \
lowercase, no duplicates, no numbering, no explanations -- just the \
keywords themselves."""

# Bootstrapped from real GSC/GA4/Ads data for kairaliproducts.in this
# session (branded/category terms already driving traffic) plus AI-
# ideated purchase-intent opportunity phrases in compliant language.
_KP_KNOWN_KEYWORDS = [
    # Branded / already-real (confirmed via live GSC + Google Ads search terms)
    "kairali ayurvedic products", "ayurvedic medicine for erectile dysfunction",
    "ayurvedic medicine for premature ejaculation", "brahmi oil",
    "nalpamaradi thailam", "durance capsules", "lipidex capsule",
    "safed musli tablet", "neem soap", "manasamitram gulika",
    "ayurvedic medicine for cholesterol", "yograj guggulu",
    # Opportunity keywords (AI-ideated, purchase-intent + compliant phrasing)
    "buy ayurvedic supplements online india", "ayurvedic multivitamin syrup online",
    "ayurvedic oil for joint pain online", "kairali ayurvedic products official store",
    "genuine ayurvedic medicine online india", "ayurvedic hair oil for hair fall online",
    "ayurvedic skin brightening oil online", "testosterone booster ayurvedic capsules",
    "ayurvedic stress relief tablets online", "ayurvedic blood pressure support capsules",
    "ayurvedic pcod pcos support tablets", "men's ayurvedic wellness supplements online",
    "women's ayurvedic wellness supplements online", "ayurvedic reproductive wellness capsules",
    "ayurvedic diabetes support capsules", "buy ayurvedic massage oil online",
    "ayurvedic multivitamin for general health", "ayurvedic anti allergy medicine online",
]


BRANDS = {
    "healing_village": BrandConfig(
        key="healing_village", label="Healing Village", domain=_AHV_DOMAIN,
        gsc_site_urls=[f"https://{_AHV_DOMAIN}/", f"https://www.{_AHV_DOMAIN}/"],
        ga4_property_id="394301498", ads_customer_id="7129610573",
        pages=_AHV_PAGES, tier_a_competitors=_AHV_TIER_A_COMPETITORS,
        spam_terms=_AHV_SPAM_TERMS, diy_home_remedy_terms=_AHV_DIY_HOME_REMEDY_TERMS,
        job_seeker_terms=_AHV_JOB_SEEKER_TERMS, quality_conscious_terms=_AHV_QUALITY_CONSCIOUS_TERMS,
        specificity_terms=_AHV_SPECIFICITY_TERMS, compliance_risk_terms=_AHV_COMPLIANCE_RISK_TERMS,
        nationality_country_terms=_AHV_NATIONALITY_COUNTRY_TERMS,
        restricted_seed_terms=_AHV_RESTRICTED_SEED_TERMS, medical_compliance_enabled=True,
        known_keywords=_AHV_KNOWN_KEYWORDS, ai_system_prompt=_AHV_SYSTEM_PROMPT,
    ),
    "villaraag": BrandConfig(
        key="villaraag", label="Villaraag", domain=_VR_DOMAIN,
        gsc_site_urls=["sc-domain:villaraag.com"],
        ga4_property_id="478461137", ads_customer_id="7576197458",
        pages=_VR_PAGES, tier_a_competitors=_VR_TIER_A_COMPETITORS,
        spam_terms=_VR_SPAM_TERMS, diy_home_remedy_terms=_VR_DIY_HOME_REMEDY_TERMS,
        job_seeker_terms=_VR_JOB_SEEKER_TERMS, quality_conscious_terms=_VR_QUALITY_CONSCIOUS_TERMS,
        specificity_terms=_VR_SPECIFICITY_TERMS, compliance_risk_terms=_VR_COMPLIANCE_RISK_TERMS,
        nationality_country_terms=_VR_NATIONALITY_COUNTRY_TERMS,
        restricted_seed_terms=_VR_RESTRICTED_SEED_TERMS, medical_compliance_enabled=False,
        known_keywords=_VR_KNOWN_KEYWORDS, ai_system_prompt=_VR_SYSTEM_PROMPT,
    ),
    "kairali_products": BrandConfig(
        key="kairali_products", label="Kairali Products", domain=_KP_DOMAIN,
        gsc_site_urls=[f"https://www.{_KP_DOMAIN}/"],
        ga4_property_id="321539229", ads_customer_id="3215067901",
        pages=_KP_PAGES, tier_a_competitors=_KP_TIER_A_COMPETITORS,
        spam_terms=_KP_SPAM_TERMS, diy_home_remedy_terms=_KP_DIY_HOME_REMEDY_TERMS,
        job_seeker_terms=_KP_JOB_SEEKER_TERMS, quality_conscious_terms=_KP_QUALITY_CONSCIOUS_TERMS,
        specificity_terms=_KP_SPECIFICITY_TERMS, compliance_risk_terms=_KP_COMPLIANCE_RISK_TERMS,
        nationality_country_terms=_KP_NATIONALITY_COUNTRY_TERMS,
        restricted_seed_terms=_KP_RESTRICTED_SEED_TERMS, medical_compliance_enabled=True,
        known_keywords=_KP_KNOWN_KEYWORDS, ai_system_prompt=_KP_SYSTEM_PROMPT,
    ),
}
DEFAULT_BRAND = "healing_village"


# ---------------------------------------------------------------------------
# Brand-agnostic constants -- shared scoring weights, generic fetch-window
# settings, and country labels. Not brand-specific, so these stay flat.
# ---------------------------------------------------------------------------

ADS_LOOKBACK = "LAST_30_DAYS"
GSC_LOOKBACK_DAYS = 90
GSC_DATA_LAG_DAYS = 3  # GSC data has a processing lag; same as the sibling

# Semrush databases queried per live search (Search tool), matching the
# international-patient markets in scope, not just India. Confirmed live
# this session: phrase_related on a real seed yields 30-50 real,
# volume-backed keywords per database when the account's plan supports it
# (see api/search.py / fetchers/semrush_client.py).
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
