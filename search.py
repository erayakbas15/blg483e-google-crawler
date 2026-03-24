import os


DATA_DIR = os.path.join("data")
STORAGE_DIR = os.path.join(DATA_DIR, "storage")


def sanitize_query_word(value):
    if not value:
        return ""
    cleaned = []
    for ch in value.lower():
        if ("a" <= ch <= "z") or ("0" <= ch <= "9"):
            cleaned.append(ch)
    return "".join(cleaned)


def search_word(query):
    word = sanitize_query_word(query)
    if not word:
        return []

    shard = word[0].lower()
    if not ("a" <= shard <= "z"):
        shard = "_"
    path = os.path.join(STORAGE_DIR, f"{shard}.data")
    if not os.path.exists(path):
        return []

    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" ")
            if len(parts) != 5:
                continue
            w, url, origin, depth_raw, freq_raw = parts
            if w != word:
                continue
            try:
                depth = int(depth_raw)
                frequency = int(freq_raw)
            except ValueError:
                continue

            # CRITICAL required formula:
            score = (frequency * 10) + 1000 - (depth * 5)
            results.append(
                {
                    "word": w,
                    "url": url,
                    "origin": origin,
                    "depth": depth,
                    "frequency": frequency,
                    "score": score,
                }
            )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results
