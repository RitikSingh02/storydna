"""Language / script detection (offline, no dependencies).

Script comes from Unicode ranges; Latin-script text is classified by function-word rates (English, Roman-script
Hindi "Hinglish", and a handful of European languages). It is a routing heuristic, not a language-ID model:
short or heavily code-mixed text can be misrouted, and the result always carries its evidence.
"""
from __future__ import annotations

import re
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# (script, first, last, language code assumed for that script, display name)
_SCRIPTS = [
    ("devanagari", 0x0900, 0x097F, "hi", "Hindi (Devanagari; Marathi/Nepali look the same)"),
    ("bengali", 0x0980, 0x09FF, "bn", "Bengali"), ("gurmukhi", 0x0A00, 0x0A7F, "pa", "Punjabi"),
    ("gujarati", 0x0A80, 0x0AFF, "gu", "Gujarati"), ("odia", 0x0B00, 0x0B7F, "or", "Odia"),
    ("tamil", 0x0B80, 0x0BFF, "ta", "Tamil"), ("telugu", 0x0C00, 0x0C7F, "te", "Telugu"),
    ("kannada", 0x0C80, 0x0CFF, "kn", "Kannada"), ("malayalam", 0x0D00, 0x0D7F, "ml", "Malayalam"),
    ("arabic", 0x0600, 0x06FF, "ar", "Arabic-script (Arabic/Urdu/Persian)"),
    ("arabic", 0x0750, 0x077F, "ar", "Arabic-script (Arabic/Urdu/Persian)"),
    ("cyrillic", 0x0400, 0x04FF, "ru", "Cyrillic (Russian etc.)"), ("greek", 0x0370, 0x03FF, "el", "Greek"),
    ("hebrew", 0x0590, 0x05FF, "he", "Hebrew"), ("thai", 0x0E00, 0x0E7F, "th", "Thai"),
    ("hangul", 0xAC00, 0xD7AF, "ko", "Korean"), ("kana", 0x3040, 0x30FF, "ja", "Japanese"),
    ("cjk", 0x4E00, 0x9FFF, "zh", "Chinese (or Japanese kanji)"),
]

_HINGLISH = set("""hai hain hota hoti hote tha thi the mein nahi nahin aur ko ke ki ka ne se jab wo woh uska uski uske apni
apne apna kar karke liye phir lekin kyunki jaata jaati deta deti karta karti karte raha rahi gaya gayi bhi sabke
saamne usne unhe usse isse kisi koi kuch par pe tak mat hum tum aap yeh iss uss wahan yahan bahut ab tab""".split())
_HINGLISH -= {"the", "par", "pe", "mat"}      # also ordinary English words

_OTHER = {
    "es": set("el la los las de del que y en un una es se por con para su al lo como pero sus le ya o este sí porque esta entre cuando muy sin sobre también me hasta hay donde quien desde todo nos durante".split()),
    "fr": set("le la les de des du un une et est en que qui dans pour pas sur au avec ce il elle se son sa ses ne plus par mais ou où comme aux cette ont été sont très".split()),
    "de": set("der die das und ist in den von zu mit sich des auf für nicht ein eine dem er sie es als auch an wird dass aber wie nach bei um noch durch nur oder wenn".split()),
    "pt": set("o a os as de do da dos das que e em um uma para com não se por mais mas como ao sua seu foi são à ele ela já também quando muito".split()),
    "it": set("il lo la i gli le di del della che e è un una per con non si da in al come ma più sono suo sua ha anche quando molto".split()),
    "id": set("yang dan di ke dari untuk dengan ini itu pada adalah tidak akan juga ada oleh saya dia mereka atau karena sebagai telah lebih dalam".split()),
    "tr": set("bir ve bu için ile de da çok daha ama gibi ne olarak ben sen o biz var yok değil kadar sonra çünkü".split()),
}
_NAMES = {"en": "English", "hi-Latn": "Hindi in Roman letters (Hinglish)", "es": "Spanish", "fr": "French",
          "de": "German", "pt": "Portuguese", "it": "Italian", "id": "Indonesian/Malay", "tr": "Turkish",
          "unknown": "unknown"}

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def detect_language(text: str) -> dict:
    """Return {code, name, script, confidence, evidence}. confidence is the share/rate that decided it (0-1)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return {"code": "unknown", "name": "unknown", "script": "none", "confidence": 0.0, "evidence": "no letters"}
    counts: dict[tuple[str, str, str], int] = {}
    latin = 0
    for c in letters:
        o = ord(c)
        if o < 0x250:
            latin += 1
            continue
        for script, a, b, code, name in _SCRIPTS:
            if a <= o <= b:
                counts[(script, code, name)] = counts.get((script, code, name), 0) + 1
                break
    n = len(letters)
    if counts:
        (script, code, name), k = max(counts.items(), key=lambda kv: kv[1])
        if k / n >= 0.4:
            if script in ("kana",) or (script == "cjk" and counts.get(("kana", "ja", "Japanese"), 0) > 0):
                code, name, script = "ja", "Japanese", "kana"
            return {"code": code, "name": name, "script": script, "confidence": round(k / n, 3),
                    "evidence": "%d of %d letters are %s" % (k, n, script)}
    words = [w.lower() for w in _WORD.findall(text)]
    if not words:
        return {"code": "unknown", "name": "unknown", "script": "latin", "confidence": 0.0, "evidence": "no words"}
    nw = len(words)
    en = sum(w in ENGLISH_STOP_WORDS for w in words) / nw
    hg = sum(w in _HINGLISH for w in words) / nw
    others = {c: sum(w in s for w in words) / nw for c, s in _OTHER.items()}
    best_other, orate = max(others.items(), key=lambda kv: kv[1])
    if nw >= 8 and hg >= 0.10 and hg >= 0.5 * en:
        return {"code": "hi-Latn", "name": _NAMES["hi-Latn"], "script": "latin", "confidence": round(hg, 3),
                "evidence": "%.0f%% Hindi function words vs %.0f%% English" % (hg * 100, en * 100)}
    if nw >= 8 and orate >= 0.18 and orate > 1.3 * en:
        return {"code": best_other, "name": _NAMES[best_other], "script": "latin", "confidence": round(orate, 3),
                "evidence": "%.0f%% %s function words vs %.0f%% English" % (orate * 100, _NAMES[best_other], en * 100)}
    if en >= 0.20 or nw < 8:
        return {"code": "en", "name": "English", "script": "latin", "confidence": round(en, 3),
                "evidence": "%.0f%% English function words" % (en * 100)}
    return {"code": "unknown", "name": "unknown (Latin script, few English function words)", "script": "latin",
            "confidence": round(en, 3), "evidence": "only %.0f%% English function words" % (en * 100)}
