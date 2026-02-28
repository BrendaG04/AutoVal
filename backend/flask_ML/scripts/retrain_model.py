"""
retrain_model.py — Retrain car price predictor on Craigslist vehicles.csv
Run: python retrain_model.py
"""
import os, re, pickle, warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import xgboost as xgb

warnings.filterwarnings("ignore")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT_YEAR = 2025
# For age computation during training, use the data collection year
# so that age=0 represents "brand new" in the training set.
# At prediction time we use the actual current year.
TRAINING_YEAR = 2021  # dataset was scraped ~2021

# ── 1. Load only needed columns ──
print("Loading data...")
USE_COLS = [
    "price", "year", "manufacturer", "model", "condition",
    "cylinders", "fuel", "odometer", "title_status",
    "transmission", "drive", "type",
]
df = pd.read_csv(os.path.join(BASE_DIR, "vehicles.csv"), usecols=USE_COLS, low_memory=False)
print(f"  Raw rows: {len(df):,}")

# ── 2. Clean ──
df = df.dropna(subset=["price", "year", "manufacturer", "model", "odometer"])
df["price"] = pd.to_numeric(df["price"], errors="coerce")
df["year"] = pd.to_numeric(df["year"], errors="coerce")
df["odometer"] = pd.to_numeric(df["odometer"], errors="coerce")
df = df.dropna(subset=["price", "year", "odometer"])

# Filter realistic ranges
df = df[(df["price"] >= 1000) & (df["price"] <= 100000)]
df = df[(df["year"] >= 2000) & (df["year"] <= CURRENT_YEAR)]
df = df[(df["odometer"] >= 0) & (df["odometer"] <= 300000)]
print(f"  After filtering: {len(df):,}")

# Normalize text columns
df["manufacturer"] = df["manufacturer"].str.strip().str.lower()
df["fuel"] = df["fuel"].fillna("gas").str.strip().str.lower()
df["transmission"] = df["transmission"].fillna("automatic").str.strip().str.lower()
df["drive"] = df["drive"].fillna("unknown").str.strip().str.lower()
df["type"] = df["type"].fillna("unknown").str.strip().str.lower()
df["condition"] = df["condition"].fillna("unknown").str.strip().str.lower()
df["title_status"] = df["title_status"].fillna("clean").str.strip().str.lower()
df["cylinders"] = df["cylinders"].fillna("unknown").str.strip().str.lower()

# ── 2b. Normalize model names to base model ──
TRIM_KEYWORDS = {
    # Standard trims
    "base", "le", "se", "xle", "xse", "ex", "lx", "dx", "sr", "sr5",
    "sxt", "gt", "st", "rs", "ss", "lt", "ls", "ltz", "sle", "slt",
    "sv", "sl", "fe", "gs", "gls", "gl", "dl", "ce", "im", "si",
    "sport", "limited", "touring", "premium", "luxury", "platinum",
    "titanium", "sel", "xlt", "laredo", "overland", "trailhawk",
    "rubicon", "sahara", "willys", "latitude", "altitude",
    # Trim packages & special editions
    "denali", "king", "ranch", "lariat", "raptor", "stx", "shelby",
    "boss", "z71", "z28", "z06", "nismo", "trd", "eddie", "bauer",
    "sho", "svt", "srt", "rt", "r/t", "hemi",
    "red", "black", "eddie bauer",
    # Drive & body
    "awd", "4wd", "fwd", "rwd", "4x4", "4x2", "2wd",
    "4dr", "2dr", "5dr", "3dr", "sedan", "coupe", "cpe",
    "hatchback", "wagon", "cab", "crew", "quad", "double", "regular",
    "4-door", "2-door", "4d", "2d", "suv", "sdn",
    # Engine/transmission
    "automatic", "manual", "cvt", "at", "mt",
    "v4", "v6", "v8", "i4", "i6", "4cyl", "6cyl", "8cyl",
    "hybrid", "turbo", "supercharged", "eco", "ecoboost",
    "dohc", "liter", "spd", "cylinder", "speed",
    "deisel", "duramax", "durmax", "cummins", "power", "stroke",
    "powerstroke", "hemi",
    # Features
    "navi", "navigation", "sunroof", "leather", "pkg", "package",
    "w/", "with", "w/o", "without",
    "natl", "auto", "gas", "diesel", "certified", "pre-owned",
    "dr", "door",
    # More trims
    "exl", "xl", "xls",
    "xdrive", "sdrive", "quattro", "4matic", "4motion",
    "off", "pro", "trail", "venture", "nightshade",
    "super", "work", "cargo", "van", "box", "truck",
    "full", "size", "mid", "mini",
    "clean", "title", "miles", "low", "runs",
    "great", "nice", "good", "like", "new", "only",
    # Extra trims that leak through
    "luxe", "pure", "pzev", "activ", "maxx", "police",
    "access", "single", "reg", "mega", "ext", "plus",
    "dually", "srw", "drw",
    "sd", "dump", "bus", "lifted",
    "energi", "plug-in",
    # 2-digit engine displacement codes
    "20", "24", "25", "30", "32", "35", "36", "37", "45", "50", "55",
    # Single-letter trims (e.g., "altima s", "escape s")
    "s", "l", "r", "n",
    # More specific trims
    "ses", "el", "max", "select", "koup", "custom",
    "cxl", "cx", "avenir", "xe", "pro-4x",
    "sle-1", "sle-2", "slt-1", "slt-2",
    "rtl", "type",
    "elite", "edge",
    "16", "18",
    # Additional trim words (round 3)
    "ultra", "tourx", "aero", "gxp", "lxs",
    "sx", "ti", "es", "sp",
    "scat", "pack",
    "p250", "p300", "p400",
    "cooper", "john", "works",
    "jk", "tj", "unlimi", "unlimited",
    "die", "hse", "local", "lots",
    "high", "tech",
    "spyder",
    "i", "ii", "iii", "iv",
    "cross", "country",
    "t6", "t5", "t8",
}

