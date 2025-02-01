from flask import Flask, render_template, request, jsonify
import webbrowser
import os
from flask_cors import CORS
import json
import uuid

import lambdaTTS
import lambdaSpeechToScore
import lambdaGetSample
from mp3_to_base64Audio import process_audio_file_in_memory
from urllib.parse import urlparse

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = '*'

rootPath = ''
results = {}  # Dictionary lưu trữ kết quả tạm thời

def is_valid_url(url):
    """Kiểm tra xem chuỗi có phải là URL hợp lệ không."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

# ----------------------------------------------------------------
@app.route(rootPath+'/')
def main():
    return render_template('main.html')

# ----------------------------------------------------------------
@app.route(rootPath+'/getAudioFromText', methods=['POST'])
def getAudioFromText():
    event = {'body': json.dumps(request.get_json(force=True))}
    return lambdaTTS.lambda_handler(event, [])

# ----------------------------------------------------------------
@app.route(rootPath+'/getSample', methods=['POST'])
def getNext():
    event = {'body':  json.dumps(request.get_json(force=True))}
    return lambdaGetSample.lambda_handler(event, [])

# ----------------------------------------------------------------
@app.route(rootPath+'/GetAccuracyFromRecordedAudio', methods=['POST'])
def GetAccuracyFromRecordedAudio():

    try:
        event = {'body': json.dumps(request.get_json(force=True))}
        lambda_correct_output = lambdaSpeechToScore.lambda_handler(event, [])
    except Exception as e:
        print('Error: ', str(e))
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Credentials': "true",
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': ''
        }

    return lambda_correct_output

# ----------------------------------------------------------------
@app.route(rootPath + '/GetAccuracyFromRecordedAudio2', methods=['POST'])
def get_accuracy_from_recorded_audio2():
    try:
        # Lấy dữ liệu từ request
        data = request.get_json(force=True)
        mp3_path = data.get('mp3_path', None)  # Đường dẫn file MP3
        title = data.get('title', 'Untitled')  # Tiêu đề (mặc định là "Untitled")
        language = data.get('language', 'en')  # Ngôn ngữ (mặc định là "en")

        # Kiểm tra tệp MP3 hoặc URL
        if not mp3_path:
            return jsonify({"status": "error", "message": "Missing mp3_path."})

        if not os.path.exists(mp3_path) and not mp3_path.startswith("http"):
            return jsonify({"status": "error", "message": "Invalid mp3_path. Provide a valid file path or URL."})

        # Xử lý tệp MP3 và chuyển đổi sang Base64
        base64_audio = process_audio_file_in_memory(mp3_path)
        if not base64_audio:
            return jsonify({"status": "error", "message": "Failed to process audio file."})

        # Chuẩn bị payload cho lambdaSpeechToScore
        event = {
            'body': json.dumps({
                'base64Audio': base64_audio,
                'title': title,
                'language': language
            })
        }

        # Gọi hàm lambda để xử lý dữ liệu
        lambda_correct_output = lambdaSpeechToScore.lambda_handler(event, [])

        # Tạo UUID duy nhất cho yêu cầu này
        request_id = str(uuid.uuid4())

        # Lưu kết quả đầy đủ vào `results`
        results[request_id] = {
            "status": "success",
            "request_id": request_id,
            "data": lambda_correct_output
        }

        # Trả về kết quả JSON
        return jsonify(results[request_id])

    except Exception as e:
        print('Error:', str(e))
        return jsonify({"status": "error", "message": f"Error processing request: {str(e)}"})

# ----------------------------------------------------------------
# Route hiển thị giao diện
@app.route(rootPath + '/view/<request_id>')
def view_result(request_id):
    try:
        # Lấy kết quả dựa trên UUID
        result = results.get(request_id)
        if not result:
            return "Result not found or expired.", 404

        # Nếu kết quả là chuỗi JSON, chuyển thành dictionary
        if isinstance(result, str):
            result = json.loads(result)

        # Kiểm tra trạng thái của kết quả
        if result.get("status") != "success":
            return f"Error: {result.get('message', 'Unknown error')}", 500

        # Trích xuất và giải mã dữ liệu phát âm
        raw_data = result.get("data")
        if isinstance(raw_data, str):  # Nếu raw_data là chuỗi JSON, giải mã nó
            raw_data = json.loads(raw_data)

        if not raw_data:
            return "No pronunciation data available.", 404

        # Xử lý bôi đỏ
        highlighted_text = process_highlighted_text(
            raw_data['real_transcripts'],
            raw_data['is_letter_correct_all_words']
        )

        # Hiển thị giao diện với dữ liệu
        return render_template('index.html', data=raw_data, highlighted_text=highlighted_text)

    except Exception as e:
        print(f"Error occurred: {e}")  # Log lỗi chi tiết
        return f"Internal Server Error: {e}", 500

# ----------------------------------------------------------------
# Hàm xử lý bôi đỏ
def process_highlighted_text(real_transcripts, is_letter_correct):
    highlighted_text = ""
    is_correct_list = is_letter_correct.split()
    words = real_transcripts.split()

    for word, correctness in zip(words, is_correct_list):
        for char, is_correct in zip(word, correctness):
            if is_correct == "0":
                highlighted_text += f'<span class="highlight">{char}</span>'
            else:
                highlighted_text += char
        highlighted_text += " "

    return highlighted_text.strip()


if __name__ == "__main__":
    language = 'en'
    print(os.system('pwd'))
    # webbrowser.open_new('http://127.0.0.1:3000/')
    app.run(host="0.0.0.0", port=3000, debug=True)
