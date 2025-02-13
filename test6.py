import difflib

def prune_text(reference, text, threshold=0.65):
    """
    Lược bỏ các từ thừa trong text dựa theo câu chuẩn reference.
    Các từ trong text có “sai sót” nhỏ so với từ tương ứng trong reference sẽ được giữ lại.
    
    Tham số:
        reference: chuỗi văn bản chuẩn (ví dụ: "Don't you want to go to the party?")
        text: chuỗi văn bản cần lược bỏ (ví dụ: "Good morning, Don't yau went this need remove to go to the perty? Thanks")
        threshold: ngưỡng so sánh (mặc định 0.65). Giá trị nằm trong [0,1]; càng gần 1 thì yêu cầu càng khắt khe.
    
    Trả về:
        Một chuỗi chỉ gồm các từ được giữ lại từ text theo thứ tự xuất hiện, phù hợp với reference.
    """
    # Tách câu thành các token (giả sử các từ cách nhau bằng khoảng trắng)
    ref_tokens = reference.split()
    text_tokens = text.split()
    
    output_tokens = []
    ref_idx = 0  # chỉ số hiện hành trong ref_tokens
    text_idx = 0  # chỉ số hiện hành trong text_tokens
    
    # Duyệt cho đến khi hết các từ của reference hoặc text
    while ref_idx < len(ref_tokens) and text_idx < len(text_tokens):
        ref_word = ref_tokens[ref_idx]
        candidate = text_tokens[text_idx]
        
        # So sánh 2 từ (không phân biệt chữ hoa chữ thường)
        similarity = difflib.SequenceMatcher(None, candidate.lower(), ref_word.lower()).ratio()
        
        if similarity >= threshold:
            # Nếu “gần giống” với từ chuẩn, giữ lại từ từ text
            output_tokens.append(candidate)
            ref_idx += 1  # chuyển sang từ tiếp theo của reference
        # Nếu không, bỏ qua candidate và kiểm tra từ sau
        text_idx += 1

    return " ".join(output_tokens)

# Ví dụ sử dụng:
text1 = "Don't you want to go to the party?"
text2 = "Good morning, Don't you went this need remove to go to the perty? Thanks"

result = prune_text(text1, text2)
print(result)