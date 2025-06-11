import os
import glob
from datetime import datetime
from collections import defaultdict
import html
import json

# =============================
# Utility helpers
# =============================

def parse_entries(source_dir: str = "source"):
    """Parse all Markdown sources into a flat list of dicts."""
    entries = []
    for path in sorted(glob.glob(os.path.join(source_dir, "*.md"))):
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Each entry is delimited by 8 hyphens on its own line (--------)
        raw_entries = content.split("--------")
        for raw in raw_entries:
            raw = raw.strip()
            if not raw:
                continue
            lines = [ln.rstrip("\n") for ln in raw.splitlines()]
            idx = 0

            # TITLE (required)
            if idx < len(lines) and lines[idx].startswith("TITLE:"):
                title = lines[idx][len("TITLE:"):].strip()
                idx += 1
            else:
                continue  # Skip malformed block

            # CATEGORY (optional)
            if idx < len(lines) and lines[idx].startswith("CATEGORY:"):
                category = lines[idx][len("CATEGORY:"):].strip()
                idx += 1
            else:
                category = ""

            # DATE (optional but expected)
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

            # Skip to BODY:
            while idx < len(lines) and lines[idx] != "BODY:":
                idx += 1
            if idx < len(lines):
                idx += 1  # skip "BODY:"

            body_lines: list[str] = []
            while idx < len(lines) and lines[idx] != "-----":
                body_lines.append(lines[idx])
                idx += 1

            # consume ----- delimiters after body
            while idx < len(lines) and lines[idx] == "-----":
                idx += 1

            # EXTENDED BODY (optional)
            extended_lines: list[str] = []
            if idx < len(lines) and lines[idx] == "EXTENDED BODY:":
                idx += 1
                while idx < len(lines) and lines[idx] != "-----":
                    extended_lines.append(lines[idx])
                    idx += 1

            entries.append(
                {
                    "title": title,
                    "category": category,
                    "date": date,
                    "date_str": date_str,
                    "body": "\n".join(body_lines).strip(),
                    "extended": "\n".join(extended_lines).strip(),
                }
            )
    return entries


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def write_file(path: str, content: str):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_cat_dir(cat: str, mapping: dict[str, str]) -> str:
    """Return directory name for category using mapping with safe fallback."""
    if not cat:
        return "uncategorized"
    if cat in mapping:
        return mapping[cat]
    return cat.replace('/', '_').replace(' ', '_') or 'uncategorized'


# =============================
# HTML fragments
# =============================

STYLE_BLOCK = """
<style>
body {display:flex; margin:0; font-family:YuGothic, "Hiragino Kaku Gothic Pro", Meiryo, sans-serif;}
#content {flex:1; padding:0 8px;}
#sidebar {width:120px; background:#f8f8f8; border-left:1px solid #ddd; padding:4px 6px; box-sizing:border-box; font-size:14px;}
#sidebar div {line-height:1.6;}
#sidebar hr {border:none; border-top:1px dashed #aaa; margin:4px 0;}
.nav {margin:10px 0; text-align:center;}
.entry {border:1px solid #ccc; border-radius:8px; margin:14px 0; overflow:hidden;}
.entry-title {background:linear-gradient(to right,#9bb0c5,#6f7f92); color:#fff; padding:4px; font-weight:bold;}
.entry-body {background:#fff; color:#444; padding:6px;}
.sym {color:#999; font-weight:normal;}
.fixed-menu {display:none; background: rgba(240, 240, 255, 0.9); top: 0; left: 0; width:100%; box-sizing: border-box; position: fixed; padding: 6px 14px; justify-content: center; gap: 20px; border-radius: 0 0 20px 20px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2); z-index: 1000; line-height:1.7; flex-wrap: wrap; min-width:680px;}
.fixed-menu a {display:inline-block; white-space:nowrap; text-decoration:none; font-weight:bold; color:#004466; font-size:14px; padding:2px 8px; transition:all 0.2s; border-radius:6px;}
.fixed-menu a:hover {background-color:#a5e5c6; color:#002233;}
@media (max-width:680px){
  #sidebar{display:none;}
  .fixed-menu{display:flex;}
  body{display:block; padding-top:60px;}
}
</style>
"""

