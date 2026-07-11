from pathlib import Path
from bs4 import BeautifulSoup, Comment

def convert_inline(node):
    """
    Convert inline formatting tags to Markdown syntax.
    """
    if isinstance(node, str):
        return node
    
    children_text = "".join(convert_inline(child) for child in node.children)
    
    if node.name == 'a':
        href = node.get('href', '')
        return f"[{children_text}]({href})"
    elif node.name == 'strong':
        return f"**{children_text}**"
    elif node.name in ['em', 'i']:
        return f"*{children_text}*"
    elif node.name == 'code':
        return f"`{children_text}`"
    elif node.name == 'sup':
        return f"^{children_text}"
    elif node.name == 'sub':
        return f"_{children_text}"
    elif node.name == 'img':
        alt = node.get('alt', '')
        src = node.get('src', '')
        return f"![{alt}]({src})"
    elif node.name == 'br':
        return "\n"
        
    return children_text

def handle_block(node):
    """
    Convert block level tags to Markdown.
    """
    if isinstance(node, str):
        text = node.strip()
        return [text] if text else []

    if node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        level = int(node.name[1])
        text = convert_inline(node).strip()
        return [f"{'#' * level} {text}", ""]

    elif node.name == 'p':
        text = convert_inline(node).strip()
        return [text, ""]

    elif node.name == 'li':
        text = convert_inline(node).strip()
        parent = node.find_parent(['ol', 'ul'])
        if parent and parent.name == 'ol':
            return [f"1. {text}"]
        return [f"- {text}"]

    elif node.name == 'table':
        rows = []
        headers = []
        for tr in node.find_all('tr'):
            row_cells = []
            for cell in tr.find_all(['th', 'td']):
                row_cells.append(convert_inline(cell).strip())
            if tr.find('th') or not headers:
                headers = row_cells
            else:
                rows.append(row_cells)

        if not headers and rows:
            headers = rows.pop(0)

        if not headers:
            return []

        table_md = []
        table_md.append("| " + " | ".join(headers) + " |")
        table_md.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in rows:
            if len(row) < len(headers):
                row += [""] * (len(headers) - len(row))
            table_md.append("| " + " | ".join(row[:len(headers)]) + " |")
        table_md.append("")
        return table_md

    elif node.name == 'img':
        alt = node.get('alt', '')
        src = node.get('src', '')
        return [f"![{alt}]({src})", ""]

    elif node.name == 'figure':
        lines = []
        for child in node.children:
            lines.extend(handle_block(child))
        return lines

    elif node.name in ['figcaption', 'caption']:
        text = convert_inline(node).strip()
        return [f"*{text}*", ""]

    elif node.name in ['section', 'div', 'aside', 'ol', 'ul', 'body', 'html']:
        lines = []
        for child in node.children:
            if child.name:
                lines.extend(handle_block(child))
        return lines

    return []

def export_html_to_markdown(html_path: Path, md_path: Path):
    """
    Parse HTML file and write markdown contents to target destination.
    """
    md_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    body = soup.find('body') or soup

    markdown_lines = handle_block(body)
    markdown_text = "\n".join(markdown_lines)

    # Clean up excess empty lines
    cleaned_text = re.sub(r'\n{3,}', '\n\n', markdown_text).strip()

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text + "\n")

    return True

import re
