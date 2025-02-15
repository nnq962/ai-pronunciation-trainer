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
import re
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

    # Lưu kết quả đầy đủ vào `results`
    results["data"] = lambda_correct_output

    return lambda_correct_output

# ----------------------------------------------------------------
@app.route(rootPath + '/view')
def view_result():
    try:
        # Lấy kết quả dựa trên UUID
        result = results.get("data")
        print("-" * 80)
        print(results)
        print()
        print(result)
        if not result:
            return "Result not found or expired.", 404

        # Nếu kết quả là chuỗi JSON, chuyển thành dictionary
        if isinstance(result, str):
            result = json.loads(result)

        # Trích xuất thông tin cần thiết
        real_transcripts = result.get("real_transcripts")
        ipa_transcript = result.get("ipa_transcript")
        real_transcripts_ipa = result.get("real_transcripts_ipa")
        matched_transcripts_ipa = result.get("matched_transcripts_ipa")
        is_letter_correct_all_words = result.get("is_letter_correct_all_words")
        pronunciation_accuracy = result.get("pronunciation_accuracy")
        pair_accuracy_category = result.get("pair_accuracy_category")

        redundant_ipa = find_leftover_words(matched_transcripts_ipa, normalize_text(ipa_transcript))
        print('unicode_to_normal', normalize_text(ipa_transcript))
        print("Matched", matched_transcripts_ipa)
        print('redudant', redundant_ipa)

        list_matched_ipa = split_ipa_into_characters(matched_transcripts_ipa)
    
        if not result:
            return "No pronunciation data available.", 404
        
        result_1 = utils.process_line_1(real_transcripts, is_letter_correct_all_words)
        result_2 = utils.process_line_2_v3(real_transcripts_ipa, ipa_transcript)
        result_3, error_count = utils.process_line_3_v3(real_transcripts_ipa, matched_transcripts_ipa)

        result_4, extra_words = utils.process_line_4_v1(ipa_transcript, result_3, redundant_ipa)
 
        print("-" * 80)
        print("COUNT =", error_count)
        print("Original pronunciation_accuracy:", pronunciation_accuracy)

        pronunciation_accuracy = int(pronunciation_accuracy)
        adjusted_score = max(pronunciation_accuracy - (error_count * 10), 0)

        line1 = utils.convert_highlighted_text_to_json(highlighted_text=utils.convert_color_style_to_class(result_1), key_name="Real transcript")
        line2 = utils.convert_highlighted_text_to_json(highlighted_text=result_2, key_name="Real transcripts ipa")
        print(result_4)
        line3 = utils.convert_highlighted_text_to_json(highlighted_text=result_4, key_name="Your transcripts ipa")
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

        # Chuyển về JSON string
        final_json_str = json.dumps(final_json, ensure_ascii=False, indent=2)

        print("\n=== Final JSON Output ===")
        # print(final_json_str)

        print("-" * 80)

        # Hiển thị giao diện với dữ liệu
        return render_template(
            "result.html",
            colored_words=result_1,
            corrected_ipa=result_2,
            highlighted_ipa=result_4,
            pronunciation_accuracy=adjusted_score
        )
    
    except Exception as e:
        print(f"Error occurred: {e}")  # Log lỗi chi tiết
        return f"Internal Server Error: {e}", 500

def split_ipa_into_characters(matched_transcripts_ipa):
    # Tách thành danh sách các từ
    words = matched_transcripts_ipa.split()
    
    # Tách từng từ thành danh sách ký tự
    ipa_character_list = [list(word) for word in words]
    
    return ipa_character_list


def find_leftover_words(matched_text, transcript_text):
    # Chuẩn hóa: Xóa phần đầu và loại bỏ dấu câu
    def clean_text(text):
        text = re.sub(r"[^\wɪʊɔæəɚɑɒɛʌθðŋʃʒˌˈ ]", "", text)  # Xóa dấu câu, giữ ký tự IPA
        return text.lower().strip().split()

    matched_tokens = clean_text(matched_text.replace("Matched", ""))
    transcript_tokens = clean_text(transcript_text.replace("Your transcripts ipa:", ""))

    # Lọc ra từ thừa bằng cách duyệt từng phần tử
    matched_temp = matched_tokens.copy()
    redundant = []
    
    for token in transcript_tokens:
        if token in matched_temp:
            matched_temp.remove(token)  # Xóa phần tử đã match để tránh duplicate match
        else:
            redundant.append(token)  # Thêm vào danh sách từ dư
    
    return redundant

import unicodedata

def normalize_text(text):
    return unicodedata.normalize("NFKD", text)


if __name__ == "__main__":
    language = 'en'
    print(os.system('pwd'))
    # webbrowser.open_new('http://127.0.0.1:3000/')
    app.run(host="0.0.0.0", port=3000, debug=True)
