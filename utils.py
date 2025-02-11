import re
import json
import difflib
import html


# ----------------------------------------------------------------
def convert_highlighted_text_to_json(highlighted_text: str, key_name="words"):
    """
    Chuyển đổi văn bản có thẻ <span> thành JSON chứa danh sách từ và trạng thái màu của từng từ.
    Giữ dấu cách để giúp frontend hiển thị đúng.
    Đồng thời nhóm các ký tự liên tiếp cùng màu thành một từ duy nhất.

    Args:
        highlighted_text (str): Văn bản có thẻ HTML.
        key_name (str): Tên của key trong JSON (mặc định là "words").

    Returns:
        str: Chuỗi JSON có cấu trúc tối ưu, gọn gàng.
    """
    words = []
    current_index = 0

    # Tách từng phần của câu (bao gồm cả phần highlight và phần không có highlight)
    pattern = re.compile(r'(<span class="highlight-(.*?)">(.*?)</span>)')
    matches = list(pattern.finditer(highlighted_text))

    for match in matches:
        # Lấy phần trước đoạn highlight (bao gồm cả khoảng trắng nếu có)
        before_text = highlighted_text[current_index:match.start()]
        if before_text:
            words.extend([{"text": word, "type": "normal"} for word in re.split(r'(\s+)', before_text) if word])

        # Lấy đoạn bị highlight
        highlight_text = match.group(3)  # Nội dung bên trong <span>
        highlight_type = match.group(2)  # Loại highlight (red, yellow,...)
        words.append({"text": highlight_text, "type": f"highlight-{highlight_type}"})

        # Cập nhật vị trí xử lý tiếp theo
        current_index = match.end()

    # Thêm phần còn lại của câu sau đoạn highlight cuối cùng
    after_text = highlighted_text[current_index:]
    if after_text:
        words.extend([{"text": word, "type": "normal"} for word in re.split(r'(\s+)', after_text) if word])

    # Nhóm các ký tự liên tiếp có cùng màu lại với nhau
    words = group_highlighted_words(words)

    result = {key_name: words}

    return json.dumps(result, ensure_ascii=False, indent=2)

# ----------------------------------------------------------------
def group_highlighted_words(word_list):
    """
    Gộp các ký tự liên tiếp cùng màu thành một cụm từ duy nhất.
    """
    grouped_words = []
    temp_word = ""
    temp_type = ""

    for word in word_list:
        if word["type"] == temp_type:
            temp_word += word["text"]
        else:
            if temp_word:
                grouped_words.append({"text": temp_word, "type": temp_type})
            temp_word = word["text"]
            temp_type = word["type"]

    # Thêm từ cuối cùng vào danh sách
    if temp_word:
        grouped_words.append({"text": temp_word, "type": temp_type})

    return grouped_words

# ----------------------------------------------------------------
def convert_color_style_to_class(html_text: str):
    """
    Chuyển đổi thẻ <span style="color: ...;"> thành <span class="highlight-...">
    
    Args:
        html_text (str): Chuỗi HTML cần chuyển đổi.
    
    Returns:
        str: Chuỗi HTML đã được chuẩn hóa.
    """
    # Định dạng lại các thẻ <span style="color: ...;"> thành <span class="highlight-...">
    html_text = re.sub(r'<span style="color:\s*(green|red|yellow);">', r'<span class="highlight-\1">', html_text)

    return html_text

# ----------------------------------------------------------------
def process_line_1(real_transcripts, is_letter_correct_all_words):
    # Tách các từ và các trạng thái từ is_letter_correct_all_words
    real_transcripts_words = real_transcripts.split(" ")
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
def process_line_2(real_transcripts_ipa, ipa_transcript):
    """
    So sánh hai chuỗi IPA ký tự theo ký tự và highlight (đánh dấu) các phần sai trên real_transcripts_ipa:
      - Các phần đúng (equal) giữ nguyên.
      - Các phần sai (replace, delete) được bao bọc trong thẻ <span class="highlight-red">...</span>.
      - Các phần chỉ có ở ipa_transcript (insert) không được hiển thị, vì mục tiêu là hiển thị real_transcripts_ipa.
    
    Đầu vào:
      - real_transcripts_ipa: chuỗi IPA của phiên âm gốc.
      - ipa_transcript: chuỗi IPA đã được đối chiếu (có thể có thêm âm tiết/ ký tự thừa).
    
    Trả về:
      - Chuỗi HTML của real_transcripts_ipa với các phần sai được bôi đỏ (bọc trong <span class="highlight-red">...</span>).
    
    Lưu ý: Đảm bảo rằng CSS có định nghĩa cho class "highlight-red", ví dụ:
          .highlight-red { color: red; }
    """
    sm = difflib.SequenceMatcher(None, real_transcripts_ipa, ipa_transcript)
    result = []
    
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            # Đoạn khớp: lấy từ real_transcripts_ipa giữ nguyên
            segment = html.escape(real_transcripts_ipa[i1:i2])
            result.append(segment)
        elif tag in ('replace', 'delete'):
            # Đoạn ở real_transcripts_ipa không khớp (hoặc bị mất so với ipa_transcript): highlight đoạn đó
            segment = html.escape(real_transcripts_ipa[i1:i2])
            result.append(f'<span class="highlight-red">{segment}</span>')
        elif tag == 'insert':
            # Các đoạn chỉ có trong ipa_transcript (insert) không có trong real_transcripts_ipa:
            # Không làm gì, vì ta chỉ hiển thị real_transcripts_ipa.
            continue
    
    return "".join(result)

