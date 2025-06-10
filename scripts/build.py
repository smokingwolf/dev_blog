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



def render_entry_block(entry):
    """Return HTML snippet for a single entry including body and extended body."""
    title = html.escape(entry["title"])
    date_str = entry["date_str"].split()[0]
    body = entry["body"].replace("\n", "<br>")
    extended = entry["extended"].replace("\n", "<br>")
    ext_html = ""
    if entry["extended"]:
        ext_id = f"ext-{hash(date_str + title)}"
        ext_html = (
            f'<a href="javascript:void(0);" '
            f'onclick="toggle(\"{ext_id}\")">&#9660;追記を開く&#9660;</a>'
            f'<div id="{ext_id}" style="display:none;">{extended}</div>'
        )
    return (
        f"<div class='entry'>"
        f"<div class='entry-title'>{date_str}  {title}</div>"
        f"<div class='entry-body'>{body}</div>"
        f"{ext_html}"
        f"</div>"
    )


def render_sidebar(all_months, categories, page_dir, root='docs'):
    """Generate sidebar HTML with links relative to page_dir."""
    rel_root = os.path.relpath(root, page_dir)
    years = sorted({y for y, _ in all_months}, reverse=True)
    month_by_year = defaultdict(list)
    for y, m in all_months:
        month_by_year[y].append(m)
    lines = ["<div id='sidebar'>"]
    lines.append(f"<div><a href='{rel_root}/archive/index.html'>開発日誌トップ</a></div>")
    for y in years:
        toggle_id = f"y{y}"
        lines.append(f"<div><a href='javascript:void(0);' onclick=\"toggleDisp('{toggle_id}')\">{y}</a></div>")
        lines.append(f"<div id='{toggle_id}' style='display:none;margin-left:10px;'>")
        for m in sorted(month_by_year[y], reverse=True):
            lines.append(f"<div><a href='{rel_root}/archive/{y}/{m}.html'>{m}</a></div>")
        lines.append("</div>")
    lines.append("<hr>")
    for cat in sorted(categories):
        safe = cat.replace('/', '_').replace(' ', '_') or 'uncategorized'
        lines.append(f"<div><a href='{rel_root}/category/{safe}/001.html'>{html.escape(cat) if cat else 'uncategorized'}</a></div>")
    lines.append("</div>")
    return "\n".join(lines)


def render_page(title, content, sidebar_html, navigation=""):
    """Wrap page content with basic HTML."""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>{html.escape(title)}</title>
