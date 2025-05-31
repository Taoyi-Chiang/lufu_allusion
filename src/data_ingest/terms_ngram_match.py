import csv
import json
import re
import unicodedata
from pathlib import Path
from tqdm import tqdm

author_name = "王起"  # Set the author name for the output file

# === User configuration ===
TERMS_CSV_PATH = Path(fr"D:/lufu_allusion/outputs/figures/term_matches_{author_name}.csv")
COMPARED_TEXT_PATH = Path(r"D:/lufu_allusion/data/raw/compared_text/")
OUTPUT_JSON_PATH = Path(fr"D:/lufu_allusion/data/processed/term_ngram_match_{author_name}_results.json")
CHARS_TO_REMOVE = "﹔。，、：；！？（）〔〕「」[]『』《》〈〉\\#\\-\\－\\(\\)\\[\\]\\]\\\\/ ,.:;!?~1234567890¶"
NGRAM_RANGE = [2, 3, 4]

# === Stopword lists and cleaning rules ===
PREFIX_EXCLUDE = [
    "徒觀其", "矞夫", "矞乃", "至夫", "懿夫", "蓋由我君", "重曰", "是知", "嗟夫", "夫其", "懿其", "所以",
    "想夫", "其始也", "當其", "況復", "時則", "至若", "豈獨", "若乃", "今則", "乃知", "既而", "嗟乎",
    "故我后", "觀夫", "然而", "爾乃", "是以", "原夫", "曷若", "斯則", "於時", "方今", "亦何必", "若然",
    "客有", "至於", "則知", "且夫", "斯乃", "況", "於是", "覩夫", "且彼", "豈若", "已而", "始也", "故",
    "然則", "豈如我", "豈不以", "我國家", "其工者", "所謂", "今吾君", "及夫", "爾其", "將以", "可以", "今",
    "國家", "然後", "向非我后", "則有", "彼", "惜乎", "由是", "乃言曰", "若夫", "亦何用", "不然",
    "嘉其", "今則", "徒美夫", "故能", "有探者曰", "惜如", "而況", "逮夫", "誠夫", "於戲", "洎乎", "伊昔",
    "則將", "今則", "況今", "士有", "暨乎", "亦何辨夫", "俾夫", "亦猶", "瞻夫", "時也", "固知", "足以",
    "矞國家", "比乎", "亦由", "觀其", "將俾乎", "聖人", "君子", "於以", "乃", "斯蓋", "噫", "夫惟",
    "高皇帝", "帝既", "嘉其", "始則", "又安得", "其", "儒有", "當是時也", "夫然", "宜乎", "故其", "國家",
    "爾其始也", "今我國家", "是時", "有司", "向若", "我皇", "故王者", "則", "鄒子", "孰", "暨夫", "用能",
    "故將", "況其", "故宜", "王者", "聖上", "先王", "乃有", "況乃", "別有", "今者", "固宜", "皇上", "且其",
    "徒觀夫", "帝堯以", "始其", "倏而", "乃曰", "向使", "漢武帝", "先是", "他日", "乃命", "觀乎", "國家以",
    "墨子", "借如", "足以", "上乃", "嗚呼", "昔伊", "先賢", "遂使", "豈比夫", "固其", "況有", "魯恭王", "皇家",
    "吾君是時", "知", "周穆王", "則有", "是用", "乃言曰", "及", "故夫", "矞乎", "夫以", "寧令", "如", "然則",
    "滅明乃", "遂", "悲夫", "安得", "故得", "且見其", "是何", "莫不", "士有", "知其", "未若"
]
SUFFIX_EXCLUDE = [
    "曰", "哉", "矣", "也", "矣哉", "乎", "焉", "者也", "也矣哉"
]

# Normalize and clean text functions

def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def clean_sentence(text: str) -> str:
    for prefix in PREFIX_EXCLUDE:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    for suffix in SUFFIX_EXCLUDE:
        if text.endswith(suffix):
            return text[:-len(suffix)].strip()
    return text.strip()

# Extract character-level n-grams from a list of characters
def extract_char_ngrams(chars: list, n: int) -> list:
    return ["".join(chars[i:i+n]) for i in range(len(chars)-n+1)]

# === Load terms from CSV and build hash-to-term mapping ===
terms = []
hash_to_terms = {}

with open(TERMS_CSV_PATH, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        token = row.get("tokens", "").strip()
        if not token:
            continue
        # Compute hash once per token
        token_hash = hash(token) & 0x7FFFFFFFFFFFFFFF
        term_info = {
            "article_num": row.get("篇號"),
            "author": row.get("賦家"),
            "article_title": row.get("賦篇"),
            "paragraph_num": row.get("段落編號"),
            "group_num": row.get("句組編號"),
            "sentence_num": row.get("句編號"),
            "original": row.get("原始句"),
            "tokens": token
        }
        if token_hash not in hash_to_terms:
            hash_to_terms[token_hash] = []
        hash_to_terms[token_hash].append(term_info)

# Pre-calc set of all term hashes for O(1) lookup
all_term_hashes = set(hash_to_terms.keys())

# === Scan compared_text folder, split into segments, clean, and match on the fly ===
matches = []

all_txt_files = list(COMPARED_TEXT_PATH.rglob("*.txt"))
for fp in tqdm(all_txt_files, desc="Scanning files", unit="file"):
    raw = normalize(fp.read_text(encoding='utf-8').replace("\n", ""))
    raw = re.sub(r"<[^>]*>", "", raw)
    segments = re.split(f"[{re.escape(CHARS_TO_REMOVE)}]", raw)

    for idx, seg in enumerate(segments):
        seg = normalize(seg).strip()
        if not seg:
            continue
        cleaned = clean_sentence(seg)
        if not cleaned:
            continue
        # Skip segments shorter than smallest n-gram (2 chars)
        if len(cleaned) < min(NGRAM_RANGE):
            continue

        # Collect this segment's matching term hashes
        seg_hashes = set()
        chars = list(cleaned)
        for n in NGRAM_RANGE:
            for gram in extract_char_ngrams(chars, n):
                g_hash = hash(gram) & 0x7FFFFFFFFFFFFFFF
                if g_hash in all_term_hashes:
                    seg_hashes.add(g_hash)

        # For each matching term hash, record all term entries and current segment
        for term_hash in seg_hashes:
            for term_info in hash_to_terms[term_hash]:
                matches.append({
                    **term_info,
                    "matched_file": str(fp.relative_to(COMPARED_TEXT_PATH.parent)),
                    "matched_index": idx,
                    "matched": seg,
                    "similarity": "NA"
                })

# === Reorganize matches into hierarchical structure ===
# Group by article_num > paragraph_num > group_num > sentence_num
hierarchy = {}
for m in matches:
    art = m["article_num"]
    para = m["paragraph_num"]
    grp = m["group_num"]
    sent = m["sentence_num"]
    hierarchy.setdefault(art, {}).setdefault(para, {}).setdefault(grp, {}).setdefault(sent, []).append({
        "tokens": m["tokens"],
        "matched_file": m["matched_file"],
        "matched_index": m["matched_index"],
        "matched": m["matched"],
        "similarity": m["similarity"]
    })

# === Output hierarchical JSON ===
OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(hierarchy, f, ensure_ascii=False, indent=2)

print(f"✅ Completed: {len(matches)} matches saved hierarchically to {OUTPUT_JSON_PATH}")
