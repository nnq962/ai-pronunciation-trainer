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

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = '*'

rootPath = ''
results = {}  # Dictionary lưu trữ kết quả tạm thời

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
def highlight_partial_mismatches(real_transcripts_ipa, matched_transcripts_ipa):
    real_syllables = real_transcripts_ipa.split()
    matched_syllables = matched_transcripts_ipa.split()

    formatted_output = []
    matched_index = 0
    len_matched = len(matched_syllables)

    print("\nProcessing Partial Mismatches:")
    print(f"Real IPA: {real_syllables}")
    print(f"Matched IPA: {matched_syllables}")

    for real_syllable in real_syllables:
        if matched_index < len_matched:
            matched_syllable = matched_syllables[matched_index]

            if real_syllable == matched_syllable:
                # Âm tiết đúng, không bôi màu
                formatted_output.append(real_syllable)
            else:
                # So sánh từng ký tự để tìm lỗi cụ thể
                highlighted_syllable = []
                min_len = min(len(real_syllable), len(matched_syllable))

                for i in range(min_len):
                    if real_syllable[i] == matched_syllable[i]:
                        highlighted_syllable.append(real_syllable[i])
                    else:
                        highlighted_syllable.append(f'<span class="highlight-red">{real_syllable[i]}</span>')

                # Nếu từ thực tế dài hơn, phần thừa cũng bôi đỏ
                if len(real_syllable) > len(matched_syllable):
                    extra_part = real_syllable[min_len:]
                    highlighted_syllable.append(f'<span class="highlight-red">{extra_part}</span>')

                formatted_output.append("".join(highlighted_syllable))

                print(f" - Partial mismatch: '{real_syllable}' vs '{matched_syllable}', highlighted -> {''.join(highlighted_syllable)}")

            matched_index += 1
        else:
            # Âm tiết hoàn toàn thiếu, bôi đỏ toàn bộ
            formatted_output.append(f'<span class="highlight-red">{real_syllable}</span>')
            print(f" - Completely missing syllable '{real_syllable}' marked as red")

    return " ".join(formatted_output)

# ----------------------------------------------------------------
def highlight_extra_syllables(real_transcripts_ipa, matched_transcripts_ipa):
    real_syllables = real_transcripts_ipa.split()
    matched_syllables = matched_transcripts_ipa.split()

    formatted_output = []
    real_index = 0
    len_real = len(real_syllables)
    len_matched = len(matched_syllables)

    print("\nProcessing Extra Syllables:")
    print(f"Real IPA: {real_syllables}")
    print(f"Transcript IPA: {matched_syllables}")

    for matched_index, matched_syllable in enumerate(matched_syllables):
        if real_index < len_real and matched_syllable == real_syllables[real_index]:
            # Nếu âm tiết khớp, giữ nguyên và tiến tới âm tiết tiếp theo
            formatted_output.append(matched_syllable)
            real_index += 1
        else:
            # Kiểm tra xem âm tiết trong Matched IPA có xuất hiện muộn hơn trong Real IPA không
            found_later = False
            for search_index in range(real_index + 1, len_real):
                if matched_syllable == real_syllables[search_index]:
                    # Nếu tìm thấy khớp muộn hơn, giữ nguyên
                    found_later = True
                    break
            
            if found_later:
                formatted_output.append(matched_syllable)  # Giữ nguyên, không bôi vàng
                real_index += 1  # Dịch vị trí real_index tới vị trí mới
            else:
                # Nếu không tìm thấy trong danh sách sau, đánh dấu là thừa (bôi vàng)
                formatted_output.append(f'<span class="highlight-yellow">{matched_syllable}</span>')
                print(f" - Extra syllable '{matched_syllable}' marked as yellow")

    return " ".join(formatted_output)

# ----------------------------------------------------------------
def is_small_diff(a: str, b: str) -> bool:
    """
    Kiểm tra xem hai từ có sự khác biệt nhỏ không.
    - Nếu chỉ khác nhau 1 ký tự → True.
    - Nếu một từ chỉ thiếu hoặc thừa đúng 1 ký tự so với từ kia → True.
    - Nếu khác nhau quá nhiều → False.
    """
    if a == b:
        return False  # Không khác biệt gì

    # Nếu độ dài khác nhau quá nhiều, không thể là lỗi nhỏ
    if abs(len(a) - len(b)) > 1:
        return False

    # Nếu một từ là tiền tố của từ còn lại (chỉ thiếu 1 ký tự)
    if len(a) < len(b) and b.startswith(a):
        return True
    if len(b) < len(a) and a.startswith(b):
        return True

    # Kiểm tra số ký tự khác biệt
    diff_count = sum(1 for x, y in zip(a, b) if x != y)

    # Nếu khác nhau đúng 1 ký tự, coi là "small diff"
    return diff_count == 1

