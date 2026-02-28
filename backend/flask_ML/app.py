from flask import Flask, request, jsonify
import pickle
import logging
import pandas as pd
import xgboost as xgb
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ALLOWED_ORIGINS = set(
    os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
)

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": list(ALLOWED_ORIGINS)}},
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.after_request
def add_cors_headers(resp):
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
    resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp

# ── Load model bundle ──
with open(os.path.join(BASE_DIR, 'model', 'car_price_predictor.pkl'), 'rb') as f:
    model_bundle = pickle.load(f)

model = xgb.XGBRegressor()

raw_model_path = model_bundle.get('model_path', 'car_price_model.json')
candidate_paths = [
    raw_model_path,
    os.path.join(BASE_DIR, 'model', raw_model_path),
    os.path.join(BASE_DIR, raw_model_path),
    os.path.join(BASE_DIR, 'model', os.path.basename(raw_model_path)),
    os.path.join(BASE_DIR, os.path.basename(raw_model_path)),
]
resolved_model_path = next((p for p in candidate_paths if p and os.path.exists(p)), None)
if not resolved_model_path:
    raise FileNotFoundError(f"Could not find model file. Tried: {candidate_paths}")

model.load_model(resolved_model_path)

pp = model_bundle['preprocessors']

# ── Model name normalizer (must match training) ──
import re

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
    raw = re.sub(r'\(.*?\)', '', raw)
    raw = re.sub(r'[*#@!$%&/\\]', '', raw)
    raw = re.sub(r'^\d{4}\s+', '', raw)
    raw = raw.strip()
    if not raw:
        return ""

    # Brand-specific prefix stripping
    raw = re.sub(r'^lifted\s+', '', raw)
    if manufacturer == "mercedes-benz":
        raw = re.sub(r'^benz\s+', '', raw)
        raw = re.sub(r'^mercedes-amg\s*', '', raw)
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

    if manufacturer in KNOWN_MODELS:
        for known in sorted(KNOWN_MODELS[manufacturer], key=len, reverse=True):
            if raw.startswith(known):
                return known

    tokens = raw.split()
    if not tokens:
        return raw

    if tokens[0].isdigit() and len(tokens[0]) == 4:
        tokens = tokens[1:]
        if not tokens:
            return ""

    result = [tokens[0]]
    for tok in tokens[1:]:
        clean = re.sub(r'[^a-z0-9\-]', '', tok)
        if not clean:
            break
        if clean in TRIM_KEYWORDS:
            break
        if clean.isdigit() and len(clean) > 4:
            break
        if clean.isdigit() or re.match(r'^[a-z]?\d{2,4}$', clean):
            result.append(clean)
            break
        if '-' in clean and any(c.isdigit() for c in clean):
            result.append(clean)
            break
        if len(clean) <= 6 and clean.isalpha():
            result.append(clean)
            if len(result) >= 3:
                break
        else:
            break

    return " ".join(result)

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
    aliases = MODEL_ALIASES.get(manufacturer, {})
    return aliases.get(model_name, model_name)

@app.route('/api/car_options')
def get_car_options():
    try:
        cats = model_bundle['categories']
        return jsonify({
            "brands_models": cats['brands_models'],
            "fuel_types": cats['fuel_types'],
            "transmissions": cats['transmissions'],
            "conditions": cats['conditions'],
            "drive_types": cats['drive_types'],
            "vehicle_types": cats['vehicle_types'],
        })
    except Exception as e:
        logger.error(f"Error loading car options: {e}")
        return jsonify({"error": "Failed to load car options"}), 500

