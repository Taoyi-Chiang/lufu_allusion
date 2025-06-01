import csv
import json
import re
import unicodedata
from pathlib import Path
from tqdm import tqdm

author_name = "王起"

# === 路徑設定 ===
TERMS_CSV_PATH     = Path(fr"D:/lufu_allusion/outputs/figures/manuel_term_matches_{author_name}.csv")
COMPARED_TEXT_PATH = Path(r"D:/lufu_allusion/data/raw/compared_text/")
OUTPUT_CSV_PATH    = Path(fr"D:/lufu_allusion/outputs/figures/term_ngram_match_{author_name}_results.csv")
MAIN_JSON_PATH     = Path(r"D:/lufu_allusion/data/processed/vocabularies/manual_parsed_results_tokens_ckip_reindexed.py.json")

# 用於切句的字元
CHARS_TO_REMOVE = "﹔。，、：；！？（）〔〕「」[]『』《》〈〉\\#\\-\\－\\(\\)\\[\\]\\]\\\\/ ,.:;!?~1234567890¶"
NGRAM_RANGE     = [2, 3, 4]

def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)

def extract_char_ngrams(chars: list, n: int) -> list:
    return ["".join(chars[i:i+n]) for i in range(len(chars)-n+1)]


# ----------------------------------------------------------------------------
# 0. 讀取「句級 match」CSV，只保留 author_name 的條目
# ----------------------------------------------------------------------------
sentence_level_matches = {}