# Known multi-word base models (manufacturer → set of base names)
KNOWN_MODELS = {
    "lexus": {"is 200t", "is 250", "is 300", "is 350", "is 500",
              "es 250", "es 300", "es 300h", "es 330", "es 350",
              "gs 300", "gs 350", "gs 430", "gs 450h", "gs 460",
              "ls 430", "ls 460", "ls 500", "ls 500h",
              "rx 300", "rx 330", "rx 350", "rx 400h", "rx 450h",
              "nx 200t", "nx 300", "nx 300h",
              "gx 460", "gx 470", "lx 470", "lx 570",
              "rc 300", "rc 350", "rc 200t",
              "ux 200", "ux 250h", "lc 500",
              "ct 200h", "hs 250h", "sc 430"},
    "mercedes-benz": {"c 230", "c 250", "c 280", "c 300", "c 350", "c 400", "c 43", "c 63",
                       "e 300", "e 320", "e 350", "e 400", "e 450", "e 500", "e 550", "e 63",
                       "s 430", "s 500", "s 550", "s 560", "s 580", "s 600", "s 63",
                       "cl 550", "cl 600",
                       "sl 400", "sl 500", "sl 550", "sl 55",
                       "slk 250", "slk 300", "slk 350", "slc 300",
                       "cls 400", "cls 550", "cls 63",
                       "cla 250", "cla 45",
                       "gl 350", "gl 450", "gl 550",
                       "gla 250", "gla 45",
                       "glb 250",
                       "glc 300", "glc 43",
                       "gle 350", "gle 400", "gle 450", "gle 43", "gle 63",
                       "glk 250", "glk 350",
                       "gls 450", "gls 550", "gls 580", "gls 63",
                       "ml 320", "ml 350", "ml 500", "ml 550",
                       "r 350",
                       "a 220", "b 250"},
    "bmw": {"1 series", "2 series", "3 series", "4 series", "5 series",
            "6 series", "7 series", "8 series",
            "x1", "x2", "x3", "x4", "x5", "x6", "x7",
            "z3", "z4", "m3", "m4", "m5", "m6", "m8",
            "i3", "i4", "i8"},
    "land rover": {"range rover sport", "range rover evoque",
                   "range rover velar", "range rover",
                   "discovery sport"},
    "rover": {"range rover sport", "range rover evoque",
              "range rover velar", "range rover",
              "discovery sport"},
    "infiniti": {"q50", "q60", "q70", "qx30", "qx50", "qx56", "qx60", "qx70", "qx80"},
    "mazda": {"mx-5 miata", "cx-3", "cx-5", "cx-7", "cx-9"},
    "toyota": {"fj cruiser", "land cruiser", "prius prime", "prius v", "prius c",
               "mr2 spyder", "scion tc", "scion xb", "scion xa", "scion xd",
               "c-hr"},
    "honda": {"cr-v", "hr-v", "cr-z"},
    "chevrolet": {"monte carlo", "silverado 1500", "silverado 2500", "silverado 3500",
                  "express 1500", "express 2500", "express 3500",
                  "suburban 1500", "suburban 2500", "bolt ev", "spark ev",
                  "malibu maxx", "s-10"},
    "ford": {"crown victoria", "super duty", "transit connect",
             "c-max",
             "e-150", "e-250", "e-350", "e-series",
             "f-150", "f-250", "f-350", "f-450", "f-550", "f-650", "f-750",
             "five hundred"},
    "gmc": {"sierra 1500", "sierra 2500", "sierra 3500",
            "savana 2500", "savana 3500",
            "yukon xl"},
    "volkswagen": {"e-golf", "golf r", "golf gti", "new beetle"},
    "hyundai": {"santa fe"},
    "tesla": {"model s", "model 3", "model x", "model y"},
    "chrysler": {"town & country", "pt cruiser"},
    "subaru": {"wrx sti"},
    "mitsubishi": {"eclipse cross", "outlander phev"},
    "nissan": {"versa note", "titan xd", "gt-r"},
    "jaguar": {"f-pace", "f-type", "e-pace", "s-type", "x-type"},
    "jeep": {"grand cherokee", "wrangler unlimited"},
    "dodge": {"grand caravan", "sprinter 2500"},
    "fiat": {"124 spider"},
    "kia": {"niro ev", "soul ev"},
    "volvo": {"xc60", "xc70", "xc90", "xc40", "v60", "v70", "v50",
              "s60", "s80", "s90", "s40", "c30", "c70"},
    "cadillac": {"cts-v", "escalade esv"},
    "lincoln": {"town car", "mark lt"},
    "buick": {"park avenue", "encore gx"},
    "pontiac": {"grand am", "grand prix"},
    "mercury": {"grand marquis"},
    "mini": {"clubman", "countryman", "paceman", "roadster", "convertible", "hardtop"},
}

