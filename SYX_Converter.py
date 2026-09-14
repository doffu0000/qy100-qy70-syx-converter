from pathlib import Path
from collections import OrderedDict

# ── Folder paths ──────────────────────────────────────────────────────────────
BASE = Path(r"C:\Users\sheam\Desktop\QY100\SYX Converter")
QY70_IN  = BASE / "QY70 SYX To Be Converted"
QY100_IN = BASE / "QY100 SYX To Be Converted"
Q1P_IN   = BASE / "Q1P To Be Converted"
Q1S_IN   = BASE / "Q1S To Be Converted"
OUT_DIR  = BASE / "Converted Files"

# ── Helpers ───────────────────────────────────────────────────────────────────
def split_sysex(blob: bytes) -> list[bytearray]:
    """Split a binary blob into individual SysEx messages."""
    out, i, b = [], 0, bytearray(blob)
    while True:
        try:
            s = b.index(0xF0, i)
            e = b.index(0xF7, s)
        except ValueError:
            break
        out.append(b[s:e+1])
        i = e + 1
    return out

def y_checksum(payload: bytes) -> int:
    """Two's complement of the 7-bit sum. Yamaha convention, verified against
    protocol.py in qy100-toolkit (60+ real hardware messages, zero failures)."""
    return (-sum(payload)) & 0x7F

# ── QY100 <-> QY70 ────────────────────────────────────────────────────────────
# Bulk Dump SEQ Data: F0 43 00 5F 01 13 aH aM aL <147 bytes> <chk> F7
# aH packs the machine (P nibble, high) and the block type (low nibble):
#   pattern: aH = 0x12 (QY100) / 0x02 (QY70)
#   song:    aH = 0x11 (QY100) / 0x01 (QY70)
# Converting only ever changes aH's high nibble (P); the low nibble (type),
# address bytes, and data are all preserved as-is.
# Checksum spans byte-count + addr + data, i.e. bytes[4:-2] of the message
# (NOT bytes[5:-2] -- that drops the byte-count-high byte from the sum).
#
# Bulk mode ON/OFF opener/closer: F0 43 10 5F aH 00 00 dd F7, aH = P<<4,
# dd = 1 (ON) / 0 (OFF).

P_QY100, P_QY70 = 1, 0


def is_seq_bulk(m: bytearray, p: int) -> bool:
    return (len(m) >= 9 and m[0] == 0xF0 and m[1] == 0x43
            and m[3] == 0x5F and m[4] == 0x01
            and (m[6] >> 4) == p and (m[6] & 0x0F) in (0x01, 0x02))


def _bulk_mode(p: int, on: bool) -> bytearray:
    return bytearray([0xF0, 0x43, 0x10, 0x5F, p << 4, 0x00, 0x00, 1 if on else 0, 0xF7])


def _convert(raw: bytes, src_p: int, dest_p: int) -> bytes | None:
    msgs = split_sysex(raw)
    out = bytearray(_bulk_mode(dest_p, True))
    converted_any = False
    for m in msgs:
        if not is_seq_bulk(m, src_p):
            continue
        new_msg = bytearray(m)
        new_msg[6] = (dest_p << 4) | (m[6] & 0x0F)  # keep type nibble (pattern/song)
        new_msg[-2] = y_checksum(bytes(new_msg[4:-2]))
        out += new_msg
        converted_any = True
    out += _bulk_mode(dest_p, False)
    return bytes(out) if converted_any else None


def convert_qy100_to_qy70(raw: bytes) -> bytes | None:
    return _convert(raw, P_QY100, P_QY70)


def convert_qy70_to_qy100(raw: bytes) -> bytes | None:
    return _convert(raw, P_QY70, P_QY100)


