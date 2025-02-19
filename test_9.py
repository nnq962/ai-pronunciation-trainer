import csv

def clear_csv(file_path):
    """Xóa nội dung của tệp CSV."""
    open(file_path, 'w').close()

def write_repeated_text(file_path, text, repeat_count):
    """Ghi từ vào tệp CSV lặp lại repeat_count lần."""
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for _ in range(repeat_count):
            writer.writerow([text])

# Đường dẫn tệp CSV
file_path = 'databases/data_en.csv'

# Xóa nội dung tệp CSV
clear_csv(file_path)

# Ghi lại từ vào CSV 12,231 lần
write_repeated_text(file_path, 'A horse run quickly', 12231)

print(f"Hoàn thành ghi vào {file_path}")