def normalize_model(manufacturer, raw_model):
    """Extract the base model name from messy Craigslist model text."""
    raw = str(raw_model).strip().lower()
    # Remove parenthetical content and special chars
    raw = re.sub(r'\(.*?\)', '', raw)
    raw = re.sub(r'[*#@!$%&/\\]', '', raw)
    # Remove leading years (e.g., "2014 accord" → "accord")
    raw = re.sub(r'^\d{4}\s+', '', raw)
    raw = raw.strip()
    if not raw:
        return ""

    # Brand-specific prefix stripping
    raw = re.sub(r'^lifted\s+', '', raw)
    if manufacturer == "mercedes-benz":
        raw = re.sub(r'^benz\s+', '', raw)
        raw = re.sub(r'^mercedes-amg\s*', '', raw)
        # Strip "-class X" patterns: "c-class c 300" → "c 300", "e-class" → ""
        raw = re.sub(r'^[a-z]{1,3}-class\s*', '', raw)
    if manufacturer == "ford":
        raw = re.sub(r'^super\s+duty\s+', '', raw)
    if manufacturer == "ram":
        raw = re.sub(r'^all-new\s+', '', raw)
    if manufacturer == "alfa-romeo":
        raw = re.sub(r'^romeo\s*', '', raw)
    if manufacturer == "rover":
        raw = re.sub(r'^rover\s+', '', raw)
    if manufacturer == "harley-davidson":
        raw = re.sub(r'^davidson\s*', '', raw)
    if manufacturer == "mini":
        raw = re.sub(r'^cooper\s+', '', raw)
    raw = raw.strip()
    if not raw:
        return ""

    # Check known multi-word models first
    if manufacturer in KNOWN_MODELS:
        for known in sorted(KNOWN_MODELS[manufacturer], key=len, reverse=True):
            if raw.startswith(known):
                return known

    tokens = raw.split()
    if not tokens:
        return raw

    # Skip if first token is a year
    if tokens[0].isdigit() and len(tokens[0]) == 4:
        tokens = tokens[1:]
        if not tokens:
            return ""

    result = [tokens[0]]

    for tok in tokens[1:]:
        clean = re.sub(r'[^a-z0-9\-]', '', tok)
        if not clean:
            break
        # Stop at trim keywords
        if clean in TRIM_KEYWORDS:
            break
        # Stop at pure numbers > 4 digits (likely year or VIN)
        if clean.isdigit() and len(clean) > 4:
            break
        # Keep numbers that look like model designators (150, 250, 350, etc.)
        if clean.isdigit() or re.match(r'^[a-z]?\d{2,4}$', clean):
            result.append(clean)
            break  # model number is typically the end of base model
        # Keep hyphenated model names (f-150, cr-v, rav-4)
        if '-' in clean and any(c.isdigit() for c in clean):
            result.append(clean)
            break
        # Keep short alpha tokens that look like model names
        if len(clean) <= 6 and clean.isalpha():
            result.append(clean)
            # If we have 2+ words already, likely enough
            if len(result) >= 3:
                break
        else:
            break

    return " ".join(result)


