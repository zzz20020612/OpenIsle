"""Deterministic reading metadata derived from preserved parser sections."""
import re


def abstract_from_sections(sections):
    for section in sections[:4]:
        content = section.get('content') or ''
        if section.get('section_type') == 'abstract':
            text = re.sub(r'^\s*Abstract\s*[:：]?\s*', '', content, flags=re.I)
        else:
            match = re.search(r'(?:^|\n)\s*(?:Abstract|摘要)\s*[:：]?\s*(.+)', content, re.I | re.S)
            if not match:
                continue
            text = match.group(1)
        text = re.split(r'\n\s*(?:Keywords?|Key words|关键词|\d+[.]?\s+Introduction)\s*[:：]?', text, flags=re.I)[0].strip()
        if len(text) >= 80:
            return text
    return ''


def reading_sections(sections):
    """Add conservative heading depth; never change stable section identities."""
    result = []
    numbered_parent = False
    for original in sections:
        section = dict(original)
        heading = section.get('heading') or ''
        semantic_heading = re.sub(r'^\s*(?:\d+(?:\.\d+)*|[IVXLCDM]+)[.)]?\s+', '', heading, flags=re.I)
        if re.match(r'(related\s+work|literature\s+review)\b', semantic_heading, re.I):
            section['section_type'] = 'background'
        elif re.match(r'proposed\s+(work|method|approach|system)\b', semantic_heading, re.I):
            section['section_type'] = 'methods'
        number = re.match(r'^\s*(\d+(?:\.\d+)*)(?:[.)]|\s)', heading)
        section['heading_level'] = min(3, number.group(1).count('.') + 1) if number else 1
        if number:
            numbered_parent = True
        elif numbered_parent and not re.match(r'(references?|bibliography|acknowledg|appendix|abstract)\b', semantic_heading, re.I):
            section['heading_level'] = 2
        result.append(section)
    return result


def keywords_from_sections(sections):
    for section in sections[:4]:
        match = re.search(r'(?:^|\n)\s*(?:Keywords?|Key words|关键词)\s*[:：]\s*([^\n]+)', section.get('content') or '', re.I)
        if match:
            return [word.strip() for word in re.split(r'[,;，；]', match.group(1)) if word.strip()]
    return []