SCRIPT_BLOCK = """
<script>
function toggle(id){
  const el = document.getElementById(id);
  if(!el) return;
  el.style.display = (el.style.display === 'none') ? 'block' : 'none';
}

// Year accordion with sessionStorage persistence
function toggleYear(id){
  const pane = document.getElementById(id);
  const btn  = document.getElementById(id+'-btn');
  if(!pane||!btn) return;
  const sym  = btn.querySelector('.sym');
  const isClosed = pane.style.display === 'none';
  pane.style.display = isClosed ? 'block' : 'none';
  sym.textContent   = isClosed ? '－' : '＋';
  sessionStorage.setItem('year-'+id, isClosed ? 'open' : 'closed');
}

window.addEventListener('DOMContentLoaded', ()=>{
  document.querySelectorAll('[data-yearpane]').forEach(pane=>{
    const id    = pane.id;
    const state = sessionStorage.getItem('year-'+id);
    const btn   = document.getElementById(id+'-btn');
    const sym   = btn?.querySelector('.sym');
    if(state === 'open'){
      pane.style.display = 'block';
      if(sym) sym.textContent = '－';
    }else{
      pane.style.display = 'none';
      if(sym) sym.textContent = '＋';
    }
  });
});
</script>
"""


def render_entry_block(entry: dict, anchor_id: str, next_anchor: str | None):
    """Return HTML snippet for a single entry, including optional extended part.

    ``anchor_id`` is the id assigned to this entry and ``next_anchor`` should be
    the id of the next entry (or ``None``). A link with a ▼ symbol pointing to
    ``next_anchor`` will be placed on the right side of the title bar.
    """
    title = html.escape(entry["title"])
    date_str = entry["date_str"].split()[0]
    body = entry["body"].replace("\n", "<br>")
    extended = entry["extended"].replace("\n", "<br>")

    ext_html = ""
    if entry["extended"]:
        ext_id = f"ext-{hash(date_str + title)}"
        ext_html = (
            f'　<a href="javascript:void(0);" onclick="toggle(\'{ext_id}\')">&#9660;追記を開く&#9660;</a>'
            f'<div id="{ext_id}" style="display:none;">{extended}</div>'
        )

    if next_anchor:
        arrow = (
            f"<span style='float:right;'>"
            f"<a href='#{next_anchor}' class='jumplink' title='次の記事へ'>▼</a>"
            f"</span>"
        )
    else:
        arrow = ""

    title_html = (
        f"■<a id='{anchor_id}'></a>{date_str}&nbsp;&nbsp;&nbsp;{title}{arrow}"
    )

    return (
        f"<div class='entry'>"
        f"<div class='entry-title'>{title_html}</div>"
        f"<div class='entry-body'>{body}</div>"
        f"{ext_html}"
        f"</div>"
    )


# =============================
# Sidebar
# =============================

def render_sidebar(all_months: list[tuple[str, str]],
                   cat_counts: dict[str, int],
                   page_dir: str,
                   root: str = 'docs',
                   month_counts: dict[tuple[str, str], int] | None = None,
                   cat_dir_map: dict[str, str] | None = None) -> str:
    """Generate sidebar HTML."""
    month_counts = month_counts or {}
    # Prepare relative path root → this page_dir
    rel_root = os.path.relpath(root, page_dir)

    # Group months by year
    month_by_year: dict[str, list[str]] = defaultdict(list)
    for y, m in all_months:
        month_by_year[y].append(m)

    years_sorted = sorted(month_by_year.keys(), reverse=True)

    lines: list[str] = []
    lines.append("<div id='sidebar'>")

    # Heading & top link
    lines.append("<div style='font-weight:bold;'>開発日誌</div>")
    lines.append(f"<div><a href='{rel_root}/archive/top/index.html'>トップへ</a></div>")
    lines.append("<hr>")

    # Category section first
    lines.append("<div style='font-weight:bold;'>【カテゴリ】</div>")
    cat_dir_map = cat_dir_map or {}
    for cat in sorted(cat_counts.keys(), key=lambda c: (-cat_counts[c], c)):
        safe = get_cat_dir(cat, cat_dir_map)
        cnt = cat_counts[cat]
        caption = f"{html.escape(cat) if cat else 'uncategorized'}&nbsp;<span class='sym'>({cnt})</span>"
        lines.append(f"<div><a href='{rel_root}/category/{safe}/001.html'>{caption}</a></div>")

    lines.append("<hr>")

    # Monthly section second
    lines.append("<div style='font-weight:bold;'>【月別】</div>")
    for y in years_sorted:
        pane_id = f"y{y}"
        # Year button with plus/minus symbol
        lines.append(
            f"<div><a href='javascript:void(0);' id='{pane_id}-btn' onclick=\"toggleYear('{pane_id}')\">{y}&nbsp;<span class='sym'>＋</span></a></div>"
        )
        lines.append(f"<div id='{pane_id}' data-yearpane style='display:none;margin-left:10px;'>")
        for m in sorted(month_by_year[y], reverse=True):
            cnt = month_counts.get((y, m), 0)
            caption = f"{int(m):02d}月&nbsp;<span class='sym'>({cnt})</span>"
            url = f"{rel_root}/archive/{y}/{m}.html"
            lines.append(f"<div><a href='{url}'>{caption}</a></div>")
        lines.append("</div>")
    lines.append("</div>")  # #sidebar
    return "\n".join(lines)