# Common spelling/format variations → canonical name
MODEL_ALIASES = {
    "toyota": {
        "4 runner": "4runner", "4- runner": "4runner", "4-runner": "4runner",
        "rav 4": "rav4", "rav-4": "rav4",
        "mr-2": "mr2", "mr2": "mr2 spyder",
        "fj": "fj cruiser",
        "camry solara": "solara", "corolla matrix": "matrix",
        "land": "land cruiser",
        "scion": "scion tc",
        "matrix s": "matrix", "matrix xr": "matrix",
        "sienna l": "sienna",
        "tacoma access": "tacoma", "tacoma lifted": "tacoma",
        "tundra 1794": "tundra",
        "yaris ia": "yaris", "yaris l": "yaris",
        "rav4 ev": "rav4",
        "prius four": "prius", "prius ii": "prius", "prius iv": "prius",
        "prius three": "prius", "prius two": "prius",
        "prius v three": "prius v", "prius v two": "prius v",
        "prius c four": "prius c",
        "prius prime plus": "prius prime",
    },
    "honda": {
        "cr-v": "cr-v", "cr v": "cr-v", "crv": "cr-v",
        "hr-v": "hr-v", "hr v": "hr-v", "hrv": "hr-v",
        "br-v": "br-v", "brv": "br-v",
        "civic type": "civic", "civic type r": "civic",
        "pilot elite": "pilot",
    },
    "nissan": {
        "rouge": "rogue",
        "versa note": "versa note", "versa note sv": "versa note",
        "370z nismo": "370z",
        "titan xd": "titan xd", "titan xd pro-4x": "titan xd",
        "titan xd single": "titan xd",
        "nv2500 hd": "nv2500",
    },
    "chevrolet": {
        "s10": "s-10", "s10 pickup": "s-10",
        "avalanche 1500": "avalanche",
        "silverado ext": "silverado 1500", "silverado hd": "silverado 2500",
        "silverado z71": "silverado 1500",
        "silverado": "silverado 1500",
        "tahoe 1500": "tahoe",
        "suburban z71": "suburban",
        "suburban 1500": "suburban", "suburban 2500": "suburban",
        "k1500": "silverado 1500", "c1500": "silverado 1500",
        "k2500": "silverado 2500", "c2500": "silverado 2500",
        "2500hd": "silverado 2500", "3500hd": "silverado 3500",
        "cc4500": "c4500",
        "corvette grand": "corvette",
        "express g2500": "express 2500", "express g3500": "express 3500",
        "express": "express 2500",
        "city": "cobalt", "crew": "silverado 1500",
        "duramax": "silverado 2500", "hd": "silverado 2500",
        "malibu maxx": "malibu",
    },
    "ford": {
        "f 150": "f-150", "f150": "f-150",
        "f 250": "f-250", "f250": "f-250",
        "f 350": "f-350", "f350": "f-350",
        "f 450": "f-450", "f450": "f-450",
        "f 550": "f-550", "f550": "f-550",
        "f 650": "f-650", "f650": "f-650",
        "f 750": "f-750", "f750": "f-750",
        "e150": "e-150", "e250": "e-250", "e350": "e-350",
        "e450": "e-450",
        "e-series cargo": "e-series", "e-350sd": "e-350",
        "econoline": "e-series", "econoline e250": "e-series", "econoline e350": "e-series",
        "cmax": "c-max", "c max": "c-max", "c": "c-max",
        "c-max energi": "c-max",
        "ranger edge": "ranger",
        "five": "five hundred", "500": "five hundred",
        "transit 150": "transit", "transit 250": "transit", "transit 350": "transit",
        "transit t150": "transit", "transit t250": "transit", "transit t350": "transit",
        "transit-250": "transit",
        "f150 king": "f-150", "f150 lariat": "f-150", "f150 raptor": "f-150", "f150 stx": "f-150",
        "f250 ext": "f-250", "f250 king": "f-250", "f250 lariat": "f-250",
        "f250 sd": "f-250", "f250sd": "f-250",
        "f350 deisel": "f-350", "f350 dually": "f-350", "f350 king": "f-350",
        "f350 lariat": "f-350", "f350 power": "f-350",
        "police": "explorer",
        "taurus x": "taurus",
    },
    "ram": {
        "pickup 1500": "1500", "pickup 2500": "2500", "pickup 3500": "3500",
        "cummins 2500": "2500", "cummins 3500": "3500", "cummins": "2500",
        "classic": "1500",
        "big horn": "1500", "bighorn": "1500", "big": "1500",
        "laramie": "1500", "lone star": "1500", "longhorn": "1500",
        "rebel": "1500", "tradesman": "1500", "express": "1500",
        "sxt": "1500", "slt": "1500", "sport": "1500",
        "crew": "1500", "quad": "1500", "limited": "1500",
        "outdoorsman": "1500", "st": "1500",
        "longhorn mega": "2500", "mega": "2500",
        "chassis": "3500", "chassis 3500": "3500",
        "hemi": "1500", "power": "2500",
        "4wd": "1500", "4x4": "1500",
        "6\"": "1500",
        "cargo": "promaster", "cv": "promaster city",
        "promaster 1500": "promaster", "promaster 2500": "promaster",
        "promaster 3500": "promaster",
        "reg": "1500", "regular": "1500",
        "diesel": "2500", "diesels": "2500", "deisel": "2500",
    },
    "bmw": {
        "1-series": "1 series", "2-series": "2 series",
        "3-series": "3 series", "4-series": "4 series",
        "5-series": "5 series", "6-series": "6 series",
        "7-series": "7 series", "8-series": "8 series",
        "128i": "1 series", "135i": "1 series",
        "320i": "3 series", "325ci": "3 series", "325i": "3 series", "325xi": "3 series",
        "328": "3 series", "328d": "3 series", "328i": "3 series", "328xi": "3 series",
        "330ci": "3 series", "330i": "3 series", "330xi": "3 series",
        "335i": "3 series", "335xi": "3 series",
        "428i": "4 series", "430i": "4 series", "435i": "4 series", "440xi": "4 series",
        "525i": "5 series", "528": "5 series", "528i": "5 series", "528xi": "5 series",
        "530i": "5 series", "530xi": "5 series",
        "535i": "5 series", "535i 6-spd": "5 series", "535xi": "5 series",
        "540i": "5 series", "550i": "5 series",
        "640i": "6 series", "645ci": "6 series", "650i": "6 series", "650xi": "6 series",
        "740i": "7 series", "750i": "7 series", "750i alpina": "7 series",
        "750li": "7 series", "750xi": "7 series",
    },
    "lexus": {
        "es300": "es 300", "es300h": "es 300h", "es330": "es 330", "es350": "es 350",
        "is200t": "is 200t", "is250": "is 250", "is300": "is 300", "is350": "is 350",
        "gs300": "gs 300", "gs350": "gs 350", "gs430": "gs 430",
        "ls430": "ls 430", "ls460": "ls 460",
        "rx300": "rx 300", "rx330": "rx 330", "rx350": "rx 350",
        "rx400h": "rx 400h", "rx450h": "rx 450h",
        "nx200t": "nx 200t", "nx300": "nx 300",
        "gx460": "gx 460", "gx470": "gx 470",
        "lx470": "lx 470", "lx570": "lx 570",
        "rc300": "rc 300", "rc350": "rc 350",
        "ct200h": "ct 200h", "ct": "ct 200h",
        "sc430": "sc 430", "sc": "sc 430",
        "hs": "hs 250h", "lx": "lx 570", "rc": "rc 350",
        "es": "es 350", "gs": "gs 350", "gx": "gx 460",
        "is": "is 350", "ls": "ls 460", "nx": "nx 300", "rx": "rx 350",
    },
    "mercedes-benz": {
        "c300": "c 300", "c230": "c 230", "c240": "c 300", "c250": "c 250", "c280": "c 300",
        "c320": "c 300", "c350": "c 350",
        "e350": "e 350", "e320": "e 320", "e500": "e 550", "e550": "e 550", "e300": "e 300",
        "s430": "s 430", "s500": "s 500", "s550": "s 550",
        "sl500": "sl 500", "sl550": "sl 550", "slk350": "slk 350", "slk": "slk 350",
        "clk320": "clk 320", "clk350": "clk 350", "clk": "clk 350",
        "cls": "cls 550",
        "ml350": "ml 350", "ml320": "ml 350", "ml500": "ml 350", "ml": "ml 350",
        "gl450": "gl 450", "gl550": "gl 450", "gl": "gl 450",
        "glc300": "glc 300", "glc": "glc 300",
        "gle350": "gle 350", "gle": "gle 350",
        "gla250": "gla 250", "gla": "gla 250",
        "glb": "glb 250",
        "glk350": "glk 350", "glk": "glk 350",
        "gls": "gls 450",
        "cla250": "cla 250", "cla": "cla 250",
        "cls550": "cls 550",
        "benz": "c 300", "electric": "eqc",
        "sprinter 2500": "sprinter", "sprinter 3500": "sprinter",
        "metris": "metris",
        "r350": "r 350",
        "a": "a 220", "b": "b 250",
        "c": "c 300", "e": "e 350",
    },
    "gmc": {
        "denali": "yukon",
        "sierra": "sierra 1500",
        "sierra denali": "sierra 1500",
        "sierra durmax 3500": "sierra 3500",
        "savana g2500": "savana 2500",
        "savana": "savana 2500",
        "tc5500": "c5500",
        "sonoma sls": "sonoma",
        "yukon denali": "yukon",
    },
    "volkswagen": {
        "golf gti": "gti", "golf gti s": "gti",
        "new beetle": "beetle",
        "golf tdi": "golf", "golf tsi": "golf",
        "jetta gli": "jetta", "jetta gls": "jetta", "jetta tdi": "jetta", "jetta tsi": "jetta",
        "passat tdi": "passat",
        "beetle tdi": "beetle",
        "atlas cross": "atlas",
        "touareg tdi": "touareg",
    },
    "mazda": {
        "2": "mazda2", "3": "mazda3", "3 i": "mazda3", "5": "mazda5", "6": "mazda6",
        "mazda3 i": "mazda3", "mazda3 s": "mazda3",
        "mazda5 grand": "mazda5",
        "mazda6 grand": "mazda6", "mazda6 i": "mazda6",
        "miata": "mx-5 miata", "miata mx-5": "mx-5 miata",
        "mx-5 miata club": "mx-5 miata", "mx-5 miata grand": "mx-5 miata",
        "mx-5 miata rf": "mx-5 miata",
        "cx9": "cx-9", "rx8": "rx-8",
        "mazdaspeed3": "mazda3",
    },
    "hyundai": {
        "sante fe": "santa fe", "sante": "santa fe",
        "genesis 38": "genesis",
    },
    "kia": {
        "forte koup": "forte", "forte5": "forte",
    },
    "infiniti": {
        "g": "g37", "g g37": "g37", "g35x": "g35", "g37x": "g37",
        "fx": "fx35",
        "jx": "jx35", "jx35": "jx35",
        "m35x": "m35",
        "m37x": "m37",
    },
    "audi": {
        "a3 tdi": "a3",
        "a4 avant": "a4",
        "a8 l": "a8", "a8l": "a8",
        "q5 tdi": "q5", "q7 tdi": "q7",
    },
    "subaru": {
        "b9": "tribeca", "b9 tribeca": "tribeca",
        "xv": "crosstrek", "xv crosstrek": "crosstrek",
        "forester x": "forester", "forester xt": "forester",
        "outback ll": "outback", "outback ll bean": "outback",
        "impreza wrx": "wrx", "impreza wrx sti": "wrx sti",
    },
    "chrysler": {
        "pt": "pt cruiser",
        "town": "town & country", "town and": "town & country",
        "town and country": "town & country", "town country": "town & country",
        "vmi": "town & country",
        "300-series": "300", "300c": "300", "300s": "300", "300m": "300",
    },
    "tesla": {
        "s": "model s", "3": "model 3", "x": "model x", "y": "model y",
    },
    "alfa-romeo": {
        "romeo": "giulia",
        "romeo giulia": "giulia",
        "giulia ti": "giulia",
        "romeo giulia ti": "giulia",
        "romeo stelvio": "stelvio",
        "stelvio ti": "stelvio",
    },
    "dodge": {
        "caravangrand": "grand caravan",
        "caravan": "grand caravan", "caravangr": "grand caravan",
        "grand": "grand caravan",
        "charger scat": "charger",
    },
    "fiat": {
        "500 abarth": "500", "500 pop": "500",
    },
    "jaguar": {
        "xj xjl": "xjl",
    },
    "jeep": {
        "grand": "grand cherokee",
        "wrangler all": "wrangler", "wrangler jk": "wrangler",
        "wrangler tj": "wrangler", "wrangler unlimi": "wrangler",
        "wrangler x": "wrangler",
    },
    "rover": {
        "range": "range rover",
        "range evoque": "range rover evoque",
        "evoque": "range rover evoque",
        "sport": "range rover sport",
        "sport die": "range rover sport",
        "velar": "range rover velar",
        "hse": "discovery",
        "lr4 hse": "lr4",
    },
    "mini": {
        "cooper": "hardtop", "base": "hardtop", "s": "hardtop",
        "clubman cooper": "clubman",
        "convertible cooper": "convertible",
        "countryman cooper": "countryman",
        "hardtop cooper": "hardtop", "hardtop john": "hardtop",
        "hardtop 2": "hardtop", "hardtop 4": "hardtop",
        "roadster cooper": "roadster",
    },
    "mercury": {
        "grand": "grand marquis",
    },
    "cadillac": {
        "cts4": "cts",
        "cts 36": "cts", "ct6 36": "ct6",
    },
    "lincoln": {
        "mark": "mark lt",
    },
    "volvo": {
        "certified": "",
        "v60 cross": "v60",
        "xc60 local": "xc60",
        "xc70 cross": "xc70",
        "xc90t6": "xc90",
    },
    "pontiac": {
        "solstice gxp": "solstice",
    },
    "mitsubishi": {
        "eclipse cross es": "eclipse cross",
        "eclipse cross sp": "eclipse cross",
        "eclipse spyder": "eclipse",
        "lancer es": "lancer",
        "mirage es": "mirage",
        "outlander es": "outlander",
    },
    "harley-davidson": {
        "davidson": "",
    },
    "buick": {
        "regal tourx": "regal",
    },
    "acura": {
        "mdx tech": "mdx", "tl tech": "tl",
    },
}

