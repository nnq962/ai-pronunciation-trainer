import re
from num2words import num2words

def convert_numbers_in_text(text):
    # Tìm tất cả các số trong văn bản
    numbers = re.findall(r'\d+', text)

    for num in numbers:
        # Chuyển số thành chữ
        word = num2words(int(num), lang='en')
        # Thay thế số bằng chữ trong chuỗi gốc
        text = text.replace(num, word, 1)  # Thay thế số đầu tiên tìm thấy

    return text

# Ví dụ đầu vào
text = "I need 500 dollars and 20 cents."

# Chuyển đổi
converted_text = convert_numbers_in_text(text)

print(converted_text)