def render_fixed_menu(all_months: list[tuple[str, str]],
                      cat_counts: dict[str, int],
                      page_dir: str,
                      root: str = 'docs',
                      month_counts: dict[tuple[str, str], int] | None = None,
                      cat_dir_map: dict[str, str] | None = None) -> str:
    """Generate responsive top menu for small screens."""
    month_counts = month_counts or {}
    rel_root = os.path.relpath(root, page_dir)
    rel_home = os.path.relpath('.', page_dir)

    month_by_year: dict[str, list[str]] = defaultdict(list)
    for y, m in all_months:
        month_by_year[y].append(m)
    years_sorted = sorted(month_by_year.keys(), reverse=True)

    lines: list[str] = []
    lines.append("<nav class='fixed-menu'><center>")
    lines.append(f"<a href='{rel_home}/' class='blue'>←ホームへ</a>")
    lines.append("<small>開発日誌</small>")
    lines.append(f"<a href='{rel_root}/archive/top/index.html' class='g'>トップページ</a>")

    # Category dropdown
    lines.append("<details class='menu-cat' style='display:inline-block;'>")
    lines.append("<summary>カテゴリー</summary>")
    cat_dir_map = cat_dir_map or {}
    for cat in sorted(cat_counts.keys(), key=lambda c: (-cat_counts[c], c)):
        safe = get_cat_dir(cat, cat_dir_map)
        cnt = cat_counts[cat]
        caption = f"{html.escape(cat) if cat else 'uncategorized'}&nbsp;<span class='sym'>({cnt})</span>"
        lines.append(f"<div><a href='{rel_root}/category/{safe}/001.html'>{caption}</a></div>")
    lines.append("</details>")

    # Monthly dropdown
    lines.append("<details class='menu-month' style='display:inline-block;'>")
    lines.append("<summary>月別データ</summary>")
    for y in years_sorted:
        lines.append("<details style='margin-left:10px;'>")
        lines.append(f"<summary>{y}</summary>")
        for m in sorted(month_by_year[y], reverse=True):
            cnt = month_counts.get((y, m), 0)
            caption = f"{int(m):02d}月&nbsp;<span class='sym'>({cnt})</span>"
            url = f"{rel_root}/archive/{y}/{m}.html"
            lines.append(f"<div><a href='{url}'>{caption}</a></div>")
        lines.append("</details>")
    lines.append("</details>")
    lines.append("</center></nav>")
    return "\n".join(lines)


# =============================
# Full page assembler
# =============================

def render_body(title: str, content: str, sidebar_html: str, navigation: str, fixed_menu: str = "") -> str:
    """Return the HTML to be placed inside <body>."""
    body_parts = [STYLE_BLOCK, SCRIPT_BLOCK]
    if fixed_menu:
        body_parts.append(fixed_menu)
    body_parts.append("<div id='content'>")
    body_parts.append(f"<div class='nav'>{navigation}</div>")
    body_parts.append(content)
    body_parts.append(f"<div class='nav'>{navigation}</div>")
    body_parts.append("<a id='bottom'></a>")
    body_parts.append("</div>")  # #content
    body_parts.append(sidebar_html)
    return "\n".join(body_parts)