# ── Q1P / Q1S (QY100 disk file) <-> SysEx ────────────────────────────────────
#
# .Q1P (style/pattern) and .Q1S (song) are the QY100's own SmartMedia disk
# format -- QY70 has no disk drive, so these are QY100-only. Reverse engineered
# from paired reference dumps (same pattern/song saved to disk *and* bulk-dumped
# over SysEx), cross-checked against qy100-toolkit's already-verified 7-in-8
# bit-packing and pattern/song track addressing.
#
# Layout: a fixed 128-byte header, followed by every SEQ Data block's payload
# with the wire's 7-bit packing undone (147 bytes -> 128 bytes, top 5 bits of
# the last packed byte are discarded -- this happens fresh per block, not
# continuously across the file), concatenated in ascending track-address (aL)
# order. The pattern/song "header" block (aL = 0x7F) always sorts last since
# 0x7F is numerically the highest track address.
#
# The header's own bytes carry a per-track table -- how many SysEx blocks
# each track occupies, which is what lets the flat body be split back into
# per-track chunks. Verified exactly (block counts match to the byte) against
# 4 pattern and 3 song reference pairs spanning 13-191 blocks, and sanity
# checked against every real .Q1P/.Q1S file on this machine (1952 patterns,
# 8 songs): every one of them divides evenly into the table's blocks plus a
# remainder for the 0x7F track, with zero exceptions.
#
# The 0x7F track's own size is NOT fixed. An earlier version of this file
# assumed 5 blocks for patterns and 6 for songs because that's what all the
# original reference pairs happened to have -- but checking the full local
# collection found patterns ranging from 4 to 34 blocks (5 is just the most
# common, at 72%) and at least one 7-block song. It isn't listed in the
# table either, so q1_to_syx derives it from the file's own size: whatever
# body bytes are left over after every named track's blocks are accounted
# for. That computation should never come out uneven -- if it does, the
# file's table doesn't match its size and something is corrupt.
#
# Two things remain unidentified and are approximated rather than guessed
# at outright: a mystery byte at header offset 16 (pattern files only, no
# correlation found against header size or track count across the full
# local collection), and the padding convention past a track's real data
# end (the disk file zero-fills; the wire dump leaves whatever was in that
# RAM region, usually ending in a run of 0xFE). For the *song* header track
# specifically, the disk file only ever uses the first 654 of its 768
# bytes -- confirmed zero past that point in all 3 reference songs, with
# the wire dump showing identical leftover bytes (including a literal
# "04 B0" at the same offset) in two of them despite different content, so
# syx_to_q1 zero-fills that tail rather than carrying the wire's garbage
# into the disk file. The equivalent boundary for patterns isn't pinned
# down yet (would need a fresh pattern + matching hardware dump to verify
# the same way), so it's left untouched there. None of this affects the
# musical content either way, only unused filler bytes.

BLOCK_BYTES = 147
UNPACKED_BYTES = 128
HEADER_SIZE = 128
HEADER_TR = 0x7F
EDIT_BUFFER_AM = 0x7E  # aM used by the reference dumps -- the "current pattern/song" slot

# Track address table: contiguous phrase/section tracks, then (for songs) the
# handful of special tracks -- Pt (0x19, style/section arrangement) and Cd
# (0x1A, chords) are named in qy100-toolkit's songfmt.py; 0x1B showed up in
# every song reference sample but isn't identified there yet.
PATTERN_TRACKS = list(range(0, 47))
SONG_TRACKS = list(range(0, 16)) + [0x19, 0x1A, 0x1B]

KINDS = {
    "pattern": dict(sig=b"YQ1PAT", type_nibble=2, table_start=18,
                     tracks=PATTERN_TRACKS, header_blocks=5, ext=".Q1P"),
    "song":    dict(sig=b"YQ1SNG", type_nibble=1, table_start=32,
                     tracks=SONG_TRACKS, header_blocks=6, ext=".Q1S"),
}


