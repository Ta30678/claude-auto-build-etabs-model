"""Convert Markdown files to PDF using PyMuPDF (fitz).

Usage:
    python md_to_pdf.py
"""
import re
import html
import fitz  # PyMuPDF


def md_to_html(md_text: str) -> str:
    """Convert markdown text to basic HTML."""
    lines = md_text.split("\n")
    html_parts = []
    in_code_block = False
    in_table = False
    in_ul = False
    in_ol = False
    table_rows = []

    # Strip YAML frontmatter
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                lines = lines[i + 1:]
                break

    def inline_format(text):
        """Handle inline formatting: bold, italic, code, links."""
        # Code spans first (so bold/italic don't interfere)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        # Bold + italic
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", text)
        # Bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        # Italic
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
        # Links
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        return text

    def flush_table():
        nonlocal table_rows, in_table
        if not table_rows:
            return ""
        result = '<table border="1" cellpadding="4" cellspacing="0">'
        for idx, row in enumerate(table_rows):
            cells = [c.strip() for c in row.split("|")]
            cells = [c for c in cells if c != ""]
            # Skip separator rows (----)
            if all(re.match(r"^[-:]+$", c) for c in cells):
                continue
            tag = "th" if idx == 0 else "td"
            result += "<tr>"
            for cell in cells:
                result += f"<{tag}>{inline_format(html.escape(cell))}</{tag}>"
            result += "</tr>"
        result += "</table><br/>"
        table_rows = []
        in_table = False
        return result

    def flush_list():
        nonlocal in_ul, in_ol
        parts = []
        if in_ul:
            parts.append("</ul>")
            in_ul = False
        if in_ol:
            parts.append("</ol>")
            in_ol = False
        return "".join(parts)

    for line in lines:
        stripped = line.strip()

        # Code block toggle
        if stripped.startswith("```"):
            if in_table:
                html_parts.append(flush_table())
            if in_code_block:
                html_parts.append("</pre>")
                in_code_block = False
            else:
                html_parts.append(flush_list())
                html_parts.append('<pre style="background-color: #f0f0f0; padding: 8px; font-size: 9px;">')
                in_code_block = True
            continue

        if in_code_block:
            html_parts.append(html.escape(line) + "\n")
            continue

        # Table rows
        if "|" in stripped and stripped.startswith("|"):
            if not in_table:
                html_parts.append(flush_list())
                in_table = True
            table_rows.append(stripped)
            continue
        elif in_table:
            html_parts.append(flush_table())

        # Empty line
        if not stripped:
            html_parts.append(flush_list())
            continue

        # Headers
        m = re.match(r"^(#{1,6})\s+(.*)", stripped)
        if m:
            html_parts.append(flush_list())
            level = len(m.group(1))
            sizes = {1: "18px", 2: "15px", 3: "13px", 4: "12px", 5: "11px", 6: "10px"}
            size = sizes.get(level, "10px")
            text = inline_format(html.escape(m.group(2)))
            margin_top = "16px" if level <= 2 else "10px"
            html_parts.append(
                f'<p style="font-size: {size}; font-weight: bold; margin-top: {margin_top}; margin-bottom: 4px;">{text}</p>'
            )
            if level <= 2:
                html_parts.append("<hr/>")
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}$", stripped):
            html_parts.append(flush_list())
            html_parts.append("<hr/>")
            continue

        # Unordered list
        m = re.match(r"^[-*+]\s+(.*)", stripped)
        if m:
            if not in_ul:
                html_parts.append(flush_list())
                html_parts.append("<ul>")
                in_ul = True
            html_parts.append(f"<li>{inline_format(html.escape(m.group(1)))}</li>")
            continue

        # Ordered list
        m = re.match(r"^\d+\.\s+(.*)", stripped)
        if m:
            if not in_ol:
                html_parts.append(flush_list())
                html_parts.append("<ol>")
                in_ol = True
            html_parts.append(f"<li>{inline_format(html.escape(m.group(1)))}</li>")
            continue

        # Indented continuation (sub-items)
        if line.startswith("  ") and (in_ul or in_ol):
            m2 = re.match(r"^\s+[-*+]\s+(.*)", line)
            if m2:
                html_parts.append(f"<li style='margin-left: 20px;'>{inline_format(html.escape(m2.group(1)))}</li>")
                continue
            m2 = re.match(r"^\s+\d+\.\s+(.*)", line)
            if m2:
                html_parts.append(f"<li style='margin-left: 20px;'>{inline_format(html.escape(m2.group(1)))}</li>")
                continue

        # Regular paragraph
        html_parts.append(flush_list())
        html_parts.append(f"<p>{inline_format(html.escape(stripped))}</p>")

    # Close any open blocks
    if in_code_block:
        html_parts.append("</pre>")
    if in_table:
        html_parts.append(flush_table())
    html_parts.append(flush_list())

    return "\n".join(html_parts)


