import re
from collections import defaultdict

files = {
    'A': r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\A\2026-0303_A_SC_KpKvKw.e2k",
    'B': r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\B\2026-0303_B_SC_KpKvKw.e2k",
    'C': r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\C\2026-0304_C_SC_KpKvKw.e2k",
    'D': r"C:\Users\User\Desktop\V22 AGENTIC MODEL\ETABS REF\大陳\D\2026-0303_D_SC_KpKvKw.e2k",
}

target_stories = ['25F','26F','27F','28F','29F','30F','R1F','R2F','R3F','PRF']

col_section_re = re.compile(r'^(C|SRC|RC|CC|SC)\d+[Xx]\d+', re.IGNORECASE)

for bldg, fpath in files.items():
    print("="*80)
    print(f"BUILDING {bldg}")
    print("="*80)

    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.split('\n')

    # ---- Parse FRAMESECTION definitions ----
    # Only store when D/B or T3/T2 are present (skip modifier-only lines)
    frame_sections = {}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('FRAMESECTION'):
            m = re.match(r'FRAMESECTION\s+"([^"]+)"', stripped)
            if m:
                sec_name = m.group(1)
                props = {}
                mm = re.search(r'MATERIAL\s+"([^"]+)"', stripped)
                if mm:
                    props['material'] = mm.group(1)
                ms = re.search(r'SHAPE\s+"([^"]+)"', stripped)
                if ms:
                    props['shape'] = ms.group(1)
                md = re.search(r'\bD\s+([\d.Ee+-]+)', stripped)
                if md:
                    props['D'] = float(md.group(1))
                mb_match = re.search(r'\bB\s+([\d.Ee+-]+)', stripped)
                if mb_match:
                    props['B'] = float(mb_match.group(1))
                mt3 = re.search(r'\bT3\s+([\d.Ee+-]+)', stripped)
                if mt3:
                    props['T3'] = float(mt3.group(1))
                mt2 = re.search(r'\bT2\s+([\d.Ee+-]+)', stripped)
                if mt2:
                    props['T2'] = float(mt2.group(1))

                # Only store/update if we found meaningful geometry data or it's the first occurrence
                has_geom = 'D' in props or 'B' in props or 'T3' in props or 'T2' in props
                has_shape = 'shape' in props
                if has_geom or (has_shape and sec_name not in frame_sections):
                    if sec_name in frame_sections:
                        # Merge: keep existing geom, add new data
                        frame_sections[sec_name].update(props)
                    else:
                        frame_sections[sec_name] = props

    # ---- Parse AUTOSECTION entries for auto-select lists ----
    auto_sections = defaultdict(list)
    autosec_re = re.compile(r'^\s+AUTOSECTION\s+"([^"]+)"\s+(.*)')
    for line in lines:
        m = autosec_re.match(line)
        if m:
            list_name = m.group(1)
            rest = m.group(2)
            # Extract all quoted section names
            members = re.findall(r'"([^"]+)"', rest)
            auto_sections[list_name].extend(members)

    # ---- Parse LINEASSIGN lines ----
    lineassign_re = re.compile(
        r'^\s+LINEASSIGN\s+"([^"]+)"\s+"([^"]+)"\s+SECTION\s+"([^"]+)"'
    )

    story_section_frames = defaultdict(lambda: defaultdict(list))
    all_sections_used = set()

    for line in lines:
        m = lineassign_re.match(line)
        if m:
            frame_name = m.group(1)
            story_name = m.group(2)
            section_name = m.group(3)

            if story_name not in target_stories:
                continue

            # Check if column section
            is_col = bool(col_section_re.match(section_name))
            if not is_col and re.match(r'^C\d', frame_name):
                is_col = True
            if not is_col and re.search(r'C\d+[Xx]\d+', section_name, re.IGNORECASE):
                is_col = True
            if not is_col and re.search(r'SRC\d+', section_name, re.IGNORECASE):
                is_col = True

            if is_col:
                story_section_frames[story_name][section_name].append(frame_name)
                all_sections_used.add(section_name)

    # Print column assignment results
    print(f"\n{'='*60}")
    print(f"  COLUMN SECTIONS AT STORIES 25F THROUGH PRF")
    print(f"{'='*60}\n")

    for story in target_stories:
        if story in story_section_frames:
            sec_data = story_section_frames[story]
            total = sum(len(v) for v in sec_data.values())
            print(f"  STORY {story}: ({total} columns total)")
            for sec_name in sorted(sec_data.keys()):
                count = len(sec_data[sec_name])
                frames_list = sorted(sec_data[sec_name], key=lambda x: (len(x), x))
                print(f"    {sec_name}: {count} columns")
                if count <= 20:
                    print(f"      frames: {', '.join(frames_list)}")
                else:
                    print(f"      frames (first 20): {', '.join(frames_list[:20])} ...")
            print()
        else:
            print(f"  STORY {story}: (not found in this model)\n")

    # Print FRAMESECTION dimensions
    print(f"{'='*60}")
    print(f"  FRAME SECTION DIMENSIONS FOR COLUMN SECTIONS")
    print(f"{'='*60}\n")

    if bldg == 'B':
        unit_note = "B model: values in meters"
    else:
        unit_note = f"{bldg} model: values in cm"

    print(f"  ({unit_note})\n")

    for sec_name in sorted(all_sections_used):
        if sec_name in frame_sections:
            props = frame_sections[sec_name]
            d_val = props.get('D', props.get('T3', None))
            b_val = props.get('B', props.get('T2', None))
            mat = props.get('material', '?')
            shape = props.get('shape', '?')

            if d_val is not None and b_val is not None:
                if bldg == 'B':
                    d_cm = d_val * 100
                    b_cm = b_val * 100
                    print(f"  {sec_name}: D={d_val}m ({d_cm:.0f}cm), B={b_val}m ({b_cm:.0f}cm)  [material={mat}, shape={shape}]")
                else:
                    d_m = d_val / 100
                    b_m = b_val / 100
                    print(f"  {sec_name}: D={d_val:.0f}cm ({d_m:.2f}m), B={b_val:.0f}cm ({b_m:.2f}m)  [material={mat}, shape={shape}]")
            else:
                print(f"  {sec_name}: shape={shape}  [D={d_val}, B={b_val}]")
                # If it's an auto-select list, show the member sections
                if sec_name in auto_sections:
                    members = auto_sections[sec_name]
                    print(f"    AUTO SELECT LIST with {len(members)} candidate sections:")
                    # Show first few and last few
                    if len(members) <= 10:
                        for ms in members:
                            print(f"      - {ms}")
                    else:
                        for ms in members[:5]:
                            print(f"      - {ms}")
                        print(f"      ... ({len(members)-10} more) ...")
                        for ms in members[-5:]:
                            print(f"      - {ms}")
        else:
            print(f"  {sec_name}: [FRAMESECTION definition NOT FOUND]")

    # Show what story the section transitions happen
    print(f"\n{'='*60}")
    print(f"  SECTION TRANSITION SUMMARY")
    print(f"{'='*60}\n")

    # For each column frame that appears in any target story, show story->section mapping
    all_col_frames = set()
    for story in target_stories:
        for sec_name, frames in story_section_frames.get(story, {}).items():
            all_col_frames.update(frames)

    frame_story_sec = {}
    for frame in sorted(all_col_frames, key=lambda x: (len(x), x)):
        story_map = {}
        for story in target_stories:
            for sec_name, frames in story_section_frames.get(story, {}).items():
                if frame in frames:
                    story_map[story] = sec_name
        frame_story_sec[frame] = story_map

    # Group frames with identical story->section patterns
    pattern_frames = defaultdict(list)
    for frame, story_map in frame_story_sec.items():
        key = tuple((s, story_map.get(s, '-')) for s in target_stories)
        pattern_frames[key].append(frame)

    for pattern, frames in sorted(pattern_frames.items(), key=lambda x: -len(x[1])):
        print(f"  Pattern for {len(frames)} columns: {', '.join(sorted(frames, key=lambda x: (len(x),x)))}")
        for story, sec in pattern:
            if sec != '-':
                print(f"    {story}: {sec}")
        print()

    print("\n")

print("DONE")
