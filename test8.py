from bs4 import BeautifulSoup
import json

"""
We must preserve spaces between spans in row1, especially those not enclosed by <span>.
We'll parse <td> children in order (both text and span elements) to avoid losing spaces.
"""

def parse_html_to_json(html):
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')

    def process_row(row_tag):
        row_data = []
        current_group = {"text": "", "class": None}
        # Iterate over direct children of <td> to capture text nodes (spaces) outside <span>
        td = row_tag.find('td')
        for child in td.children:
            if child.name is None:
                # This is a NavigableString (text node)
                text = str(child).replace('\xa0', ' ')
                class_attr = ''  # no class for plain text
            else:
                # This is presumably a <span> tag
                text = child.text.replace('\xa0', ' ')
                class_list = child.get('class', [])
                class_attr = class_list[0] if class_list else ''
            
            # Merge with current group if same class
            if class_attr == current_group["class"]:
                current_group["text"] += text
            else:
                # push old group if not empty
                if current_group["text"]:
                    row_data.append(current_group)
                # start a new group
                current_group = {"text": text, "class": class_attr}
        # After loop, if there's leftover text in current_group
        if current_group["text"]:
            row_data.append(current_group)
        
        return row_data

    first_row_data = process_row(rows[0])
    second_row_data = process_row(rows[1])

    return json.dumps({"row1": first_row_data, "row2": second_row_data}, ensure_ascii=False, indent=4)

# Example usage
html_data = """
    <table style="border-spacing: 0px; font-family: monospace;">
        <tr><td><span class="highlight-green">ˈ</span><span class="highlight-green">ɛ</span><span class="highlight-green">v</span><span class="highlight-green">ə</span><span class="highlight-green">r</span><span class="highlight-green">i</span> <span class="highlight-green">g</span><span class="highlight-red">ə</span><span class="highlight-red">r</span><span class="highlight-red">l</span> <span class="highlight-green">d</span><span class="highlight-green">r</span><span class="highlight-green">i</span><span class="highlight-green">m</span><span class="highlight-yellow">z</span> <span class="highlight-green">ə</span><span class="highlight-green">v</span> <span class="highlight-green">ˈ</span><span class="highlight-green">o</span><span class="highlight-green">ʊ</span><span class="highlight-green">n</span><span class="highlight-green">ɪ</span><span class="highlight-green">ŋ</span> <span class="highlight-green">ə</span> <span class="highlight-green">ˈ</span><span class="highlight-green">p</span><span class="highlight-green">o</span><span class="highlight-green">ʊ</span><span class="highlight-green">ˌ</span><span class="highlight-green">n</span><span class="highlight-green">i</span><span class="highlight-green">.</span></td></tr>
        <tr><td><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span> <span class="expected">&nbsp;</span><span class="expected">ʊ</span><span class="expected">d</span><span class="expected">-</span> <span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">z</span> <span class="expected">&nbsp;</span><span class="expected">&nbsp;</span> <span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span> <span class="expected">&nbsp;</span> <span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span><span class="expected">&nbsp;</span></td></tr>
    </table>
"""

json_output = parse_html_to_json(html_data)
print(json_output)