def create_pdf(html_content: str, output_path: str, title: str):
    """Create a PDF from HTML content using PyMuPDF Story API."""
    CSS = """
    body {
        font-family: "Microsoft JhengHei", "微軟正黑體", sans-serif;
        font-size: 10px;
        line-height: 1.5;
        color: #333;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #1a1a1a;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        font-size: 9px;
        margin: 6px 0;
    }
    th {
        background-color: #e8e8e8;
        font-weight: bold;
        text-align: left;
        padding: 4px 6px;
    }
    td {
        padding: 3px 6px;
        vertical-align: top;
    }
    pre {
        font-family: "Consolas", "Courier New", monospace;
        font-size: 8.5px;
        background-color: #f5f5f5;
        padding: 8px;
        border: 1px solid #ddd;
    }
    code {
        font-family: "Consolas", "Courier New", monospace;
        font-size: 9px;
        background-color: #f0f0f0;
        padding: 1px 3px;
    }
    hr {
        border: none;
        border-top: 1px solid #ccc;
        margin: 6px 0;
    }
    ul, ol {
        margin: 4px 0;
        padding-left: 20px;
    }
    li {
        margin: 2px 0;
    }
    p {
        margin: 4px 0;
    }
    """

    # Wrap in full HTML
    full_html = f"""<!DOCTYPE html>
<html>
<head>
<style>{CSS}</style>
</head>
<body>
<p style="font-size: 22px; font-weight: bold; color: #0056b3; margin-bottom: 4px;">{html.escape(title)}</p>
<hr style="border-top: 2px solid #0056b3;"/>
{html_content}
</body>
</html>"""

    # A4 page dimensions in points
    WIDTH, HEIGHT = fitz.paper_size("a4")
    MARGIN = 50  # ~1.76 cm margins

    writer = fitz.DocumentWriter(output_path)
    story = fitz.Story(full_html, user_css=CSS, archive=fitz.Archive())

    # Register font
    story.reset()

    more = True
    while more:
        dev = writer.begin_page(fitz.Rect(0, 0, WIDTH, HEIGHT))
        # Content area with margins
        where = fitz.Rect(MARGIN, MARGIN, WIDTH - MARGIN, HEIGHT - MARGIN)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()

    writer.close()
    print(f"  -> {output_path}")


def main():
    import os

    base = os.path.dirname(os.path.abspath(__file__))

    files = [
        {
            "input": os.path.join(base, ".claude", "agents", "phase1-reader.md"),
            "output": os.path.join(base, "Phase1-Reader-Agent.pdf"),
            "title": "Phase 1 READER Agent — 結構配置圖判讀專家",
        },
        {
            "input": os.path.join(base, ".claude", "commands", "bts-structure.md"),
            "output": os.path.join(base, "BTS-Structure-Workflow.pdf"),
            "title": "BTS-STRUCTURE — Phase 1 主結構建模流程",
        },
        {
            "input": os.path.join(base, "skills", "plan-reader", "SKILL.md"),
            "output": os.path.join(base, "Plan-Reader-SKILL.pdf"),
            "title": "結構配置圖核心解讀器 (Plan Reader)",
        },
    ]

    for f in files:
        print(f"Converting: {os.path.basename(f['input'])}")
        with open(f["input"], "r", encoding="utf-8") as fh:
            md_text = fh.read()
        html_content = md_to_html(md_text)
        create_pdf(html_content, f["output"], f["title"])

    print("\nDone! 3 PDF files created.")


if __name__ == "__main__":
    main()
