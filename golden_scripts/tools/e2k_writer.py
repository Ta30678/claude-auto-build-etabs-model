"""
E2K file writer — reconstructs e2k text from an E2KModel's raw_sections.
Maintains correct section ordering and formatting.
"""
from golden_scripts.tools.e2k_parser import SECTION_ORDER


def write_e2k(model, output_path):
    """Write an E2KModel to an e2k file.

    Args:
        model: E2KModel instance
        output_path: destination file path
    """
    text = to_text(model)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)


def to_text(model):
    """Convert an E2KModel to e2k text string.

    Sections are written in canonical order (SECTION_ORDER).
    Sections not in SECTION_ORDER are appended at the end (before END OF MODEL FILE).
    """
    lines = []

    # Header
    if '__HEADER__' in model.raw_sections:
        lines.append(model.raw_sections['__HEADER__'])
        lines.append('')

    # Collect ordered and unordered sections
    written = {'__HEADER__', 'END OF MODEL FILE'}
    ordered_sections = []
    for sec_name in SECTION_ORDER:
        if sec_name == 'END OF MODEL FILE':
            continue
        if sec_name in model.raw_sections:
            ordered_sections.append(sec_name)
            written.add(sec_name)

    # Sections in file but not in SECTION_ORDER
    extra_sections = [k for k in model.raw_sections if k not in written]

    # Write ordered sections
    for sec_name in ordered_sections:
        text = model.raw_sections[sec_name]
        lines.append(f'$ {sec_name}')
        if text:
            lines.append(text)
        lines.append('')

    # Write extra sections (before END)
    for sec_name in extra_sections:
        text = model.raw_sections[sec_name]
        lines.append(f'$ {sec_name}')
        if text:
            lines.append(text)
        lines.append('')

    # END marker
    lines.append('$ END OF MODEL FILE')
    lines.append('')

    return '\n'.join(lines)


def format_float(value, precision=6):
    """Format a float for e2k output, removing trailing zeros."""
    s = f'{value:.{precision}f}'
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s