@app.route('/predict', methods=['POST', 'OPTIONS'])
@limiter.limit("30 per minute")
def predict():
    if request.method == 'OPTIONS':
        return ("", 204)

    try:
        data = request.get_json(silent=True) or {}

        odometer_raw = data.get('odometer', data.get('mileage', data.get('milage')))
        if odometer_raw in (None, ""):
            return jsonify({'error': 'Missing mileage/odometer', 'status': 'error'}), 400

        year = int(data.get('year', data.get('model_year', 0)))
        odometer = float(odometer_raw)

        # Input range validation
        import datetime
        current_year = datetime.datetime.now().year
        if year < 1900 or year > current_year + 2:
            return jsonify({'error': f'Year must be between 1900 and {current_year + 1}', 'status': 'error'}), 400
        if odometer < 0 or odometer > 1_000_000:
            return jsonify({'error': 'Mileage must be between 0 and 1,000,000', 'status': 'error'}), 400

        age = current_year - year
        if age < 0:
            age = 0
        miles_per_year = odometer / (age + 1)

        manufacturer = str(data.get('manufacturer', data.get('brand', ''))).strip().lower()
        car_model_raw = str(data.get('model', '')).strip().lower()
        car_model = normalize_model(manufacturer, car_model_raw)
        car_model = apply_aliases(manufacturer, car_model)
        fuel = str(data.get('fuel', data.get('fuel_type', 'gas'))).strip().lower()
        transmission = str(data.get('transmission', 'automatic')).strip().lower()
        drive = str(data.get('drive', 'unknown')).strip().lower()
        vehicle_type = str(data.get('type', 'unknown')).strip().lower()
        condition = str(data.get('condition', 'good')).strip().lower()
        cylinders = str(data.get('cylinders', '4 cylinders')).strip().lower()
        title_status = str(data.get('title_status', 'clean')).strip().lower()

        # Clean title binary
        clean_title_val = data.get('clean_title', None)
        if clean_title_val is not None:
            clean_title = 1 if clean_title_val else 0
        else:
            clean_title = 1 if title_status == 'clean' else 0

        # Cylinders → numeric
        cylinders_num = pp['cyl_map'].get(cylinders, 4)

        # Condition → ordinal
        condition_ord = pp['cond_map'].get(condition, 3)

        # Target-encoded manufacturer & model
        mfr_key = manufacturer
        model_key = f"{manufacturer}|{car_model}"
        global_mean = pp['global_mean']
        manufacturer_encoded = pp['manufacturer_encoder'].get(mfr_key, global_mean)
        model_encoded = pp['model_encoder'].get(model_key, global_mean)

        input_dict = {
            'odometer': odometer,
            'age': age,
            'miles_per_year': miles_per_year,
            'cylinders_num': cylinders_num,
            'condition_ord': condition_ord,
            'clean_title': clean_title,
            'manufacturer_encoded': manufacturer_encoded,
            'model_encoded': model_encoded,
        }

        # One-hot columns: fuel, transmission, drive, type
        for col in pp['fuel_columns']:
            input_dict[col] = 0
        fuel_col = f'fuel_{fuel}'
        if fuel_col in input_dict:
            input_dict[fuel_col] = 1

        for col in pp['trans_columns']:
            input_dict[col] = 0
        trans_col = f'trans_{transmission}'
        if trans_col in input_dict:
            input_dict[trans_col] = 1

        for col in pp['drive_columns']:
            input_dict[col] = 0
        drive_col = f'drive_{drive}'
        if drive_col in input_dict:
            input_dict[drive_col] = 1

        for col in pp['type_columns']:
            input_dict[col] = 0
        # Map to top types or 'other'
        if vehicle_type not in pp['top_types']:
            vehicle_type = 'other'
        type_col = f'type_{vehicle_type}'
        if type_col in input_dict:
            input_dict[type_col] = 1

        input_data = pd.DataFrame([input_dict])[model_bundle['feature_names']]

        prediction = model.predict(input_data)[0]
        prediction = max(prediction, 500)
        prediction = min(prediction, pp['price_cap'])

        return jsonify({
            'prediction': round(float(prediction), 2),
            'status': 'success',
        })

    except (ValueError, TypeError) as e:
        return jsonify({
            'error': 'Invalid input — check your values and try again.',
            'status': 'error'
        }), 400
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({
            'error': 'An unexpected error occurred. Please try again.',
            'status': 'error'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)