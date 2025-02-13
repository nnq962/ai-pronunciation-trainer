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
import utils

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = '*'

rootPath = ''
results = {}  # Dictionary lưu trữ kết quả tạm thời

# ----------------------------------------------------------------
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
@app.route(rootPath + '/view/<request_id>')
def view_result(request_id):
    try:
        # Lấy tham số để kiểm tra người dùng có muốn nhận JSON không
        response_format = request.args.get("format", "html").lower()

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

        # Trích xuất thông tin cần thiết
        real_transcripts = raw_data.get("real_transcripts")
        ipa_transcript = raw_data.get("ipa_transcript")
        real_transcripts_ipa = raw_data.get("real_transcripts_ipa")
        matched_transcripts_ipa = raw_data.get("matched_transcripts_ipa")
        is_letter_correct_all_words = raw_data.get("is_letter_correct_all_words")
        pronunciation_accuracy = raw_data.get("pronunciation_accuracy")
        pair_accuracy_category = raw_data.get("pair_accuracy_category")

        if not raw_data:
            return "No pronunciation data available.", 404

        # Xử lý dữ liệu màu sắc
        result_1 = utils.process_line_1(real_transcripts, is_letter_correct_all_words)
        result_2 = utils.process_line_2_v3(real_transcripts_ipa, ipa_transcript)
        result_3, error_count = utils.process_line_3_v2(real_transcripts_ipa, ipa_transcript)

        print("-" * 80)
        print("Original pronunciation_accuracy:", pronunciation_accuracy)

        # Điều chỉnh điểm phát âm
        pronunciation_accuracy = int(pronunciation_accuracy)
        adjusted_score = max(pronunciation_accuracy - (error_count * 10), 0)

        line1 = utils.convert_highlighted_text_to_json(highlighted_text=utils.convert_color_style_to_class(result_1), key_name="Real transcript")
        line2 = utils.convert_highlighted_text_to_json(highlighted_text=result_2, key_name="Real transcripts ipa")
        line3 = utils.convert_highlighted_text_to_json(highlighted_text=result_3, key_name="Your transcripts ipa")
        line4 = {"Pronunciation Accuracy": adjusted_score}

        # Chuyển đổi từ JSON string thành dictionary (Python object)
        json_line1 = json.loads(line1)
        json_line2 = json.loads(line2)
        json_line3 = json.loads(line3)

        # Gộp tất cả vào một dictionary
        final_json = {
            **json_line1,
            **json_line2,
            **json_line3,
            **line4
        }

        print("-" * 80)
        print("✅ Final JSON Data Generated!")

        # Nếu người dùng yêu cầu JSON, trả về JSON thay vì hiển thị HTML
        if response_format == "json":
            return jsonify(final_json)  # Trả về JSON trực tiếp

        # Hiển thị giao diện với dữ liệu
        return render_template(
            "result.html",
            colored_words=result_1,
            corrected_ipa=result_2,
            highlighted_ipa=result_3,
            pronunciation_accuracy=adjusted_score
        )
    
    except Exception as e:
        print(f"Error occurred: {e}")  # Log lỗi chi tiết
        return f"Internal Server Error: {e}", 500

if __name__ == "__main__":
    language = 'en'
    print(os.system('pwd'))
    # webbrowser.open_new('http://127.0.0.1:3000/')
    app.run(host="0.0.0.0", port=3000, debug=True)
