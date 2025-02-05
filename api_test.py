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
from utils import process_words_with_colors, highlight_partial_mismatches, highlight_extra_syllables, refine_yellow_highlights, convert_highlighted_text_to_json, convert_color_style_to_class

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

        if not result:
            return "No pronunciation data available.", 404

        colored_words = process_words_with_colors(real_transcripts, ipa_transcript, is_letter_correct_all_words)
        corrected_ipa = highlight_partial_mismatches(real_transcripts_ipa, matched_transcripts_ipa)
        highlighted_ipa = highlight_extra_syllables(real_transcripts_ipa, ipa_transcript)
        refined_ipa, extra_word_count = refine_yellow_highlights(real_transcripts_ipa, highlighted_ipa)

        print("-" * 80)
        print("Original pronunciation_accuracy:", pronunciation_accuracy)

        pronunciation_accuracy = int(pronunciation_accuracy)
        adjusted_score = max(pronunciation_accuracy - (extra_word_count * 10), 0)

        line1 = convert_highlighted_text_to_json(highlighted_text=convert_color_style_to_class(colored_words), key_name="Real transcript")
        line2 = convert_highlighted_text_to_json(highlighted_text=corrected_ipa, key_name="Real transcripts ipa")
        line3 = convert_highlighted_text_to_json(highlighted_text=refined_ipa, key_name="Your transcripts ipa")
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
        print(final_json_str)

        print("-" * 80)

        # Hiển thị giao diện với dữ liệu
        return render_template(
            "result.html",
            colored_words=colored_words,
            corrected_ipa=corrected_ipa,
            highlighted_ipa=refined_ipa,
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
