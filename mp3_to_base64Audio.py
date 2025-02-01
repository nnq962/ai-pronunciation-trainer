from pydub import AudioSegment
import base64
import io
import requests
import os

def is_url(path_or_url):
    """
    Kiểm tra xem đầu vào có phải là URL không.
    Args:
        path_or_url (str): Đường dẫn hoặc URL.
    Returns:
        bool: True nếu là URL, False nếu không.
    """
    return path_or_url.startswith("http://") or path_or_url.startswith("https://")

def fetch_audio_from_url(url):
    """
    Tải tệp âm thanh từ URL.
    Args:
        url (str): Đường dẫn URL của tệp âm thanh.
    Returns:
        bytes: Dữ liệu âm thanh tải về.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return io.BytesIO(response.content)  # Trả về dạng file-like object
    except Exception as e:
        print(f"Error fetching audio from URL: {e}")
        return None

def convert_mp3_to_ogg_in_memory(mp3_path_or_url):
    """
    Chuyển đổi tệp MP3 sang OGG với codec libopus và trả về dữ liệu âm thanh dạng byte.
    Args:
        mp3_path_or_url (str): Đường dẫn hoặc URL đến tệp MP3.
    Returns:
        bytes: Dữ liệu âm thanh OGG.
    """
    try:
        if is_url(mp3_path_or_url):
            # Nếu là URL, tải tệp về
            mp3_data = fetch_audio_from_url(mp3_path_or_url)
            if mp3_data is None:
                return None
            audio = AudioSegment.from_file(mp3_data, format="mp3")
        else:
            # Nếu là đường dẫn cục bộ, đọc tệp MP3
            audio = AudioSegment.from_file(mp3_path_or_url, format="mp3")
        
        # Tạo buffer in-memory để lưu dữ liệu OGG
        ogg_buffer = io.BytesIO()
        # Xuất dữ liệu OGG vào buffer
        audio.export(ogg_buffer, format="ogg", codec="libopus")
        # Lấy dữ liệu byte từ buffer
        ogg_data = ogg_buffer.getvalue()
        ogg_buffer.close()
        return ogg_data
    except Exception as e:
        print(f"Error during conversion: {e}")
        return None

def encode_audio_to_base64(audio_data):
    """
    Mã hóa dữ liệu âm thanh thành chuỗi Base64.
    Args:
        audio_data (bytes): Dữ liệu âm thanh dạng byte.
    Returns:
        str: Chuỗi Base64 với header phù hợp.
    """
    try:
        base64_audio = base64.b64encode(audio_data).decode('utf-8')
        return f"data:audio/ogg;base64,{base64_audio}"
    except Exception as e:
        print(f"Error encoding audio data to Base64: {e}")
        return None

def process_audio_file_in_memory(mp3_path_or_url):
    """
    Xử lý tệp MP3: chuyển đổi sang OGG và mã hóa Base64 trực tiếp trong bộ nhớ.
    Args:
        mp3_path_or_url (str): Đường dẫn hoặc URL đến tệp MP3 đầu vào.
    Returns:
        str: Chuỗi Base64 nếu thành công, None nếu thất bại.
    """
    # Chuyển đổi MP3 sang OGG trong bộ nhớ
    ogg_data = convert_mp3_to_ogg_in_memory(mp3_path_or_url)
    if ogg_data is not None:
        # Mã hóa Base64
        return encode_audio_to_base64(ogg_data)
    return None