def apply_aliases(manufacturer, model_name):
    """Apply manufacturer-specific aliases to consolidate model names."""
    aliases = MODEL_ALIASES.get(manufacturer, {})
    return aliases.get(model_name, model_name)

print("Normalizing model names...")
df["model_raw"] = df["model"].str.strip().str.lower()
df["model"] = df.apply(lambda r: normalize_model(r["manufacturer"], r["model_raw"]), axis=1)
df["model"] = df.apply(lambda r: apply_aliases(r["manufacturer"], r["model"]), axis=1)

# Drop rows with empty model after normalization
df = df[df["model"].str.len() > 0]

# Show stats
n_raw = df["model_raw"].nunique()
n_clean = df["model"].nunique()
print(f"  Models before: {n_raw:,} → after: {n_clean:,}")

# For the dropdown, only keep models with enough data (MIN_LISTINGS)
MIN_LISTINGS = 15
model_counts = df.groupby(["manufacturer", "model"]).size()
popular_models = model_counts[model_counts >= MIN_LISTINGS].reset_index()[["manufacturer", "model"]]
popular_set = set(zip(popular_models["manufacturer"], popular_models["model"]))
n_popular = popular_models["model"].nunique()
print(f"  Models with {MIN_LISTINGS}+ listings (for dropdown): {len(popular_set):,}")

