#!/usr/bin/env python3
"""Merge two .po files: use main as base, add entries unique to HEAD."""
import sys
import re

def parse_po(filepath):
    """Parse a .po file into header and entries dict (keyed by msgid string)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into blocks separated by one or more blank lines
    blocks = re.split(r'\n\n+', content)
    header = None
    entries = {}
    order = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Extract msgid value
        msgid_match = re.search(r'^msgid\s+"(.*)"', block, re.MULTILINE)
        if not msgid_match:
            continue

        msgid_val = msgid_match.group(1)

        # Handle multiline msgid
        lines = block.split('\n')
        full_msgid = ''
        in_msgid = False
        for line in lines:
            if line.startswith('msgid "'):
                in_msgid = True
                m = re.match(r'msgid "(.*)"', line)
                if m:
                    full_msgid = m.group(1)
            elif in_msgid and line.startswith('"'):
                m = re.match(r'"(.*)"', line)
                if m:
                    full_msgid += m.group(1)
            else:
                if in_msgid:
                    in_msgid = False

        if full_msgid == '':
            # This is the header block
            header = block
        else:
            entries[full_msgid] = block
            if full_msgid not in order:
                order.append(full_msgid)

    return header, entries, order


def main():
    head_file = '/tmp/po_head.po'
    main_file = '/tmp/po_main.po'
    output_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/po_merged.po'

    head_header, head_entries, head_order = parse_po(head_file)
    main_header, main_entries, main_order = parse_po(main_file)

    print(f"HEAD: {len(head_entries)} entries", file=sys.stderr)
    print(f"Main: {len(main_entries)} entries", file=sys.stderr)

    # Find entries only in HEAD
    only_in_head = [k for k in head_order if k not in main_entries]
    print(f"Only in HEAD: {len(only_in_head)}", file=sys.stderr)
    for k in only_in_head:
        print(f"  + {k[:80]}", file=sys.stderr)

    # Start with main as base
    merged_order = list(main_order)
    merged_entries = dict(main_entries)

    # Add HEAD-only entries at the end
    for k in only_in_head:
        merged_order.append(k)
        merged_entries[k] = head_entries[k]

    # Write output
    with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
        # Write header
        f.write(main_header + '\n\n')
        # Write all entries
        for k in merged_order:
            f.write(merged_entries[k] + '\n\n')

    total = len(merged_entries)
    print(f"Merged: {total} entries -> {output_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
