from gtts import gTTS

def generate_audio_gtts(text, output_file):
    """
    Tạo tệp âm thanh từ văn bản sử dụng gTTS.
    Args:
        text (str): Văn bản cần chuyển thành âm thanh.
        output_file (str): Tên file âm thanh đầu ra.
    """
    tts = gTTS(text=text, lang='en')
    tts.save(output_file)
    print(f"Audio file saved as {output_file}")

# Tạo tệp âm thanh
generate_audio_gtts("Good morning, how many banana are in the table? Thanks", "test_4.mp3")

# Hello, how are you today?