# Show examples
for mfr in ["toyota", "honda", "lexus", "ford", "bmw"]:
    models = sorted(popular_models[popular_models["manufacturer"] == mfr]["model"].tolist())
    print(f"  {mfr}: {models[:20]}")

# ── 3. Feature Engineering ──
# Use age instead of raw year (fixes extrapolation for 2023+ cars)
# Training age uses TRAINING_YEAR so age=0 = newest car in dataset
df["age"] = TRAINING_YEAR - df["year"]
df.loc[df["age"] < 0, "age"] = 0  # clamp any future-dated entries
df["miles_per_year"] = df["odometer"] / (df["age"] + 1)

# Cylinders → numeric
cyl_map = {
    "3 cylinders": 3, "4 cylinders": 4, "5 cylinders": 5,
    "6 cylinders": 6, "8 cylinders": 8, "10 cylinders": 10,
    "12 cylinders": 12, "other": 4, "unknown": 4,
}
df["cylinders_num"] = df["cylinders"].map(cyl_map).fillna(4).astype(int)

# Condition → ordinal
cond_map = {
    "new": 6, "like new": 5, "excellent": 4,
    "good": 3, "fair": 2, "salvage": 1, "unknown": 3,
}
df["condition_ord"] = df["condition"].map(cond_map).fillna(3).astype(int)