def unpack_block(payload: bytes) -> bytes:
    """147 bytes of 7-bit wire data -> 128 bytes of 8-bit data (5 leftover bits dropped)."""
    bits = []
    for b in payload:
        for k in range(6, -1, -1):
            bits.append((b >> k) & 1)
    out = bytearray()
    for i in range(0, (len(bits) // 8) * 8, 8):
        v = 0
        for k in range(8):
            v = (v << 1) | bits[i + k]
        out.append(v)
    return bytes(out)


def pack_block(data: bytes, size: int = BLOCK_BYTES) -> bytes:
    """Inverse of unpack_block: 8-bit bytes -> 7-bit wire bytes, zero-padded to `size`."""
    bits = []
    for b in data:
        for k in range(7, -1, -1):
            bits.append((b >> k) & 1)
    bits += [0] * (size * 7 - len(bits))
    out = bytearray()
    for i in range(0, size * 7, 7):
        v = 0
        for k in range(7):
            v = (v << 1) | bits[i + k]
        out.append(v)
    return bytes(out)


def detect_q1_kind(data: bytes) -> str | None:
    sig = data[0:16]
    for name, k in KINDS.items():
        if sig[:6] == k["sig"]:
            return name
    return None


def q1_to_syx(data: bytes) -> tuple[bytes, str]:
    """.Q1P/.Q1S bytes -> a QY100-format (P=1) bulk-dump SysEx stream."""
    kind = detect_q1_kind(data)
    if kind is None:
        raise ValueError("not a recognized Q1P/Q1S file (bad signature %r)" % data[0:6])
    k = KINDS[kind]
    header = data[0:HEADER_SIZE]
    body = data[HEADER_SIZE:]

    order = []
    named_blocks = 0
    for slot, tr in enumerate(k["tracks"]):
        off = k["table_start"] + 2 * slot
        count = (header[off] << 8) | header[off + 1]
        if count:
            order.append((tr, count))
            named_blocks += count

    # The header/"cabecera" track (0x7F) isn't listed in the table -- its
    # size isn't fixed (checked against 1952 real .Q1P files: ~72% have 5
    # blocks, but sizes from 4 to 34 all occur; same story for .Q1S). It's
    # always the remainder after every named track's blocks are accounted
    # for, so derive it from the file's own size instead of assuming one.
    remaining = len(body) - named_blocks * UNPACKED_BYTES
    if remaining < 0 or remaining % UNPACKED_BYTES != 0:
        raise ValueError("%s file size doesn't match its own block-count table "
                          "(corrupt file?)" % k["ext"])
    header_blocks = remaining // UNPACKED_BYTES
    order.append((HEADER_TR, header_blocks))

    out = bytearray(_bulk_mode(P_QY100, True))
    pos = 0
    for tr, count in order:
        for _ in range(count):
            chunk = body[pos:pos + UNPACKED_BYTES]
            pos += UNPACKED_BYTES
            msg = bytearray([0xF0, 0x43, 0x00, 0x5F, 0x01, 0x13,
                              (P_QY100 << 4) | k["type_nibble"], EDIT_BUFFER_AM, tr])
            msg += pack_block(chunk)
            msg.append(y_checksum(bytes(msg[4:])))
            msg.append(0xF7)
            out += msg
    out += _bulk_mode(P_QY100, False)
    return bytes(out), kind


def syx_to_q1(raw: bytes, kind: str) -> bytes | None:
    """A QY100-format (P=1) bulk-dump SysEx stream -> .Q1P/.Q1S bytes.

    Returns None if the stream has no blocks of the requested kind.
    """
    k = KINDS[kind]
    by_track: "OrderedDict[int, list[bytes]]" = OrderedDict()
    for m in split_sysex(raw):
        if not is_seq_bulk(m, P_QY100) or (m[6] & 0x0F) != k["type_nibble"]:
            continue
        by_track.setdefault(m[8], []).append(m[9:-2])

    if not by_track:
        return None

    header = bytearray(HEADER_SIZE)
    header[0:16] = (k["sig"] + b" " * (11 - len(k["sig"])) + b"V1.00")[:16]
    if kind == "pattern":
        header[112:128] = bytes([0x00, 0x00, 0x02, 0x22] + [0] * 12)
    else:
        header[72:74] = bytes([0x02, 0x8E])

    body = bytearray()
    for slot, tr in enumerate(k["tracks"]):
        blocks = by_track.get(tr, [])
        off = k["table_start"] + 2 * slot
        header[off] = (len(blocks) >> 8) & 0xFF
        header[off + 1] = len(blocks) & 0xFF
        for payload in blocks:
            body += unpack_block(payload)

    header_payloads = by_track.get(HEADER_TR, [])
    header_track_start = len(body)
    for payload in header_payloads:
        body += unpack_block(payload)

    # The song header track's real fields (tempo, name, arrangement info)
    # only ever use the first 654 of its 768 bytes on disk -- verified
    # zero past that point in all 3 reference songs (a standard 6-block
    # header), while the wire dump carries whatever was left in that RAM
    # region at capture time (padding bytes, then a stretch of 0xFE).
    # Only the standard-size header is touched; anything else is left as
    # captured rather than guessed at.
    SONG_HEADER_REAL_LEN = 654
    if kind == "song" and len(header_payloads) == 6:
        tail_start = header_track_start + SONG_HEADER_REAL_LEN
        for i in range(tail_start, len(body)):
            body[i] = 0

    return bytes(header) + bytes(body)


# ── Main ──────────────────────────────────────────────────────────────────────
def _glob_ci(folder: Path, ext: str) -> list[Path]:
    """Case-insensitive glob by extension, deduplicated (Windows matches
    "*.syx" and "*.SYX" against the same files, since its filesystem is
    already case-insensitive)."""
    seen: dict[str, Path] = {}
    for p in list(folder.glob(f"*{ext.lower()}")) + list(folder.glob(f"*{ext.upper()}")):
        seen[p.name.lower()] = p
    return list(seen.values())


def process_folder(src_folder: Path, convert_fn, suffix_from: str, suffix_to: str):
    files = _glob_ci(src_folder, ".syx")
    if not files:
        print(f"  No .syx files found in {src_folder.name}")
        return

    for src in files:
        stem = src.stem  # e.g. "Dip_QY70"
        if suffix_from in stem:
            out_stem = stem.replace(suffix_from, suffix_to)
        else:
            out_stem = stem + suffix_to  # fallback

        raw = src.read_bytes()
        result = convert_fn(raw)
        if result is None:
            print(f"  [SKIP]  {src.name}  — no convertible bulk messages found")
            continue

        dst = OUT_DIR / (out_stem + ".syx")
        dst.write_bytes(result)
        print(f"  [OK]    {src.name}  →  {dst.name}")

        # Bonus output: if this QY100-format stream also carries pattern or
        # song data, save the matching .Q1P/.Q1S disk file alongside it.
        qy100_raw = raw if suffix_from == "_QY100" else result
        base_stem = stem.replace(suffix_from, "") if suffix_from in stem else stem
        for kind, k in KINDS.items():
            q1_bytes = syx_to_q1(qy100_raw, kind)
            if q1_bytes is None:
                continue
            q1_dst = OUT_DIR / (base_stem + k["ext"])
            q1_dst.write_bytes(q1_bytes)
            print(f"  [OK]    {src.name}  →  {q1_dst.name}")


def process_q1_folder(src_folder: Path, ext: str):
    files = _glob_ci(src_folder, ext)
    if not files:
        print(f"  No *{ext} files found in {src_folder.name}")
        return

    for src in files:
        data = src.read_bytes()
        try:
            syx_qy100, kind = q1_to_syx(data)
        except ValueError as e:
            print(f"  [SKIP]  {src.name}  — {e}")
            continue

        (OUT_DIR / (src.stem + "_QY100.syx")).write_bytes(syx_qy100)
        print(f"  [OK]    {src.name}  →  {src.stem}_QY100.syx")

        syx_qy70 = convert_qy100_to_qy70(syx_qy100)
        if syx_qy70:
            (OUT_DIR / (src.stem + "_QY70.syx")).write_bytes(syx_qy70)
            print(f"  [OK]    {src.name}  →  {src.stem}_QY70.syx")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for folder in (QY70_IN, QY100_IN, Q1P_IN, Q1S_IN):
        folder.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("QY100 → QY70  (reading from 'QY100 SYX To Be Converted')")
    print('='*60)
    process_folder(QY100_IN, convert_qy100_to_qy70, "_QY100", "_QY70")

    print(f"\n{'='*60}")
    print("QY70  → QY100 (reading from 'QY70 SYX To Be Converted')")
    print('='*60)
    process_folder(QY70_IN, convert_qy70_to_qy100, "_QY70", "_QY100")

    print(f"\n{'='*60}")
    print("Q1P → SysEx  (reading from 'Q1P To Be Converted')")
    print('='*60)
    process_q1_folder(Q1P_IN, ".Q1P")

    print(f"\n{'='*60}")
    print("Q1S → SysEx  (reading from 'Q1S To Be Converted')")
    print('='*60)
    process_q1_folder(Q1S_IN, ".Q1S")

    print(f"\nDone. Converted files are in:\n  {OUT_DIR}\n")

if __name__ == "__main__":
    main()
