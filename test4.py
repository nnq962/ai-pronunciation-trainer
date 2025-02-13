import difflib

def highlight_mistakes(text1, text2):
    diff = difflib.ndiff(text1, text2)
    highlighted = []
    
    for d in diff:
        if d[0] == '-':  # Ký tự có trong text1 nhưng mất trong text2 (Bị xóa)
            highlighted.append(f"\033[91m{d[2]}\033[0m")  # Màu đỏ
        elif d[0] == '+':  # Ký tự có trong text2 nhưng không có trong text1 (Thêm sai)
            highlighted.append(f"\033[93m{d[2]}\033[0m")  # Màu vàng (để dễ phân biệt)
        else:
            highlighted.append(d[2])  # Ký tự giống nhau giữ nguyên

    return ''.join(highlighted)

# Test
text1 = "doʊnt ju wɔnt tɪ goʊ tɪ ðə ˈpɑrti?"   # Chuỗi đúng
text2 = "gʊd ˈmɔrnɪŋ, du ju wɔnt tɪ goʊ tɪ ðə ˈpɑrtiz?"  # Chuỗi sai

result = highlight_mistakes(text1, text2)
print(result)