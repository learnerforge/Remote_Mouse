"""Convert docs/*.md to docs/*.html with navigation template."""
import os, re, html as html_mod

DOCS = os.path.dirname(os.path.abspath(__file__))
CSS = '../css/style.css'

NAV_ITEMS = [
    ('index.html', 'Home'),
    ('architecture.html', 'Architecture'),
    ('configuration.html', 'Configuration'),
    ('protocol.html', 'Protocol'),
    ('troubleshooting.html', 'Troubleshooting'),
    ('comparison.html', 'Comparison'),
]

TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Remote Mouse Docs</title>
<link rel="stylesheet" href="{css}">
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true,theme:'dark',fontSize:13}})</script>
</head>
<body>
<nav>
<h2>Remote Mouse</h2>
<ul>{nav}</ul>
<div class="section-title">Reference</div>
<ul>
{nav_ref}
</ul>
</nav>
<main>
{content}
</main>
</body>
</html>'''

def inline_md(text):
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text

def md_to_html(text):
    lines = text.split('\n')
    result = []
    i = 0
    code_block = False
    code_lang = ''
    code_lines = []
    in_table = False
    table_rows = []
    in_list = False
    list_type = 'ul'
    list_items = []

    def close_code():
        nonlocal code_block, code_lang, code_lines
        if code_lines:
            if code_lang == 'mermaid':
                result.append('<pre class="mermaid">' + html_mod.escape('\n'.join(code_lines)) + '</pre>')
            else:
                result.append('<pre><code>' + html_mod.escape('\n'.join(code_lines)) + '</code></pre>')
        code_block = False
        code_lang = ''
        code_lines = []

    def close_table():
        nonlocal in_table, table_rows
        if table_rows:
            result.append('<table>\n' + '\n'.join(table_rows) + '\n</table>')
            table_rows = []
        in_table = False

    def close_list():
        nonlocal in_list, list_items
        if list_items:
            result.append('<' + list_type + '>\n' + '\n'.join(list_items) + '\n</' + list_type + '>')
            list_items = []
        in_list = False

    while i < len(lines):
        line = lines[i]

        # Code blocks
        if re.match(r'^```', line.strip()):
            if code_block:
                close_code()
            else:
                close_table()
                close_list()
                code_block = True
                code_lang = line.strip()[3:]
                code_lines = []
            i += 1
            continue
        if code_block:
            code_lines.append(line)
            i += 1
            continue

        # Tables
        if line.strip().startswith('|') and line.strip().endswith('|'):
            close_list()
            # Skip separator rows
            if re.match(r'^\|[\s:-]+\|$', line.strip()):
                if not in_table:
                    i += 1
                    continue
                i += 1
                continue
            if not in_table:
                in_table = True
                table_rows = []
            cells = [c.strip() for c in line.split('|')[1:-1]]
            tag = 'th' if not table_rows else 'td'
            row = '<tr>' + ''.join(f'<{tag}>{inline_md(c)}</{tag}>' for c in cells) + '</tr>'
            table_rows.append(row)
            i += 1
            continue
        else:
            if in_table:
                close_table()

        # Lists
        ul_match = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        ol_match = re.match(r'^(\s*)\d+[.)]\s+(.*)', line)
        if ul_match:
            close_table()
            if not in_list:
                close_list()
                in_list = True
                list_type = 'ul'
                list_items = []
            list_items.append('<li>' + inline_md(ul_match.group(2)) + '</li>')
            i += 1
            continue
        elif ol_match:
            close_table()
            if not in_list:
                close_list()
                in_list = True
                list_type = 'ol'
                list_items = []
            list_items.append('<li>' + inline_md(ol_match.group(2)) + '</li>')
            i += 1
            continue
        else:
            if in_list:
                close_list()

        # Headings
        if line.startswith('#### '):
            result.append('<h4>' + inline_md(line[5:]) + '</h4>')
            i += 1; continue
        if line.startswith('### '):
            result.append('<h3>' + inline_md(line[4:]) + '</h3>')
            i += 1; continue
        if line.startswith('## '):
            result.append('<h2>' + inline_md(line[3:]) + '</h2>')
            i += 1; continue
        if line.startswith('# '):
            result.append('<h1>' + inline_md(line[2:]) + '</h1>')
            i += 1; continue

        # Horizontal rule
        if re.match(r'^-{3,}$', line.strip()):
            result.append('<hr>')
            i += 1; continue

        # Blockquote
        if line.startswith('> '):
            result.append('<blockquote><p>' + inline_md(line[2:]) + '</p></blockquote>')
            i += 1; continue

        # Empty line
        if not line.strip():
            if in_list:
                close_list()
            result.append('')
            i += 1; continue

        # Paragraph
        result.append('<p>' + inline_md(line) + '</p>')
        i += 1

    close_code()
    close_table()
    close_list()
    return '\n'.join(result)

def convert_file(md_path, title):
    with open(md_path, encoding='utf-8') as f:
        text = f.read()

    content = md_to_html(text)

    nav_items = []
    for path, label in NAV_ITEMS:
        page_label = 'Home' if path == 'index.html' else label
        active = ' class="active"' if title == page_label else ''
        nav_items.append(f'<li><a href="{path}"{active}>{label}</a></li>')
    nav_html = '\n'.join(nav_items)

    html_path = md_path.replace('.md', '.html')
    html = TEMPLATE.format(
        title=html_mod.escape(title),
        css=CSS,
        nav=nav_html,
        nav_ref=nav_html,
        content=content
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  {os.path.basename(md_path)} -> {os.path.basename(html_path)}')

if __name__ == '__main__':
    files = [
        ('README_FULL.md', 'Home'),
        ('ARCHITECTURE.md', 'Architecture'),
        ('CONFIGURATION.md', 'Configuration'),
        ('PROTOCOL.md', 'Protocol'),
        ('TROUBLESHOOTING.md', 'Troubleshooting'),
        ('COMPARISON.md', 'Comparison'),
    ]
    for md, title in files:
        path = os.path.join(DOCS, md)
        if os.path.exists(path):
            convert_file(path, title)
    print('Done.')
