import sys
import os
import bs4
from bs4 import BeautifulSoup
import copy

def prep_file(in_path, out_path):
    with open(in_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Add style
    head = soup.find('head')
    if head and not head.find('style'):
        style = soup.new_tag('style')
        style.string = "\n.eng.hidden { display: none; }\n.vn.visible { color: #000; }\n"
        head.append(style)

    tags_to_duplicate = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'caption', 'figcaption', 'th', 'td']
    
    # We only want to duplicate tags that don't contain other tags from the list, or we just duplicate the deepest ones?
    # Actually, in OpenStax, it's safer to duplicate tags that directly contain text or inline elements (span, a, em, strong, sup, sub).
    # But for simplicity, let's duplicate any tag in tags_to_duplicate IF it does not contain another tag in tags_to_duplicate.
    for tag_name in tags_to_duplicate:
        for tag in soup.find_all(tag_name):
            # Check if it contains another duplicatable tag
            contains_block = False
            for child in tag.find_all(tags_to_duplicate):
                contains_block = True
                break
            
            if contains_block:
                continue # Let the inner tags be duplicated instead
                
            # If it already has eng hidden, skip
            if 'eng' in tag.get('class', []) and 'hidden' in tag.get('class', []):
                continue
            
            # Duplicate
            new_tag = copy.copy(tag)
            
            # Modify original (eng)
            classes = tag.get('class', [])
            if 'eng' not in classes: classes.append('eng')
            if 'hidden' not in classes: classes.append('hidden')
            tag['class'] = classes
            
            # Modify new (vn)
            vn_classes = new_tag.get('class', [])
            if 'vn' not in vn_classes: vn_classes.append('vn')
            if 'visible' not in vn_classes: vn_classes.append('visible')
            new_tag['class'] = vn_classes
            
            if new_tag.get('id'):
                new_tag['id'] = new_tag['id'] + '-vn'
                
            tag.insert_after(new_tag)

    # Save
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))

if __name__ == '__main__':
    in_file = sys.argv[1]
    out_file = sys.argv[2]
    prep_file(in_file, out_file)
