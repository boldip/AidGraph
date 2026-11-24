"""Display names for funders in the paper's tables (Table 2 and Extended Data Table 5):
the names used in the submitted Table 2, OCHA pooled-fund labels and a few shortening rules.
display(name, ref) returns a LaTeX-escaped string."""
import re

NAMES = {  # display names used in the submitted Table 2
    "Mott MacDonald Limited": "Mott MacDonald",
    "The William and Flora Hewlett Foundation": "Hewlett Foundation",
    "Aga Khan Foundation (United Kingdom)": "Aga Khan Foundation UK",
    "London School of Hygiene and Tropical Medicine": "London School of Hygiene \\& Tropical Medicine",
    "Gavi, the vaccine alliance": "Gavi, the Vaccine Alliance",
    "International Union for Conservation of Nature": "IUCN",
    "WYG International B.V.": "WYG International",
    "Stichting Woord en Daad": "Woord en Daad",
    "Cowater International Inc": "Cowater International",
    "ACTIONAID INTERNATIONAL KENYA": "ActionAid International Kenya",
    "SOS Children's Villages The Netherlands": "SOS Children's Villages Netherlands",
    "Ministry of Foreign Affairs - United Arab Emirates": "UAE Ministry of Foreign Affairs",
    "United States Agency for International Development": "USAID",
    "UK - Foreign, Commonwealth and Development Office": "UK FCDO",
    "GlobalGiving.org": "GlobalGiving",
}
CBPF = {"TCD": "Chad", "NER": "Niger", "BFA": "Burkina Faso", "PAK": "Pakistan", "NGA": "Nigeria",
        "SYR": "Syria", "YEM": "Yemen", "JOR": "Jordan", "UKR": "Ukraine", "PSE": "Palestine",
        "SOM": "Somalia", "SUD": "Sudan", "DRC": "DR Congo", "CAR": "Central African Republic",
        "ETH": "Ethiopia", "LBN": "Lebanon", "IRQ": "Iraq", "SSD": "South Sudan", "AFG": "Afghanistan",
        "MMR": "Myanmar", "VEN": "Venezuela", "MOZ": "Mozambique", "HTI": "Haiti", "COL": "Colombia"}


def display(name, ref):
    BYREF = {"XM-DAC-3-1": "Denmark MFA (Danida)", "US-GOV-1": "USAID", "GB-GOV-1": "UK FCDO",
             "US-EIN-300108263": "GlobalGiving", "US-GOV-11": "US Dept of State"}
    if ref in BYREF:
        return BYREF[ref]
    m = re.match(r"^XM-OCHA-CBPF-([A-Z]{3})\d*$", ref)
    if m:
        return f"OCHA Pooled Fund ({CBPF.get(m.group(1), m.group(1))})"
    if not isinstance(name, str):
        return ref
    if name in NAMES:
        return NAMES[name]
    n = name
    n = re.sub(r"^United States Department of", "US Dept of", n)
    n = re.sub(r"^United States ", "US ", n)
    n = re.sub(r"^UK - Department (of|for)", r"UK Dept \1", n)
    n = re.sub(r"^The University of", "University of", n)
    n = re.sub(r"^Sweden, through Swedish International Development.*", "Sida", n)
    n = re.sub(r"^Ireland - Department of Foreign Affairs.*", "Ireland Dept of Foreign Affairs", n)
    n = re.sub(r"^Netherlands - Ministry of Foreign Affairs.*", "Netherlands MFA", n)
    n = re.sub(r"^Ministry of Foreign Affairs - United Arab Emirates.*", "UAE Ministry of Foreign Affairs", n)
    n = re.sub(r"^International Development Law Organization.*", "International Development Law Organization", n)
    n = re.sub(r" \(D(HSC)?\)$|\s*\(.*\)$", "", n) if n.startswith("UK Dept") else n
    n = re.sub(r"\s+(Limited|Ltd\.?|Inc\.?|B\.V\.)$", "", n)
    n = n.replace(" and Industrial Strategy", " \\& Industrial Strategy")
    n = re.sub(r"^Wageningen University & Research.*", "Wageningen University \\& Research", n)
    n = re.sub(r"^WASTE advisers.*", "WASTE", n)
    n = re.sub(r"^UK Department for Energy, Security and Net Zero.*", "UK Dept for Energy Security \\& Net Zero", n)
    n = n.replace("&", "\\&") if "\\&" not in n else n
    return n.replace("%", "\\%").replace("_", "\\_").replace("#", "\\#").replace("$", "\\$")
