import os
import glob
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import html
import json
import re
import urllib.parse

# Fixed timezone for Japanese local time
JST = timezone(timedelta(hours=9))

# Number of recent entries to show in sidebar. Set to 0 to disable section.
LATEST_POST_COUNT = 7


# ★GitHub Secrets（環境変数）から秘密の本文を取得して置換
# ※GitHubの「Secrets and variables」→ 「Codespaces」 →
#  「New repository secret」で「FINAL_LETTER_TEXT_SECRET」に入れた文字列が
#   BODY内の {{FINAL_LETTER_TEXT_SECRET}} で表示可能です。
secret_text = os.environ.get("FINAL_LETTER_TEXT_SECRET", "[NO SECRET]")

# =============================
# Utility helpers
# =============================

def parse_entries(source_dir: str = "source_txt"):
    """Parse all Markdown sources into a flat list of dicts."""
    entries = []
    for path in sorted(glob.glob(os.path.join(source_dir, "*.txt"))):
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

            # CATEGORY (optional, comma-separated allowed)
            if idx < len(lines) and lines[idx].startswith("CATEGORY:"):
                category_line = lines[idx][len("CATEGORY:"):].strip()
                idx += 1
            else:
                category_line = ""
            categories = [c.strip() for c in category_line.split(',') if c.strip()] if category_line else []

            # DATE (optional but expected)
            if idx < len(lines) and lines[idx].startswith("DATE:"):
                date_str = lines[idx][len("DATE:"):].strip()
                idx += 1
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                date = date.replace(tzinfo=JST)
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
            
            # BODYにFINAL_LETTER_TEXT_SECRET  (body_lines)
            # body_lines に置換をかける
            body_lines = [line.replace("{{FINAL_LETTER_TEXT_SECRET}}", secret_text) for line in body_lines]
            
            entries.append(
                {
                    "title": title,
                    "category": category_line,
                    "categories": categories,
                    "date": date,
                    "date_str": date_str,
                    "body": "\n".join(body_lines).rstrip(),
                    "extended": "\n".join(extended_lines).rstrip(),
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
<style type='text/css'>
.linkbutton{
  font-size: 0.9em;
  padding: 1px 6px;
  vertical-align: baseline;
  line-height: 1;
  height: auto;
  margin-left: 4px;
  color:#66f;
  background-color:#f9f9f9;
  border: 1px solid #888;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s;
}
.copy-popup{
  background-color: #eef;
  border: 1px solid #88c;
  padding: 4px 8px;
  border-radius: 5px;
  font-size: 0.85em;
  color: #333;
  white-space: nowrap;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.15);
  transition: opacity 0.5s ease;
  position: absolute;
  pointer-events: none;
  opacity: 0;
  max-width: 80vw;             /* 画面幅の 80% で折り返す */
  overflow-wrap: anywhere;     /* 長い URL を途中で区切る */
  word-break: break-all;       /* ↑が効かない旧ブラウザ保険 */
  white-space: pre-wrap;       /* \n を改行として扱い、余計な連続空白は1個に */
}
.article_end_date{
  font-size:0.9em;
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

function copyLink(date, title, el){
  const url = `https://smokingwolf.github.io/dev_blog/archive/${date.slice(0,4)}/${date.slice(5,7)}.html#${date}`;
  const text = `\n【${date}\u3000${title}】\n ${url}`;
  navigator.clipboard.writeText(text).then(()=>{
    if(el && el.tagName === 'BUTTON'){
      const orig = el.textContent;
      el.textContent = '✅ コピー完了!';
      setTimeout(()=>{ el.textContent = '🔗 リンクをコピー'; }, 2000);
    }

    const popup = document.createElement('div');
    popup.className = 'copy-popup';
    popup.textContent = `✅ コピー完了：${text}`;
    document.body.appendChild(popup);

    const rect = el.getBoundingClientRect();
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
    const popupWidth = popup.offsetWidth;
    const pageWidth = document.documentElement.clientWidth;

    let left = rect.left + scrollLeft + (rect.width / 2) - (popupWidth / 2);
    let top  = rect.top  + scrollTop - popup.offsetHeight - 8;
    if(left < scrollLeft + 4) left = scrollLeft + 4;
    if(left + popupWidth > scrollLeft + pageWidth - 4)
        left = scrollLeft + pageWidth - popupWidth - 4;

    popup.style.left = `${left}px`;
    popup.style.top  = `${top}px`;
    popup.style.opacity = '1';
    popup.style.zIndex = '9999';

    setTimeout(()=>{ popup.style.opacity = '0'; }, 1800);
    setTimeout(()=>{ popup.remove(); }, 2500);
  });
}
</script>
"""

# Meta tags to prevent caching, inserted only for the top index page
NO_CACHE_META = """
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
"""

# Precompiled regex for locating the opening <head> tag
HEAD_OPEN_RE = re.compile(r"(<head[^>]*>)", re.IGNORECASE)


def render_entry_block(entry: dict, anchor_id: str, next_anchor: str | None,
                       page_dir: str, root: str = 'docs'):
    """Return HTML snippet for a single entry, including optional extended part.

    ``anchor_id`` is the id assigned to this entry and ``next_anchor`` should be
    the id of the next entry (or ``None``). A link with a ▼ symbol pointing to
    ``next_anchor`` will be placed on the right side of the title bar.
    """
    title_raw = entry["title"]
    title_html_safe = html.escape(title_raw)
    date_str = entry["date_str"].split()[0]
    weekday = "月火水木金土日"[entry["date"].weekday()]
    date_disp = f"{date_str} ({weekday})"
    body = entry["body"].replace("\n", "<br>")
    extended = entry["extended"].replace("\n", "<br>")
    title_js = title_raw.replace("\\", "\\\\").replace("'", "\\'")

    ext_html = ""
    if entry["extended"]:
        ext_id = f"ext-{hash(date_str + title_raw)}"
        ext_html = (
            f'<CENTER>　<a href="javascript:void(0);" onclick="toggle(\'{ext_id}\')">&#9660;追記を開く&#9660;</a></CENTER>'
            f'<div id="{ext_id}" style="display:none;" class="extended">{extended}</div>'
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
        f"■"
        f"<span onclick=\"copyLink('{date_str}','{title_js}', this)\" style='cursor:pointer;'>"
        f"{date_disp}&nbsp;&nbsp;&nbsp;{title_html_safe}</span>{arrow}"
    )

    year, month, _ = date_str.split('-')
    link = f"https://smokingwolf.github.io/dev_blog/archive/{year}/{month}.html#{anchor_id}"
    enc_url = urllib.parse.quote(link, safe='')
    enc_title = urllib.parse.quote(entry['title'], safe='')
    clap_html = (
        #f"<a href=\"//clap.fc2.com/post/smokingwolf/?url={enc_url}&title={enc_title}\" target=\"_blank\" title=\"web拍手 by FC2\">"
        #f"<img src=\"//clap.fc2.com/images/button/white/smokingwolf?url={enc_url}&lang=ja\" alt=\"web拍手 by FC2\" style=\"border:none;\" /></a>"
    )
    cat_html = ""
    categories: list[str] = entry.get("categories") or []
    cat_dirs: list[str] = entry.get("cat_dirs") or []
    if categories and page_dir:
        rel_root = os.path.relpath(root, page_dir)
        links = []
        for c, d in zip(categories, cat_dirs):
            link = f"{rel_root}/category/{d}/001.html"
            links.append(f"<a href='{link}'>{html.escape(c)}</a>")
        cat_html = f" <span style='float:right;'>カテゴリ: {', '.join(links)}</span>"

    end_html = (
        f"<div class='entry-foot'>"
        f"　<font class='article_end_date'>{date_disp}</font>　"
        f"{clap_html}<span style='display:inline-block;width:15px;'></span>"
        f" <button class='linkbutton' onclick=\"copyLink('{date_str}','{title_js}', this)\">📋 リンクをコピー</button>"
        f"{cat_html}"
        f"</div>"
    )

    return (
        f"<a id='{anchor_id}'></a><BR><div class='entry'>"
        f"<div class='entry-title'>{title_html}</div>"
        f"<div class='entry-body'>{body}</div>"
        f"{ext_html}"
        f"{end_html}</div>"
    )


# =============================
# Sidebar
# =============================

def render_sidebar(all_months: list[tuple[str, str]],
                   cat_counts: dict[str, int],
                   page_dir: str,
                   root: str = 'docs',
                   month_counts: dict[tuple[str, str], int] | None = None,
                   cat_dir_map: dict[str, str] | None = None,
                   recent_entries: list[dict] | None = None) -> str:
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
    lines.append(f"<div><a class='sidebar_link' href='{rel_root}/archive/top/index.html'>トップへ</a></div>")
    lines.append(f"<div><B><a class='sidebar_link' href='{rel_root}/index.html'>全記事一覧</a></B></div>")
    if recent_entries:
        lines.append("<hr>")
        lines.append("<div style='font-weight:bold;'>【最新記事】</div>")
        for ent in recent_entries:
            y = ent['date'].strftime('%Y')
            m = ent['date'].strftime('%m')
            d = ent['date'].strftime('%d')
            title = html.escape(ent['title'])
            url = f"{rel_root}/archive/{y}/{m}.html#{ent['anchor_id']}"
            caption = f"{m}/{d} {title}"
            lines.append(f"<div><a class='sidebar_link_recent' href='{url}'>●{caption}</a></div>")
    lines.append("<hr>")

    # Category section first
    lines.append("<div style='font-weight:bold;'>【カテゴリ】</div>")
    cat_dir_map = cat_dir_map or {}
    for cat in sorted(cat_counts.keys(), key=lambda c: (-cat_counts[c], c)):
        safe = get_cat_dir(cat, cat_dir_map)
        cnt = cat_counts[cat]
        caption = f"{html.escape(cat) if cat else 'uncategorized'}&nbsp;<span class='sym'>({cnt})</span>"
        lines.append(f"<div><a class='sidebar_link' href='{rel_root}/category/{safe}/001.html'>{caption}</a></div>")

    lines.append("<hr>")

    # Monthly section second
    lines.append("<div style='font-weight:bold;'>【月別】</div>")
    for y in years_sorted:
        pane_id = f"y{y}"
        # Year button with plus/minus symbol
        lines.append(
            f"<div><a class='sidebar_link' href='javascript:void(0);' id='{pane_id}-btn' onclick=\"toggleYear('{pane_id}')\">{y}&nbsp;<span class='sym'>＋</span></a></div>"
        )
        lines.append(f"<div id='{pane_id}' data-yearpane style='display:none;margin-left:10px;'>")
        for m in sorted(month_by_year[y], reverse=True):
            cnt = month_counts.get((y, m), 0)
            caption = f"{int(m):02d}月&nbsp;<span class='sym'>({cnt})</span>"
            url = f"{rel_root}/archive/{y}/{m}.html"
            lines.append(f"<div><a class='sidebar_link' href='{url}'>{caption}</a></div>")
        lines.append("</div>")
    lines.append("</div>")  # #sidebar
    return "\n".join(lines)


# =============================
# Full page assembler
# =============================

def render_body(title: str, content: str, sidebar_html: str, navigation: str,
                header_in_content: str, footer_end_content: str,
                article_pos: str = "") -> str:
    """Return the HTML to be placed inside <body>."""
    body_parts = [STYLE_BLOCK, SCRIPT_BLOCK]
    body_parts.append("<div id='content'>")
    body_parts.append(header_in_content)
    body_parts.append("")
    if article_pos:
        body_parts.append(f"<div class='article_pos'>{html.escape(article_pos)}</div>")
    body_parts.append(f"<div class='nav'>{navigation}</div>")
    body_parts.append(content)
    if article_pos:
        body_parts.append(f"<div class='article_pos'>{html.escape(article_pos)}</div>")
    body_parts.append(f"<div class='nav'>{navigation}</div>")
    body_parts.append("<a id='bottom'></a>")
    body_parts.append(footer_end_content)
    body_parts.append("")
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
    all_entries = [e for e in parse_entries() if e.get('date')]
    now_jst = datetime.now(JST)
    entries = [e for e in all_entries if e['date'] <= now_jst]
    entries.sort(key=lambda e: e['date'])  # oldest → newest

    # Load shared header & footer (required)
    with open(os.path.join('design', 'header.txt'), encoding='utf-8') as f:
        HEADER_TEMPLATE = f.read()
    with open(os.path.join('design', 'footer.txt'), encoding='utf-8') as f:
        FOOTER_TEMPLATE = f.read()
    with open(os.path.join('design', 'header_in_content.txt'), encoding='utf-8') as f:
        HEADER_IN_CONTENT = f.read()
    with open(os.path.join('design', 'footer_end_content.txt'), encoding='utf-8') as f:
        FOOTER_END_CONTENT = f.read()

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
        cats = e.get('categories') or ['']
        if not cats:
            cat_map[''].append(e)
        else:
            for c in cats:
                cat_map[c].append(e)

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
        cats = e.get('categories') or ['']
        e['cat_dirs'] = [get_cat_dir(c, cat_dir_map) for c in cats]

    if LATEST_POST_COUNT > 0:
        recent_entries = sorted(entries, key=lambda x: x['date'], reverse=True)[:LATEST_POST_COUNT]
    else:
        recent_entries = []

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
            blocks.append(render_entry_block(ent, ent['anchor_id'], next_id, page_dir, root))
        entry_html = '<br><br><br>\n'.join(blocks)

        sidebar = render_sidebar(months_sorted, cat_counts, page_dir, root, month_counts, cat_dir_map, recent_entries)
        body_html = render_body(
            f'{year}-{month}',
            entry_html,
            sidebar,
            navigation,
            HEADER_IN_CONTENT,
            FOOTER_END_CONTENT,
            f'{year}年{month}月',
        )
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
                blocks.append(render_entry_block(ent, ent['anchor_id'], next_id, page_dir, root))
            entry_html = '<br><br><br>\n'.join(blocks)
            sidebar = render_sidebar(months_sorted, cat_counts, page_dir, root, month_counts, cat_dir_map, recent_entries)
            total_pages = (len(es_sorted) + 9) // 10
            pos_text = f"{cat or 'uncategorized'} {page_num}/{total_pages}"
            body_html = render_body(
                cat or 'uncategorized',
                entry_html,
                sidebar,
                navigation,
                HEADER_IN_CONTENT,
                FOOTER_END_CONTENT,
                pos_text,
            )
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
            blocks.append(render_entry_block(ent, ent['anchor_id'], next_id, page_dir, root))
        entry_html = '<br><br><br>\n'.join(blocks)
        sidebar = render_sidebar(months_sorted, cat_counts, page_dir, root, month_counts, cat_dir_map, recent_entries)
        body_html = render_body(
            '開発日誌',
            entry_html,
            sidebar,
            navigation,
            HEADER_IN_CONTENT,
            FOOTER_END_CONTENT,
            'トップ',
        )
        full_html = assemble_full_page('開発日誌', body_html, HEADER_TEMPLATE, FOOTER_TEMPLATE)
        # Insert no-cache meta tags only on the top index page
        full_html = HEAD_OPEN_RE.sub(r"\1\n" + NO_CACHE_META, full_html, count=1)
        write_file(page_path, full_html)

    # -------------------------
    # Master index page (all titles)
    # -------------------------
    page_dir = root
    page_path = os.path.join(page_dir, 'index.html')
    all_sorted = sorted(entries, key=lambda x: x['date'], reverse=True)
    by_year: dict[str, list[dict]] = defaultdict(list)
    for ent in all_sorted:
        by_year[ent['date'].strftime('%Y')].append(ent)
    years = sorted(by_year.keys(), reverse=True)

    lines: list[str] = []
    lines.append("<br><B><font color='#aaaaff'>【全記事一覧】</font></B><div class='master_years'>")
    year_links = '　'.join([f"<a href='#{y}' class='g'>{y}年</a>" for y in years])
    lines.append(year_links)
    lines.append("</div><br><br>")
    for idx, y in enumerate(years):
        lines.append(f"<a id='{y}'></a><H1>{y}</H1>")
        for ent in by_year[y]:
            date = ent['date'].strftime('%Y-%m-%d')
            weekday = '月火水木金土日'[ent['date'].weekday()]
            month = ent['date'].strftime('%m')
            url = f"archive/{y}/{month}.html#{ent['anchor_id']}"
            title = html.escape(ent['title'])
            cat = ent.get('category', '')
            cat_html = f" <font class='top_minicategory'>{html.escape(cat)}</font>" if cat else ''
            lines.append(f"・<a href='{url}' class='blue'>{date}({weekday})　{title}</a>{cat_html}<br>")
        if idx < len(years) - 1:
            lines.append("<div align='right'><a href='#top' class='g'>▲一番上へ戻る</a></div><br>")
    index_content = "\n".join(lines)

    sidebar = render_sidebar(months_sorted, cat_counts, page_dir, root, month_counts, cat_dir_map, recent_entries)
    body_html = render_body('記事一覧', index_content, sidebar, '', HEADER_IN_CONTENT, FOOTER_END_CONTENT)
    full_html = assemble_full_page('記事一覧', body_html, HEADER_TEMPLATE, FOOTER_TEMPLATE)
    # Adjust script path for root index and add scroll position persistence
    full_html = full_html.replace('../../js/', 'js/')
    scroll_js = (
        "<script>\n"
        "const restore=()=>{\n"
        "  const p=sessionStorage.getItem('index-scroll');\n"
        "  if(p!==null) window.scrollTo(0,parseInt(p,10));\n"
        "};\n"
        "const save=()=>{\n"
        "  sessionStorage.setItem('index-scroll',window.pageYOffset);\n"
        "};\n"
        "window.addEventListener('DOMContentLoaded',restore);\n"
        "window.addEventListener('pageshow',restore);\n"
        "window.addEventListener('beforeunload',save);\n"
        "window.addEventListener('pagehide',save);\n"
        "</script>\n"
    )
    full_html = full_html.replace('</body>', scroll_js + '</body>')
    write_file(page_path, full_html)

    # Ensure GitHub pages skips Jekyll processing
    write_file(os.path.join(root, '.nojekyll'), '')


if __name__ == '__main__':
    build()
