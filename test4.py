from utils import convert_color_style_to_class

html_input = '''
<span style="color: green;">Hello</span>, 
<span style="color: red;">world</span>! 
This is a <span style="color: yellow;">test</span>.
'''

converted_html = convert_color_style_to_class(html_input)

print("\n=== Converted HTML ===")
print(converted_html)