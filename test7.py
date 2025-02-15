import spacy

# Tải mô hình spaCy tiếng Anh
nlp = spacy.load("en_core_web_md")

# Ví dụ câu đầu tiên:
sentence = """k\u0259m \u0259nd mit \u02c8\u025bvri\u02ccw\u0259n!"""

# Tách từng từ (đơn giản nhất là split theo khoảng trắng)
# Nếu có dấu câu phức tạp, bạn có thể dùng các tokenizer chính quy (regex) hoặc
# tokenizer của spaCy để tách chính xác hơn.
words = sentence.split()

# Từ cần so sánh
target_word = "\u03b8\u00e6\u014bk"
doc_target = nlp(target_word)

# Tính độ tương đồng giữa target_word ("bus") với từng từ trong câu
similarities = []
for w in words:
    doc_w = nlp(w)
    score = doc_target.similarity(doc_w)
    similarities.append((w, score))

# Tìm từ có độ tương đồng cao nhất
best_word, best_score = max(similarities, key=lambda x: x[1])

# In kết quả
print("Từ có độ tương đồng cao nhất với '{}':".format(target_word))
print(" - Từ: '{}'".format(best_word))
print(" - Điểm similarity: {:.4f}".format(best_score))