# Title status → binary
df["clean_title"] = (df["title_status"] == "clean").astype(int)

# ── 4. Target Encoding (manufacturer & model) ──
global_mean = df["price"].mean()
SMOOTHING = 50

def target_encode(series, target, smoothing=SMOOTHING):
    stats = target.groupby(series).agg(["mean", "count"])
    smoother = stats["count"] / (stats["count"] + smoothing)
    encoded = smoother * stats["mean"] + (1 - smoother) * global_mean
    return encoded.to_dict()

manufacturer_enc = target_encode(df["manufacturer"], df["price"])
df["mfr_model"] = df["manufacturer"] + "|" + df["model"]
model_enc = target_encode(df["mfr_model"], df["price"])

df["manufacturer_encoded"] = df["manufacturer"].map(manufacturer_enc).fillna(global_mean)
df["model_encoded"] = df["mfr_model"].map(model_enc).fillna(global_mean)

# ── 5. One-Hot Encoding ──
fuel_dummies = pd.get_dummies(df["fuel"], prefix="fuel")
trans_dummies = pd.get_dummies(df["transmission"], prefix="trans")
drive_dummies = pd.get_dummies(df["drive"], prefix="drive")

top_types = df["type"].value_counts().head(12).index.tolist()
df["type_clean"] = df["type"].where(df["type"].isin(top_types), "other")
type_dummies = pd.get_dummies(df["type_clean"], prefix="type")