# ----------------------------------------------------------------
def is_partial_match(a: str, b: str) -> bool:
    """
    Kiểm tra xem hai từ có sự khác biệt nhỏ không.
    - Nếu chỉ khác nhau số ký tự trong khoảng cho phép (tính toán dựa trên độ dài từ) → True.
    - Nếu khác quá nhiều → False.
    """
    if a == b:
        return False  # Không khác biệt gì

    # Tính toán ngưỡng cho phép sai số dựa trên độ dài từ
    max_diff = max(1, round(min(len(a), len(b)) * 0.3))  # Cho phép sai khoảng 30% độ dài từ

    # Nếu độ dài khác nhau quá nhiều, không thể là lỗi nhỏ
    if abs(len(a) - len(b)) > max_diff:
        return False

    # Nếu một từ là tiền tố của từ còn lại (chỉ thiếu/thừa một số ký tự nhỏ)
    if len(a) < len(b) and b.startswith(a):
        return True
    if len(b) < len(a) and a.startswith(b):
        return True

    # Kiểm tra số ký tự khác biệt
    diff_count = sum(1 for x, y in zip(a, b) if x != y)

    # Nếu khác nhau tối đa `max_diff` ký tự, coi là "partial match"
    return diff_count <= max_diff

# ----------------------------------------------------------------
def highlight_partial_extra_syllables(real_word: str, matched_word: str) -> str:
    """
    So sánh từng ký tự và chỉ bôi vàng những ký tự sai thay vì bôi vàng toàn bộ từ.
    Không tự động thêm ký tự bị thiếu mà chỉ bôi vàng các ký tự có trong matched_word.
    """
    output = []
    min_len = min(len(real_word), len(matched_word))

    for i in range(min_len):
        if real_word[i] == matched_word[i]:
            output.append(matched_word[i])
        else:
            output.append(f'<span class="highlight-yellow">{matched_word[i]}</span>')

    # Nếu từ có thêm ký tự (dài hơn real_word), bôi vàng phần thừa
    if len(matched_word) > len(real_word):
        extra = matched_word[len(real_word):]
        output.append(f'<span class="highlight-yellow">{extra}</span>')

    return "".join(output)

# ----------------------------------------------------------------
def refine_yellow_highlights(real_transcripts_ipa: str, highlighted: str):                
    """
    - Kiểm tra lại các từ bị bôi vàng:
        - Nếu từ chỉ sai một ký tự, chỉ bôi vàng phần sai.
        - Nếu từ thực sự sai hoàn toàn, giữ nguyên bôi vàng.
    - Trả về refined_highlighted và số từ thừa hoàn toàn.
    """
    real_syllables = real_transcripts_ipa.split()
    
    # Tìm tất cả các từ bị bôi vàng trong highlighted_ipa
    yellow_words = re.findall(r'<span class="highlight-yellow">(.*?)</span>', highlighted)
    
    # Nếu không có từ bôi vàng, trả về luôn
    if not yellow_words:
        return highlighted, 0

    print("\n🔎 Debug: Từ đang bị bôi vàng:", yellow_words)

    refined_highlighted = highlighted
    corrected_count = 0  # Biến đếm số từ đã được chỉnh sửa thành gần đúng

    for yellow_word in yellow_words:
        print(f"\n🔍 Checking word: '{yellow_word}'")
        
        # Kiểm tra xem từ này có xuất hiện trong real_syllables không
        best_match = None
        for real_word in real_syllables:
            if is_partial_match(yellow_word, real_word):
                best_match = real_word
                break  # Chỉ lấy từ đầu tiên khớp gần đúng

        if best_match:
            # Nếu chỉ sai một phần, bôi vàng phần sai thay vì bỏ bôi vàng toàn bộ
            refined_word = highlight_partial_extra_syllables(best_match, yellow_word)
            refined_highlighted = refined_highlighted.replace(
                f'<span class="highlight-yellow">{yellow_word}</span>', refined_word, 1
            )
            corrected_count += 1
            print(f"✅ '{yellow_word}' has small differences with '{best_match}', applying partial highlight.")
        else:
            print(f"❌ '{yellow_word}' is completely extra and counted.")

    # Tính toán số từ thực sự thừa
    extra_count = len(yellow_words) - corrected_count
    print(f"\n🔢 Final extra word count: {extra_count}")
    
    return refined_highlighted, extra_count

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
