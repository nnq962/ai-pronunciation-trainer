import difflib
import html

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

# Ví dụ test:
if __name__ == '__main__':
    # Test case ví dụ bạn đưa ra:
    real = "ju nid tɪ meɪk ə lɪst."
    my   = "ju nid tɪ meɪk ə lɪp."
    result_html, errors = process_line_3(real, my)
    print(result_html)
    print(errors)