<style>
body{{display:flex;}}
#content{{flex:1;}}
#sidebar{{width:80px;margin-left:10px;}}
.nav{{margin:10px 0;}}
.entry{{border:1px solid #ccc;border-radius:8px;margin:10px 0;overflow:hidden;}}
.entry-title{{background:linear-gradient(to right,#9bb0c5,#6f7f92);color:#fff;padding:4px;}}
.entry-body{{background:#fff;color:#444;padding:4px;}}
</style>
<script>
function toggle(id){{
  var e=document.getElementById(id);
  if(e.style.display==='none'){{e.style.display='block';}}else{{e.style.display='none';}}
}}
function toggleDisp(id){{
  var e=document.getElementById(id);
  if(e.style.display==='none'){{e.style.display='block';}}else{{e.style.display='none';}}
}}
</script>
</head>
<body>
<div id='content'>
<div class='nav'>{navigation}</div>
{content}
<div class='nav'>{navigation}</div>
</div>
{sidebar_html}
</body>
</html>"""


def build():
    entries = parse_entries()
    entries = [e for e in entries if e.get('date')]
    entries.sort(key=lambda e: e['date'])
    root = 'docs'
    ensure_dir(root)

    # group entries by month and category
    month_map = defaultdict(list)
    cat_map = defaultdict(list)
    for e in entries:
        ym = (e['date'].strftime('%Y'), e['date'].strftime('%m'))
        month_map[ym].append(e)
        cat_map[e['category']].append(e)

    months_sorted = sorted(month_map.keys())
    categories = list(cat_map.keys())

    # create monthly archive pages
    for idx, ym in enumerate(months_sorted):
        year, month = ym
        page_dir = os.path.join(root, 'archive', year)
        page_path = os.path.join(page_dir, f'{month}.html')
        prev_key = months_sorted[idx-1] if idx > 0 else None
        next_key = months_sorted[idx+1] if idx < len(months_sorted)-1 else None
        if prev_key:
            prev_link = os.path.relpath(os.path.join(root, 'archive', prev_key[0], f'{prev_key[1]}.html'), os.path.dirname(page_path))
            prev_html = f"<a href='{prev_link}'>前の月へ</a>"
        else:
            prev_html = "<span style='color:#ccc'>前の月へ</span>"
        if next_key:
            next_link = os.path.relpath(os.path.join(root, 'archive', next_key[0], f'{next_key[1]}.html'), os.path.dirname(page_path))
            next_html = f"<a href='{next_link}'>次の月へ</a>"
        else:
            next_html = "<span style='color:#ccc'>次の月へ</span>"
        navigation = f"{prev_html} | {next_html}"
        entry_html = '<br><br><br>\n'.join(
            render_entry_block(e) for e in sorted(month_map[ym], key=lambda x: x['date'], reverse=True)
        )
        sidebar = render_sidebar(months_sorted, categories, os.path.dirname(page_path))
        html_page = render_page(f'{year}-{month}', entry_html, sidebar, navigation)
        write_file(page_path, html_page)

    # create category pages (10 posts each)
    for cat, es in cat_map.items():
        es_sorted = sorted(es, key=lambda x: x['date'], reverse=True)
        safe = cat.replace('/', '_').replace(' ', '_') or 'uncategorized'
        for idx in range(0, len(es_sorted), 10):
            chunk = es_sorted[idx:idx+10]
            page_num = idx // 10 + 1
            page_dir = os.path.join(root, 'category', safe)
            page_path = os.path.join(page_dir, f'{page_num:03d}.html')
            if page_num > 1:
                prev_link = f'{page_num-1:03d}.html'
                prev_html = f"<a href='{prev_link}'>前のページ</a>"
            else:
                prev_html = "<span style='color:#ccc'>前のページ</span>"
            if idx + 10 < len(es_sorted):
                next_link = f'{page_num+1:03d}.html'
                next_html = f"<a href='{next_link}'>次のページ</a>"
            else:
                next_html = "<span style='color:#ccc'>次のページ</span>"
            navigation = f"{prev_html} | {next_html}"
            entry_html = '<br><br><br>\n'.join(render_entry_block(e) for e in chunk)
            sidebar = render_sidebar(months_sorted, categories, os.path.dirname(page_path))
            html_page = render_page(cat or 'uncategorized', entry_html, sidebar, navigation)
            write_file(page_path, html_page)

    # build index page showing latest two months
    if months_sorted:
        months_desc = sorted(months_sorted, reverse=True)
        first_month = months_desc[0]
        second_month = months_desc[1] if len(months_desc) > 1 else None
        entries_for_index = []
        entries_for_index.extend(sorted(month_map[first_month], key=lambda x: x['date'], reverse=True))
        if second_month:
            entries_for_index.extend(sorted(month_map[second_month], key=lambda x: x['date'], reverse=True))
        next_month = months_desc[2] if len(months_desc) > 2 else None
        prev_html = "<span style='color:#ccc'>前へ</span>"
        if next_month:
            link = f"{next_month[0]}/{next_month[1]}.html"
            next_html = f"<a href='{link}'>次へ</a>"
        else:
            next_html = "<span style='color:#ccc'>次へ</span>"
        nav = f"{prev_html} | {next_html}"
        page_dir = os.path.join(root, 'archive')
        page_path = os.path.join(page_dir, 'index.html')
        entry_html = '<br><br><br>\n'.join(render_entry_block(e) for e in entries_for_index)
        sidebar = render_sidebar(months_sorted, categories, page_dir)
        html_page = render_page('開発日誌', entry_html, sidebar, nav)
        write_file(page_path, html_page)

    # ensure GitHub Pages skips Jekyll processing
    write_file(os.path.join(root, '.nojekyll'), '')


if __name__ == '__main__':
    build()
