import os
import glob
from datetime import datetime
from collections import defaultdict
import html


def parse_entries(source_dir="source"):
    entries = []
    for path in sorted(glob.glob(os.path.join(source_dir, "*.md"))):
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # split entries by separator lines of hyphens
        raw_entries = content.split("--------")
        for raw in raw_entries:
            raw = raw.strip()
            if not raw:
                continue
            lines = [line.rstrip("\n") for line in raw.splitlines()]
            idx = 0
            if idx < len(lines) and lines[idx].startswith("TITLE:"):
                title = lines[idx][len("TITLE:"):].strip()
                idx += 1
            else:
                continue
            if idx < len(lines) and lines[idx].startswith("CATEGORY:"):
                category = lines[idx][len("CATEGORY:"):].strip()
                idx += 1
            else:
                category = ""
            if idx < len(lines) and lines[idx].startswith("DATE:"):
                date_str = lines[idx][len("DATE:"):].strip()
                idx += 1
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
            else:
                date = None
                date_str = ""
            # skip delimiter and BODY label
            while idx < len(lines) and lines[idx] != "BODY:":
                idx += 1
            if idx < len(lines) and lines[idx] == "BODY:":
                idx += 1
            body_lines = []
            while idx < len(lines) and lines[idx] != "-----":
                body_lines.append(lines[idx])
                idx += 1
            while idx < len(lines) and lines[idx] == "-----":
                idx += 1
            # EXTENDED BODY
            extended_lines = []
            if idx < len(lines) and lines[idx] == "EXTENDED BODY:":
                idx += 1
                while idx < len(lines) and lines[idx] != "-----":
                    extended_lines.append(lines[idx])
                    idx += 1
            entry = {
                "title": title,
                "category": category,
                "date": date,
                "date_str": date_str,
                "body": "\n".join(body_lines).strip(),
                "extended": "\n".join(extended_lines).strip(),
            }
            entries.append(entry)
    return entries


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def write_file(path, content):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def render_entry(entry, root):
    slug = entry.get("slug")
    title = html.escape(entry["title"])
    date_str = entry["date_str"]
    body = entry["body"]
    extended = entry["extended"]
    ext_html = ""
    if extended:
        ext_id = f"ext-{slug}"
        ext_html = (
            f'<a href="javascript:void(0);" ' +
            f'onclick="toggle(\"{ext_id}\")">追記を開く</a>'
            f'<div id="{ext_id}" style="display:none;">{extended}</div>'
        )
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>{title}</title>
<script>
function toggle(id){{
 var e=document.getElementById(id);
 if(e.style.display==='none'){{e.style.display='block';}}else{{e.style.display='none';}}
}}
</script>
</head>
<body>
<h1>{title}</h1>
<div>{date_str}</div>
<div>{body}</div>
{ext_html}
</body>
</html>"""
    return html_content


def render_list(entries, title, page_path, root):
    lines = ["<ul>"]
    for e in entries:
        url = os.path.relpath(os.path.join(root, 'posts', f"{e['slug']}.html"), os.path.dirname(page_path))
        date_text = e['date'].strftime('%Y-%m-%d') if e['date'] else e['date_str']
        lines.append(f"<li>{date_text} <a href='{url}'>{html.escape(e['title'])}</a> [{html.escape(e['category'])}]</li>")
    lines.append("</ul>")
    body = "\n".join(lines)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>{html.escape(title)}</title>
<script>
function toggle(id){{
 var e=document.getElementById(id);
 if(e.style.display==='none'){{e.style.display='block';}}else{{e.style.display='none';}}
}}
</script>
</head>
<body>
<h1>{html.escape(title)}</h1>
{body}
</body>
</html>"""


def build():
    entries = parse_entries()
    entries.sort(key=lambda e: e['date'])
    root = 'dev_blog'
    ensure_dir(root)

    # assign slug and write entry pages
    for idx, e in enumerate(entries):
        slug = e['date'].strftime('%Y%m%d%H%M%S') if e['date'] else f"entry{idx}"
        e['slug'] = slug
        path = os.path.join(root, 'posts', f'{slug}.html')
        html_content = render_entry(e, root)
        write_file(path, html_content)

    # build month archives and categories
    month_map = defaultdict(list)
    cat_map = defaultdict(list)
    for e in entries:
        ym = e['date'].strftime('%Y/%m') if e['date'] else 'unknown'
        month_map[ym].append(e)
        cat_map[e['category']].append(e)

    for ym, es in month_map.items():
        year, month = ym.split('/')
        page_path = os.path.join(root, 'archive', year, f'{month}.html')
        content = render_list(sorted(es, key=lambda x: x['date'], reverse=True), f'{year}-{month}', page_path, root)
        write_file(page_path, content)

    for cat, es in cat_map.items():
        cat_file = cat.replace('/', '_')
        page_path = os.path.join(root, 'category', f'{cat_file}.html')
        content = render_list(sorted(es, key=lambda x: x['date'], reverse=True), cat, page_path, root)
        write_file(page_path, content)

    # latest page
    latest_entries = sorted(entries, key=lambda e: e['date'], reverse=True)[:20]
    latest_path = os.path.join(root, 'latest.html')
    latest_content = render_list(latest_entries, 'Latest Posts', latest_path, root)
    write_file(latest_path, latest_content)


if __name__ == '__main__':
    build()
