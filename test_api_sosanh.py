import requests

# URL của API
url = "https://subling.fly.dev/api/json/speaking/submissions?fields%5Bsubmission%5D=id%2Ctext%2Cwidget_url%2Caudio_url%2Clength%2Creference_id"


from mp3_to_base64Audio import process_audio_file_in_memory

base64_audio = process_audio_file_in_memory("test_4.mp3")

# Kiểm tra xem base64_audio đã có tiền tố chưa
if not base64_audio.startswith("data:"):
    audio_data = f"data:audio/mpeg;base64,{base64_audio}"
else:
    audio_data = base64_audio

# In kết quả
# print("AUDIO DATA:", audio_data)

# Header của yêu cầu
headers = {
    "accept": "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
}

# Dữ liệu của yêu cầu (phần audio sẽ thêm vào sau)
data = {
    "data": {
        "attributes": {
            "text": "Hello, how are you today?",
            "audio": audio_data
        }
    }
}

# Gửi yêu cầu POST
response = requests.post(url, headers=headers, json=data)

# In kết quả
print("Status Code:", response.status_code)
print("Response JSON:", response.json())