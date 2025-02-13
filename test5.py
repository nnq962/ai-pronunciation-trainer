import difflib

def highlight_differences(text1, text2):
    diff = list(difflib.ndiff(text1, text2))
    text1_highlighted = ""  # Hiển thị text1 với lỗi màu đỏ
    text2_highlighted = ""  # Hiển thị lỗi sai và thừa trong text2 màu vàng

    skip_next = False  # Biến để tránh ghi khoảng trắng thừa khi có ký tự thay thế

    for i in range(len(diff)):
        if skip_next:
            skip_next = False
            continue  # Bỏ qua ký tự tiếp theo nếu nó đã bị thay thế

        d = diff[i]

        if d[0] == '-':  # Ký tự có trong text1 nhưng mất trong text2 (bị sai)
            if i + 1 < len(diff) and diff[i + 1][0] == '+':  # Nếu ngay sau có ký tự `+` -> Thay thế
                text1_highlighted += f"\033[91m{d[2]}\033[0m"  # Màu đỏ (ký tự gốc)
                text2_highlighted += f"\033[93m{diff[i + 1][2]}\033[0m"  # Màu vàng (ký tự thay thế)
                skip_next = True  # Bỏ qua ký tự `+` tiếp theo vì đã xử lý
            else:  # Nếu không có `+`, tức là ký tự bị xóa
                text1_highlighted += f"\033[91m{d[2]}\033[0m"  # Màu đỏ
                text2_highlighted += " "  # Giữ căn chỉnh
        elif d[0] == '+':  # Ký tự có trong text2 nhưng không có trong text1 (thêm thừa)
            text1_highlighted += " "  # Giữ căn chỉnh
            text2_highlighted += f"\033[93m{d[2]}\033[0m"  # Màu vàng
        else:
            text1_highlighted += d[2]  # Ký tự đúng giữ nguyên
            text2_highlighted += d[2]  # Ký tự đúng giữ nguyên

    print("Text1 (chuẩn, sai tô đỏ):")
    print(text1_highlighted)
    print("\nText2 (sai & thừa tô vàng):")
    print(text2_highlighted)

# Test
text1 = "doʊnt ju wɔnt tɪ goʊ tɪ ðə ˈpɑrti?"   # Chuỗi đúng
text2 = "gʊd ˈmɔrnɪŋ. du ju wɔnt tɪ goʊ tɪ goodujra p ratyam?"  # Chuỗi sai

highlight_differences(text1, text2)