import json

# === 檔案路徑設定 ===
input_path = r"D:\lufu_allusion\data\processed\vocabularies\manual_parsed_results_tokens_ckip.json"
output_path = r"D:\lufu_allusion\data\processed\vocabularies\manual_parsed_results_tokens_ckip_reindexed.py.json"

# === 載入原始 JSON ===
with open(input_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# === 重編號邏輯（句組、句編號全篇唯一）===
for article in data:
    group_counter = 1
    sentence_counter = 1

    for para_index, para in enumerate(article.get("段落", []), start=1):
        para["段落編號"] = para_index

        for group in para.get("句組", []):
            group["句組編號"] = group_counter
            group_counter += 1

            for sentence in group.get("句子", []):
                sentence["句編號"] = sentence_counter
                sentence_counter += 1

# === 儲存為新 JSON 檔 ===
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"完成！全篇內部編號已調整（句組與句子不再因段落重啟），儲存至：{output_path}")