def assemble_full_page(title: str, body_html: str, header_tpl: str, footer_tpl: str) -> str:
    """Merge header / body / footer. %TITLE% placeholder in header will be replaced."""
    header = header_tpl.replace("%TITLE%", html.escape(title))
    return header + body_html + footer_tpl


# =============================
# Build process
# =============================

def build():
    entries = [e for e in parse_entries() if e.get('date')]
    entries.sort(key=lambda e: e['date'])  # oldest → newest

    # Load shared header & footer (required)
    with open(os.path.join('design', 'header.txt'), encoding='utf-8') as f:
        HEADER_TEMPLATE = f.read()
    with open(os.path.join('design', 'footer.txt'), encoding='utf-8') as f:
        FOOTER_TEMPLATE = f.read()

    root = 'docs'
    ensure_dir(root)

    # Load category directory mapping if available
    mapping_path = os.path.join('design', 'categories.json')

    if os.path.exists(mapping_path):
        with open(mapping_path, encoding='utf-8') as f:
            cat_dir_map: dict[str, str] = json.load(f)
    else:
        cat_dir_map = {}

    # Group by month & category
    month_map: dict[tuple[str, str], list[dict]] = defaultdict(list)
    cat_map: dict[str, list[dict]] = defaultdict(list)
    month_counts: dict[tuple[str, str], int] = {}

    for e in entries:
        ym = (e['date'].strftime('%Y'), e['date'].strftime('%m'))
        month_map[ym].append(e)
        cat_map[e['category']].append(e)

    for ym, lst in month_map.items():
        month_counts[ym] = len(lst)

    cat_counts = {cat: len(lst) for cat, lst in cat_map.items()}

    # Assign unique anchor ids for each entry based on the date. If multiple
    # entries share the same date, add alphabetical suffixes (A, B, ...).
    anchor_counter: dict[str, int] = defaultdict(int)
    for e in entries:
        key = e['date'].strftime('%Y-%m-%d')
        idx = anchor_counter[key]
        anchor_counter[key] += 1
        if idx == 0:
            anchor = key
        else:
            anchor = f"{key}{chr(ord('A') + idx - 1)}"
        e['anchor_id'] = anchor

    months_sorted = sorted(month_map.keys())  # ascending

    # -------------------------
    # Monthly archive pages
    # -------------------------
    for idx, ym in enumerate(months_sorted):
        year, month = ym
        page_dir = os.path.join(root, 'archive', year)
        page_path = os.path.join(page_dir, f'{month}.html')

        older_key = months_sorted[idx-1] if idx > 0 else None  # 前 = older
        newer_key = months_sorted[idx+1] if idx < len(months_sorted)-1 else None  # 次 = newer

        # Build navigation ( "次の月へ | 前の月へ" )
        if newer_key:
            newer_link = os.path.relpath(os.path.join(root, 'archive', newer_key[0], f'{newer_key[1]}.html'), page_dir)
            next_html = f"<a href='{newer_link}'>次の月へ</a>"
        else:
            next_html = "<span style='color:#ccc'>次の月へ</span>"

        if older_key:
            older_link = os.path.relpath(os.path.join(root, 'archive', older_key[0], f'{older_key[1]}.html'), page_dir)
            prev_html = f"<a href='{older_link}'>前の月へ</a>"
        else:
            prev_html = "<span style='color:#ccc'>前の月へ</span>"

        navigation = f"{next_html} | {prev_html}"

        # Render entries for that month, newest first
        month_entries = sorted(month_map[ym], key=lambda x: x['date'], reverse=True)
        blocks: list[str] = []
        for i, ent in enumerate(month_entries):
            next_id = month_entries[i + 1]['anchor_id'] if i < len(month_entries) - 1 else 'bottom'
            blocks.append(render_entry_block(ent, ent['anchor_id'], next_id))
        entry_html = '<br><br><br>\n'.join(blocks)

        sidebar = render_sidebar(months_sorted, cat_counts, page_dir, root, month_counts, cat_dir_map)
        fixed_menu = render_fixed_menu(months_sorted, cat_counts, page_dir, root, month_counts, cat_dir_map)
        body_html = render_body(f'{year}-{month}', entry_html, sidebar, navigation, fixed_menu)
        full_html = assemble_full_page(f'{year}-{month}', body_html, HEADER_TEMPLATE, FOOTER_TEMPLATE)
        write_file(page_path, full_html)

    # -------------------------
    # Category pages (10 posts each)
    # -------------------------
    for cat, es in cat_map.items():
        es_sorted = sorted(es, key=lambda x: x['date'], reverse=True)
        safe = get_cat_dir(cat, cat_dir_map)
        for idx in range(0, len(es_sorted), 10):
            chunk = es_sorted[idx:idx+10]
            page_num = idx // 10 + 1
            page_dir = os.path.join(root, 'category', safe)
            page_path = os.path.join(page_dir, f'{page_num:03d}.html')

            # Category navigation (次 | 前)
            if page_num > 1:
                newer_link = f'{page_num-1:03d}.html'
                next_html = f"<a href='{newer_link}'>次のページ</a>"
            else:
                next_html = "<span style='color:#ccc'>次のページ</span>"

            if idx + 10 < len(es_sorted):
                older_link = f'{page_num+1:03d}.html'
                prev_html = f"<a href='{older_link}'>前のページ</a>"
            else:
                prev_html = "<span style='color:#ccc'>前のページ</span>"
            navigation = f"{next_html} | {prev_html}"

            blocks = []
            for i, ent in enumerate(chunk):
                next_id = chunk[i + 1]['anchor_id'] if i < len(chunk) - 1 else 'bottom'
                blocks.append(render_entry_block(ent, ent['anchor_id'], next_id))
            entry_html = '<br><br><br>\n'.join(blocks)
            sidebar = render_sidebar(months_sorted, cat_counts, page_dir, root, month_counts, cat_dir_map)
            fixed_menu = render_fixed_menu(months_sorted, cat_counts, page_dir, root, month_counts, cat_dir_map)
            body_html = render_body(cat or 'uncategorized', entry_html, sidebar, navigation, fixed_menu)
            full_html = assemble_full_page(cat or 'uncategorized', body_html, HEADER_TEMPLATE, FOOTER_TEMPLATE)
            write_file(page_path, full_html)

    # -------------------------
    # Index page (latest two months)
    # -------------------------
    if months_sorted:
        months_desc = sorted(months_sorted, reverse=True)  # newest first
        first_month = months_desc[0]
        second_month = months_desc[1] if len(months_desc) > 1 else None

        entries_for_index: list[dict] = []
        entries_for_index.extend(sorted(month_map[first_month], key=lambda x: x['date'], reverse=True))
        if second_month:
            entries_for_index.extend(sorted(month_map[second_month], key=lambda x: x['date'], reverse=True))

        # Determine link to older month (前へ) – third newest
        older_link_month = months_desc[2] if len(months_desc) > 2 else None

        if older_link_month:
            older_link = os.path.relpath(
                os.path.join(root, 'archive', older_link_month[0], f"{older_link_month[1]}.html"),
                os.path.join(root, 'archive', 'top')
            )
            prev_html = f"<a href='{older_link}'>前へ</a>"
        else:
            prev_html = "<span style='color:#ccc'>前へ</span>"

        next_html = "<span style='color:#ccc'>次へ</span>"  # newest page has no newer link
        navigation = f"{next_html} | {prev_html}"

        page_dir = os.path.join(root, 'archive', 'top')
        page_path = os.path.join(page_dir, 'index.html')

        blocks = []
        for i, ent in enumerate(entries_for_index):
            next_id = entries_for_index[i + 1]['anchor_id'] if i < len(entries_for_index) - 1 else 'bottom'
            blocks.append(render_entry_block(ent, ent['anchor_id'], next_id))
        entry_html = '<br><br><br>\n'.join(blocks)
        sidebar = render_sidebar(months_sorted, cat_counts, page_dir, root, month_counts, cat_dir_map)
        fixed_menu = render_fixed_menu(months_sorted, cat_counts, page_dir, root, month_counts, cat_dir_map)
        body_html = render_body('開発日誌', entry_html, sidebar, navigation, fixed_menu)
        full_html = assemble_full_page('開発日誌', body_html, HEADER_TEMPLATE, FOOTER_TEMPLATE)
        write_file(page_path, full_html)

    # Ensure GitHub pages skips Jekyll processing
    write_file(os.path.join(root, '.nojekyll'), '')


if __name__ == '__main__':
    build()
