import re

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


def is_small_diff(a: str, b: str) -> bool:
    """
    Trả về True nếu hai từ chỉ khác nhau 1-2 ký tự (ví dụ: 'bəˈnænəz' vs 'bəˈnænə').
    """
    if a == b:
        return False  # Giống nhau hoàn toàn thì không cần thay đổi
    if abs(len(a) - len(b)) <= 2:  # Chỉ khác nhau tối đa 2 ký tự
        mismatch_count = sum(1 for x, y in zip(a, b) if x != y)
        return mismatch_count <= 2
    return False

def highlight_partial_mismatches(real_word: str, matched_word: str) -> str:
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

def refine_yellow_highlights(real_transcripts_ipa: str, highlighted: str) -> str:
    """
    Kiểm tra lại các từ bị bôi vàng:
    - Nếu từ chỉ sai một ký tự, chỉ bôi vàng phần sai.
    - Nếu từ thực sự sai hoàn toàn, giữ nguyên bôi vàng toàn bộ.
    """
    real_syllables = real_transcripts_ipa.split()
    
    # Tìm tất cả các từ bị bôi vàng trong highlighted_ipa
    yellow_words = re.findall(r'<span class="highlight-yellow">(.*?)</span>', highlighted)
    
    # Nếu không có từ bôi vàng, trả về luôn
    if not yellow_words:
        return highlighted

    print("\n🔎 Debug: Từ đang bị bôi vàng:", yellow_words)

    refined_highlighted = highlighted

    for yellow_word in yellow_words:
        # Tìm từ gần nhất trong real_syllables để so sánh
        best_match = None
        for real_word in real_syllables:
            if is_small_diff(yellow_word, real_word):
                best_match = real_word
                break  # Chỉ lấy từ đầu tiên khớp gần đúng

        if best_match:
            # Nếu chỉ sai một phần, bôi vàng phần sai thay vì bỏ bôi vàng toàn bộ
            refined_word = highlight_partial_mismatches(best_match, yellow_word)
            refined_highlighted = refined_highlighted.replace(
                f'<span class="highlight-yellow">{yellow_word}</span>', refined_word, 1
            )
            print(f"✅ Partially highlighted wrong characters in '{yellow_word}' instead of removing highlight.")
        else:
            print(f"❌ Kept yellow highlight on '{yellow_word}' because it is significantly different from all words in Real IPA.")

    return refined_highlighted

real_transcripts_ipa = "haʊ ˈmɛni bəˈnænəz ɔn ðə ˈteɪbəl?"
ipa_transcript = "haʊ ˈmɛni bəˈnænə ɔn ðə ˈteɪbəl?"

highlighted_ipa = highlight_extra_syllables(real_transcripts_ipa, ipa_transcript)
refined_ipa = refine_yellow_highlights(real_transcripts_ipa, highlighted_ipa)

print("\n=== Final Output ===")
print(refined_ipa)