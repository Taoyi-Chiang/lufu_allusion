import json
import csv
import os
from collections import defaultdict

# === 設定目標賦家 ===
target_author = "王起"

# === 檔案路徑 ===
main_json_path = r"D:\lufu_allusion\data\processed\vocabularies\manual_parsed_results_tokens_ckip_reindexed.py.json"
match_json_path = r"D:\lufu_allusion\data\processed\ALL_match_results_jaccard.json"
output_json_path = fr"D:\lufu_allusion\data\processed\vocabularies\with_all_match_refs_{target_author}.json"
output_csv_path = fr"D:\lufu_allusion\outputs\figures\sentence_matches_{target_author}.csv"

# === 確保輸出資料夾存在 ===
os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)

# === 載入主檔 JSON ===
with open(main_json_path, "r", encoding="utf-8") as f:
    main_data = json.load(f)

# === 載入 match 檔並建立索引表 {(article_num, sentence_num): [match_dict]} ===
with open(match_json_path, "r", encoding="utf-8") as f:
    match_data = json.load(f)

match_map = defaultdict(list)
for m in match_data:
    if m["author"] != target_author:
        continue
    key = (m["article_num"], m["sentence_num"])
    match_map[key].append({
        "matched_file": m["matched_file"],
        "matched_index": m["matched_index"],
        "matched": m["matched"],
        "similarity": m["similarity"]
    })

# === 合併 matched_refs，僅保留目標賦家的資料 ===
filtered_data = []
for article in main_data:
    if article.get("賦家") != target_author:
        continue
    article_num = article.get("篇號")
for para in article.get("段落", []):
    if para.get("missing", False):
        print(f"⛔ 跳過缺字段落：篇號 {article.get('篇號')}，段落編號 {para.get('段落編號')}")
        continue
    for group in para.get("句組", []):
        for sentence in group.get("句子", []):
            key = (article_num, sentence["句編號"])
            if key in match_map:
                sentence["matched_refs"] = match_map[key]
    filtered_data.append(article)

# === 儲存整合後 JSON ===
with open(output_json_path, "w", encoding="utf-8") as f:
    json.dump(filtered_data, f, ensure_ascii=False, indent=2)

print(f"✅ JSON 整合完成：{output_json_path}")

# === 攤平 CSV ===
rows = []

for article in filtered_data:
    article_num = article["篇號"]
    author = article["賦家"]
    title = article["賦篇"]

for para in article["段落"]:
    para_num = para["段落編號"]
    if para.get("missing", False):
        print(f"⛔ 跳過缺字段落（攤平略過）：篇號 {article_num}，段落編號 {para_num}")
        continue
    for group in para.get("句組", []):
        group_num = group["句組編號"]
        for sentence in group.get("句子", []):
            sent_num = sentence["句編號"]
            original = sentence["原始"]
            tokens = " ".join(sentence["tokens"])
            matched_refs = sentence.get("matched_refs", [])

            if matched_refs:
                for ref in matched_refs:
                    rows.append([
                        article_num, author, title,
                        para_num, group_num, sent_num,
                            original, tokens,
                            ref["matched_file"],
                            ref["matched_index"],
                            ref["matched"],
                            ref["similarity"]
                        ])
                else:
                    rows.append([
                        article_num, author, title,
                        para_num, group_num, sent_num,
                        original, tokens,
                        "", "", "", ""
                    ])

# === 輸出 CSV ===
with open(output_csv_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow([
        "篇號", "賦家", "賦篇", "段落編號", "句組編號", "句編號",
        "原始句", "tokens",
        "matched_file", "matched_index", "matched", "similarity"
    ])
    writer.writerows(rows)

print(f"📄 已輸出完整平坦化 CSV：{output_csv_path}")