# ----------------------------------------------------------------
def util_process_line_3(real_token, ipa_token):
    """
    So sánh 2 token (các chuỗi con) ký tự theo ký tự và bôi vàng những phần sai ở ipa_token.
    Nếu ký tự khớp, giữ nguyên; nếu không khớp, bọc trong thẻ <span class="highlight-yellow">.
    
    Trả về:
      - Chuỗi token đã căn chỉnh (HTML).
      - Một flag (boolean) cho biết token đó bị sai hoàn toàn hay không.
        (True nếu toàn bộ token được highlight, tức không có phần nào khớp,
         False nếu có một hoặc nhiều phần không được highlight)
    """
    char_matcher = difflib.SequenceMatcher(None, real_token, ipa_token)
    result_chars = []
    # Giả sử ban đầu token sai hoàn toàn, nếu có bất kỳ phần nào khớp thì gán False.
    full_error = True
    for tag, i1, i2, j1, j2 in char_matcher.get_opcodes():
        segment = html.escape(ipa_token[j1:j2])
        if tag == 'equal':
            full_error = False
            result_chars.append(segment)
        else:
            result_chars.append(f'<span class="highlight-yellow">{segment}</span>')
    return "".join(result_chars), full_error

# ----------------------------------------------------------------
def process_line_3(real_transcripts_ipa, ipa_transcript):
    """
    So sánh hai chuỗi IPA (phiên âm gốc và phiên âm nhận được) theo cấp độ token
    (tách bằng khoảng trắng), sau đó với các token không khớp thực hiện so sánh ký tự bên trong.
    
    - Các token khớp hoàn toàn được giữ nguyên.
    - Với các token không khớp, nếu số token thay thế (replace) ở hai chuỗi bằng nhau,
      tiến hành so sánh theo ký tự.
    - Nếu token được highlight hoàn toàn (toàn bộ token bôi vàng), mới tính token đó vào error_count.
    - Nếu không cân bằng (insert hoặc replace không cân bằng), toàn bộ token ở ipa_transcript
      trong vùng đó được bôi vàng và được tính là lỗi.
    
    Trả về:
      - Chuỗi HTML của ipa_transcript với các phần sai được bôi vàng.
      - Số lượng token bị lỗi (chỉ tính những token bị highlight hoàn toàn).
    """
    # Tách chuỗi thành danh sách token theo khoảng trắng
    real_tokens = real_transcripts_ipa.split()
    ipa_tokens  = ipa_transcript.split()
    
    token_matcher = difflib.SequenceMatcher(None, real_tokens, ipa_tokens)
    result_tokens = []
    error_count = 0
    
    for tag, i1, i2, j1, j2 in token_matcher.get_opcodes():
        if tag == 'equal':
            # Các token khớp hoàn toàn: giữ nguyên
            result_tokens.extend(ipa_tokens[j1:j2])
        elif tag == 'replace':
            # Nếu số token thay thế ở 2 chuỗi bằng nhau, so sánh từng cặp token theo ký tự.
            if (i2 - i1) == (j2 - j1):
                for idx in range(j2 - j1):
                    real_token = real_tokens[i1 + idx]
                    ipa_token  = ipa_tokens[j1 + idx]
                    aligned_token, token_is_fully_wrong = util_process_line_3(real_token, ipa_token)
                    result_tokens.append(aligned_token)
                    # Chỉ tính lỗi nếu token được highlight hoàn toàn
                    if token_is_fully_wrong:
                        error_count += 1
            else:
                # Nếu không cân bằng, bôi vàng toàn bộ token trong vùng này và tính tất cả là lỗi.
                for token in ipa_tokens[j1:j2]:
                    result_tokens.append(f'<span class="highlight-yellow">{html.escape(token)}</span>')
                    error_count += 1
        elif tag == 'insert':
            # Các token thừa xuất hiện trong ipa_transcript: bôi vàng toàn bộ và tính là lỗi.
            for token in ipa_tokens[j1:j2]:
                result_tokens.append(f'<span class="highlight-yellow">{html.escape(token)}</span>')
                error_count += 1
        elif tag == 'delete':
            # Không có token tương ứng trong ipa_transcript => bỏ qua
            pass
    
    html_result = " ".join(result_tokens)
    return html_result, error_count