with open(TERMS_CSV_PATH, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if (row.get("賦家") or "").strip() != author_name:
            continue

        mf = row.get("matched_file")
        if not mf or not mf.strip():
            continue

        author        = row.get("賦家", "").strip()
        article_title = row.get("賦篇", "").strip()
        para_no       = row.get("段落編號", "").strip()
        grp_no        = row.get("句組編號", "").strip()
        sent_no       = row.get("句編號", "").strip()

        matched_file  = mf.strip()
        matched_index = (row.get("matched_index") or "").strip()
        matched_text  = (row.get("matched") or "").strip()
        similarity    = (row.get("similarity") or "").strip()

        key = (author, article_title, para_no, grp_no, sent_no)
        ref = {
            "matched_file":   matched_file,
            "matched_index":  matched_index,
            "matched":        matched_text,
            "similarity":     similarity
        }
        sentence_level_matches.setdefault(key, []).append(ref)


# ----------------------------------------------------------------------------
# 1. 讀 main JSON 建立：
#    main_lookup: key=(author, article_title, para_no, grp_no, sent_no) → (篇號, 原始句)
#    sentence_order_map: 同 key → JSON 句子先後索引 (0-based)
# ----------------------------------------------------------------------------
main_lookup = {}
sentence_order_map = {}
order_counter = 0

with open(MAIN_JSON_PATH, 'r', encoding='utf-8') as f:
    main_data = json.load(f)

for essay in main_data:
    author        = str(essay.get("賦家", "")).strip()
    article_title = str(essay.get("賦篇", "")).strip()
    art_no        = str(essay.get("篇號", "")).strip()

    for para in essay.get("段落", []):
        para_no = str(para.get("段落編號", "")).strip()
        for grp in para.get("句組", []):
            grp_no = str(grp.get("句組編號", "")).strip()
            for sentence in grp.get("句子", []):
                sent_no       = str(sentence.get("句編號", "")).strip()
                orig_sentence = sentence.get("原始", "").strip()

                key = (author, article_title, para_no, grp_no, sent_no)
                main_lookup[key] = (art_no, orig_sentence)
                sentence_order_map[key] = order_counter
                order_counter += 1


# ----------------------------------------------------------------------------
# 2. 讀 TERMS_CSV_PATH，建立 hash_to_terms 供 n-gram 查找：  
#    - 只保留 author_name 的 token  
#    - 同時記錄每個 token 在原 CSV 的行號 "order"，以便後續排序  
# ----------------------------------------------------------------------------
hash_to_terms = {}
term_order = 0

with open(TERMS_CSV_PATH, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if (row.get("賦家") or "").strip() != author_name:
            continue

        token = (row.get("tokens") or "").strip()
        if not token:
            continue

        token_hash = hash(token) & 0x7FFFFFFFFFFFFFFF
        term_info = {
            "order":       term_order,
            "賦家":       (row.get("賦家") or "").strip(),
            "賦篇":       (row.get("賦篇") or "").strip(),
            "段落編號":   (row.get("段落編號") or "").strip(),
            "句組編號":   (row.get("句組編號") or "").strip(),
            "句編號":     (row.get("句編號") or "").strip(),
            "tokens":     token
        }

        hash_to_terms.setdefault(token_hash, []).append(term_info)
        term_order += 1

all_term_hashes = set(hash_to_terms.keys())


# ----------------------------------------------------------------------------
# 3. 掃描 compared_text，對尚未句級 match 的句子做 n-gram 比對（不再使用 stop words）
# ----------------------------------------------------------------------------
token_level_matches = {}

all_txt_files = list(COMPARED_TEXT_PATH.rglob("*.txt"))
for fp in tqdm(all_txt_files, desc="Scanning files", unit="file"):
    raw = normalize(fp.read_text(encoding='utf-8')).replace("\n", "")
    raw = re.sub(r"<[^>]*>", "", raw)
    segments = re.split(f"[{re.escape(CHARS_TO_REMOVE)}]", raw)

    for idx, seg in enumerate(segments):
        seg = normalize(seg).strip()
        if not seg:
            continue

        # 直接使用 normalize 後的 seg，不再移除前後停用詞
        cleaned = seg
        if not cleaned:
            continue
        if len(cleaned) < min(NGRAM_RANGE):
            continue

        # 計算該句所有 n-gram 的 hash
        seg_hashes = set()
        chars = list(cleaned)
        for n in NGRAM_RANGE:
            for gram in extract_char_ngrams(chars, n):
                g_hash = hash(gram) & 0x7FFFFFFFFFFFFFFF
                if g_hash in all_term_hashes:
                    seg_hashes.add(g_hash)

        # 對每個匹配到的 term_hash，可能對應多筆 term_info
        for term_hash in seg_hashes:
            for term_info in hash_to_terms[term_hash]:
                key_sentence = (
                    term_info["賦家"],
                    term_info["賦篇"],
                    term_info["段落編號"],
                    term_info["句組編號"],
                    term_info["句編號"]
                )

                # 如果該句已有句級 match，跳過 n-gram
                if key_sentence in sentence_level_matches:
                    continue

                author        = term_info["賦家"]
                article_title = term_info["賦篇"]
                para_no       = term_info["段落編號"]
                grp_no        = term_info["句組編號"]
                sent_no       = term_info["句編號"]
                tokens        = term_info["tokens"]
                order         = term_info["order"]

                art_no, orig_sentence = main_lookup.get(key_sentence, ("", ""))

                match_dict = {
                    "sentence_order":  sentence_order_map.get(key_sentence, 10**9),
                    "order":           order,
                    "篇號":            art_no,
                    "賦家":            author,
                    "賦篇":            article_title,
                    "段落編號":        para_no,
                    "句組編號":        grp_no,
                    "句編號":          sent_no,
                    "原始句":          orig_sentence,
                    "tokens":          tokens,
                    "matched_file":    f"{fp.parent.name}\\{fp.stem}",
                    "matched_index":   idx,
                    "matched":         cleaned,
                    "similarity":      "NA"
                }

                token_level_matches.setdefault(key_sentence, []).append(match_dict)


# ----------------------------------------------------------------------------
# 4. 合併所有句，僅遍歷屬於 author_name 的 key，按 JSON 先後順序：
#    1) 若有句級 match → 全部列出；
#    2) 否則若有 token-level match → 按 order 排序後列出；
#    3) 否則 → 空白列
# ----------------------------------------------------------------------------
matches = []

sorted_keys = sorted(
    [k for k in sentence_order_map.keys() if k[0] == author_name],
    key=lambda k: sentence_order_map[k]
)

for key_sentence in sorted_keys:
    author, article_title, para_no, grp_no, sent_no = key_sentence
    art_no, orig_sent = main_lookup.get(key_sentence, ("", ""))

    # (1) 句級 match
    if key_sentence in sentence_level_matches:
        for ref in sentence_level_matches[key_sentence]:
            matches.append({
                "篇號":         art_no,
                "賦家":         author,
                "賦篇":         article_title,
                "段落編號":     para_no,
                "句組編號":     grp_no,
                "句編號":       sent_no,
                "原始句":       orig_sent,
                "tokens":       "",
                "matched_file":   ref["matched_file"],
                "matched_index":  ref["matched_index"],
                "matched":        ref["matched"],
                "similarity":     ref["similarity"]
            })
        continue

    # (2) token-level match（按 order 排序）
    if key_sentence in token_level_matches:
        sorted_token_matches = sorted(
            token_level_matches[key_sentence],
            key=lambda x: x["order"]
        )
        for ref in sorted_token_matches:
            matches.append({
                "篇號":         ref["篇號"],
                "賦家":         ref["賦家"],
                "賦篇":         ref["賦篇"],
                "段落編號":     ref["段落編號"],
                "句組編號":     ref["句組編號"],
                "句編號":       ref["句編號"],
                "原始句":       ref["原始句"],
                "tokens":       ref["tokens"],
                "matched_file":   ref["matched_file"],
                "matched_index":  ref["matched_index"],
                "matched":        ref["matched"],
                "similarity":     ref["similarity"]
            })
        continue

    # (3) 無 match → 空白列
    matches.append({
        "篇號":         art_no,
        "賦家":         author,
        "賦篇":         article_title,
        "段落編號":     para_no,
        "句組編號":     grp_no,
        "句編號":       sent_no,
        "原始句":       orig_sent,
        "tokens":       "",
        "matched_file":   "",
        "matched_index":  "",
        "matched":        "",
        "similarity":     ""
    })


# ----------------------------------------------------------------------------
# 5. 輸出 CSV，僅包含中文欄位
# ----------------------------------------------------------------------------
csv_headers = [
    "篇號",
    "賦家",
    "賦篇",
    "段落編號",
    "句組編號",
    "句編號",
    "原始句",
    "tokens",
    "matched_file",
    "matched_index",
    "matched",
    "similarity"
]

OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8-sig') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
    writer.writeheader()
    for m in matches:
        writer.writerow({key: m.get(key, "") for key in csv_headers})

print(f"✅ Completed: {len(matches)} matches saved to {OUTPUT_CSV_PATH}")
