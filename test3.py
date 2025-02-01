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
    
    # Tạo UUID duy nhất cho yêu cầu này
    request_id = str(uuid.uuid4())

    # Lưu kết quả đầy đủ vào `results`
    results[request_id] = {
        "status": "success",
        "request_id": request_id,
        "data": lambda_correct_output
    }

    print('-' * 80)
    print("DONE")
    print(request_id)

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
    result = results.get(request_id)

    # Lấy dữ liệu từ API
    inner_data = json.loads(result["data"])

    # Debug: In dữ liệu gốc từ API
    print("Full API response:")
    print(json.dumps(inner_data, indent=2))
    
    # Trích xuất thông tin cần thiết
    real_transcripts = inner_data.get("real_transcripts")
    ipa_transcript = inner_data.get("ipa_transcript")
    real_transcripts_ipa = inner_data.get("real_transcripts_ipa")
    matched_transcripts_ipa = inner_data.get("matched_transcripts_ipa")
    is_letter_correct_all_words = inner_data.get("is_letter_correct_all_words")
    pronunciation_accuracy = inner_data.get("pronunciation_accuracy")


    # Debug: In từng thông tin đã trích xuất
    print("\nExtracted Data:")
    print(f"Real Transcripts: {real_transcripts}")
    print(f"IPA Transcript: {ipa_transcript}")
    print(f"Real Transcripts IPA: {real_transcripts_ipa}")
    print(f"Matched Transcripts IPA: {matched_transcripts_ipa}")
    print(f"Is Letter Correct (All Words): {is_letter_correct_all_words}")
    print(f"Pronunciation Accuracy: {pronunciation_accuracy}")
    
    # Xử lý highlight và hiển thị full IPA đúng
    highlighted_ipa, corrected_ipa = process_transcript(
        ipa_transcript,
        real_transcripts_ipa
    )

    print("-" * 80)
    print("highlighted_ipa:", highlighted_ipa)
    print("corrected_ipa:", corrected_ipa)

    colored_words = process_words_with_colors(real_transcripts, ipa_transcript, is_letter_correct_all_words)

    return render_template(
        "result.html",
        colored_words=colored_words,  # Thay thế real_transcripts bằng colored_words
        highlighted_ipa=highlighted_ipa,
        corrected_ipa=corrected_ipa,
        pronunciation_accuracy=pronunciation_accuracy
    )

# ----------------------------------------------------------------
def process_words_with_colors(real_transcripts, ipa_transcript, is_letter_correct_all_words):
    # Tách các từ và các trạng thái từ is_letter_correct_all_words
    real_transcripts_words = real_transcripts.split(" ")
    ipa_transcript_words = ipa_transcript.split(" ")
    letters_correct_status = is_letter_correct_all_words.split(" ")

    # Tạo danh sách chứa HTML cho từng từ
    colored_words = []

    # Lặp qua từng từ
    for word_idx, real_word in enumerate(real_transcripts_words):
        # Nếu vượt quá trạng thái được cung cấp, bỏ qua từ
        if word_idx >= len(letters_correct_status):
            colored_words.append(real_word)
            continue

        # Lấy trạng thái chữ cái của từ hiện tại
        letter_status = letters_correct_status[word_idx]
        word_html = ""

        # Lặp qua từng chữ cái
        for letter_idx, letter in enumerate(real_word):
            if letter_idx < len(letter_status) and letter_status[letter_idx] == "1":
                # Nếu chữ cái đúng, tô màu xanh
                word_html += f'<span style="color: green;">{letter}</span>'
            else:
                # Nếu chữ cái sai, tô màu đỏ
                word_html += f'<span style="color: red;">{letter}</span>'

        # Thêm từ vào danh sách
        colored_words.append(word_html)

    # Ghép danh sách lại thành chuỗi HTML
    return " ".join(colored_words)

# ----------------------------------------------------------------
def process_transcript(ipa_transcript, real_transcripts_ipa):
    ipa_transcript_split = ipa_transcript.split()
    real_transcripts_ipa_split = real_transcripts_ipa.split()

    highlighted_ipa = []
    corrected_ipa = []

    len_real = len(real_transcripts_ipa_split)
    len_ipa = len(ipa_transcript_split)

    print("\nProcessing Syllables:")
    print(f"IPA Split: {ipa_transcript_split}")
    print(f"Real IPA Split: {real_transcripts_ipa_split}")

    for i in range(len_real):
        actual = ipa_transcript_split[i] if i < len_ipa else ""
        expected = real_transcripts_ipa_split[i]

        print(f"\nComparing syllable {i+1}: '{actual}' vs '{expected}'")

        if actual != expected:
            if actual:
                highlighted_ipa.append(f'<span class="highlight-yellow">{actual}</span>')
                print(f" - Marked '{actual}' as incorrect (yellow)")
            else:
                highlighted_ipa.append("&nbsp;" * len(expected))
                print(f" - Missing syllable, added spaces")

            if expected:
                corrected_ipa.append(f'<span class="highlight-red">{expected}</span>')
                print(f" - Marked '{expected}' as correction (red)")
            else:
                corrected_ipa.append("&nbsp;" * len(actual))
                print(f" - Extra syllable, added spaces")
        else:
            highlighted_ipa.append(actual)
            corrected_ipa.append(expected)
            print(f" - Syllable '{actual}' is correct")

    # Append remaining syllables
    for i in range(len_real, len_ipa):
        actual = ipa_transcript_split[i]
        highlighted_ipa.append(actual)
        corrected_ipa.append("&nbsp;" * len(actual))
        print(f" - Appended extra syllable '{actual}' without marking")

    return " ".join(highlighted_ipa), " ".join(corrected_ipa)

if __name__ == "__main__":
    language = 'en'
    print(os.system('pwd'))
    # webbrowser.open_new('http://127.0.0.1:3000/')
    app.run(host="0.0.0.0", port=3000, debug=True)