# ----------------------------------------------------------------
def process_line_2_v2(real_transcripts_ipa, ipa_transcript):
    """
    So sánh hai chuỗi IPA thông minh hơn, bỏ qua các từ thừa trong transcript.
    
    Args:
        real_transcripts_ipa: Chuỗi IPA chuẩn
        ipa_transcript: Chuỗi IPA cần so sánh (có thể có từ thừa)
    
    Returns:
        Chuỗi HTML với các phần khác biệt được đánh dấu
    """
    def split_into_words(text):
        # Tách thành các từ, giữ lại dấu câu và khoảng trắng
        words = []
        current_word = ''
        
        for char in text:
            if char.isspace() or char in '.,:;!?':
                if current_word:
                    words.append(current_word)
                    current_word = ''
                words.append(char)
            else:
                current_word += char
        
        if current_word:
            words.append(current_word)
            
        return [w for w in words if w]

    def find_best_match(word, candidates):
        """Tìm từ phù hợp nhất trong danh sách candidates."""
        best_ratio = 0
        best_match = None
        
        for candidate in candidates:
            if candidate.isspace() or candidate in '.,:;!?':
                continue
                
            # Với từ ngắn (<=2 ký tự), yêu cầu khớp chính xác
            if len(word) <= 2:
                if word == candidate:
                    return candidate
                continue
                
            # Với từ dài hơn, sử dụng SequenceMatcher
            matcher = difflib.SequenceMatcher(None, word, candidate)
            matching_blocks = matcher.get_matching_blocks()
            
            # Tính tỷ lệ dựa trên độ dài của matching block dài nhất
            longest_match = max((match.size for match in matching_blocks), default=0)
            ratio = longest_match / max(len(word), len(candidate))
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate
                
        # Điều chỉnh ngưỡng dựa trên độ dài từ
        threshold = 0.7 if len(word) <= 4 else 0.5
        return best_match if best_ratio > threshold else None

    def compare_words(word1, word2):
        """So sánh chi tiết hai từ và đánh dấu phần khác biệt."""
        if word1.isspace() or word1 in '.,:;!?':
            return html.escape(word1)
            
        if word1 == word2:
            return html.escape(word1)
            
        if not word2:
            return f'<span class="highlight-red">{html.escape(word1)}</span>'
        
        # Xử lý đặc biệt cho từ ngắn (2-3 ký tự)
        if len(word1) <= 3:
            result = []
            for i, (c1, c2) in enumerate(zip(word1, word2.ljust(len(word1)))):
                if c1 == c2:
                    result.append(html.escape(c1))
                else:
                    result.append(f'<span class="highlight-red">{html.escape(c1)}</span>')
            return ''.join(result)
        
        # Xử lý từ dài hơn
        sm = difflib.SequenceMatcher(None, word1, word2)
        result = []
        
        similarity_ratio = sm.ratio()
        if similarity_ratio < 0.3:
            return f'<span class="highlight-red">{html.escape(word1)}</span>'
        
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                result.append(html.escape(word1[i1:i2]))
            else:
                segment = html.escape(word1[i1:i2])
                if segment:
                    result.append(f'<span class="highlight-red">{segment}</span>')
        
        return ''.join(result)

    real_words = split_into_words(real_transcripts_ipa)
    transcript_words = split_into_words(ipa_transcript)
    
    result = []
    used_transcript_indices = set()
    
    for real_word in real_words:
        if real_word.isspace() or real_word in '.,:;!?':
            result.append(html.escape(real_word))
            continue
            
        remaining_words = [w for i, w in enumerate(transcript_words) 
                         if i not in used_transcript_indices]
        best_match = find_best_match(real_word, remaining_words)
        
        if best_match:
            match_index = transcript_words.index(best_match)
            used_transcript_indices.add(match_index)
            result.append(compare_words(real_word, best_match))
        else:
            result.append(f'<span class="highlight-red">{html.escape(real_word)}</span>')
    
    return ''.join(result)