# ── 6. Assemble Feature Matrix ──
# NOTE: no raw 'year' — only 'age' — so model generalizes to future years
numeric_features = ["odometer", "age", "miles_per_year",
                    "cylinders_num", "condition_ord", "clean_title",
                    "manufacturer_encoded", "model_encoded"]
X = pd.concat([df[numeric_features], fuel_dummies, trans_dummies,
               drive_dummies, type_dummies], axis=1)
y = df["price"]

feature_names = X.columns.tolist()
print(f"  Features: {len(feature_names)}")

# ── 7. Train/Test Split & Train ──
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.15, random_state=42
)

print("Training XGBoost...")
model = xgb.XGBRegressor(
    n_estimators=500,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=5,
    reg_alpha=1,
    reg_lambda=5,
    random_state=42,
    n_jobs=-1,
    tree_method="hist",
)
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=50,
)

# ── 8. Evaluate ──
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
print(f"\n  MAE:  ${mae:,.0f}")
print(f"  R²:   {r2:.4f}")

# Spot-check predictions
sample = X_test.sample(10, random_state=1)
sample_pred = model.predict(sample)
sample_actual = y_test.loc[sample.index]
print("\nSpot-check (Actual → Predicted):")
for a, p in zip(sample_actual, sample_pred):
    print(f"  ${a:>8,.0f} → ${p:>8,.0f}")

# ── 9. Save Model ──
model_json_path = os.path.join(BASE_DIR, "model", "car_price_model.json")
model.save_model(model_json_path)

# Build the bundle
unique_manufacturers = sorted(df["manufacturer"].unique().tolist())
# Only include models with enough listings for the dropdown
brands_models = (
    popular_models.groupby("manufacturer")["model"]
    .apply(lambda x: sorted(set(x.tolist())))
    .to_dict()
)
fuel_types = sorted(df["fuel"].unique().tolist())
transmissions = sorted(df["transmission"].unique().tolist())
conditions = ["new", "like new", "excellent", "good", "fair", "salvage"]
drive_types = sorted(df["drive"].dropna().unique().tolist())
vehicle_types = sorted(top_types)

fuel_columns = fuel_dummies.columns.tolist()
trans_columns = trans_dummies.columns.tolist()
drive_columns = drive_dummies.columns.tolist()
type_columns = type_dummies.columns.tolist()

bundle = {
    "model_path": "car_price_model.json",
    "feature_names": feature_names,
    "categories": {
        "manufacturers": unique_manufacturers,
        "brands_models": brands_models,
        "fuel_types": fuel_types,
        "transmissions": transmissions,
        "conditions": conditions,
        "drive_types": drive_types,
        "vehicle_types": vehicle_types,
    },
    "preprocessors": {
        "current_year": CURRENT_YEAR,
        "training_year": TRAINING_YEAR,
        "global_mean": float(global_mean),
        "manufacturer_encoder": manufacturer_enc,
        "model_encoder": model_enc,
        "cyl_map": cyl_map,
        "cond_map": cond_map,
        "price_cap": float(df["price"].quantile(0.99)),
        "fuel_columns": fuel_columns,
        "trans_columns": trans_columns,
        "drive_columns": drive_columns,
        "type_columns": type_columns,
        "top_types": top_types,
    },
}

pkl_path = os.path.join(BASE_DIR, "model", "car_price_predictor.pkl")
with open(pkl_path, "wb") as f:
    pickle.dump(bundle, f)

print(f"\n✅ Model saved to {model_json_path}")
print(f"✅ Bundle saved to {pkl_path}")
print(f"   Price cap (99th pctile): ${bundle['preprocessors']['price_cap']:,.0f}")
print(f"   Manufacturers: {len(unique_manufacturers)}")
print(f"   Unique models: {n_clean:,}")
total_models = sum(len(v) for v in brands_models.values())
print(f"   Total brand→model combos: {total_models:,}")
