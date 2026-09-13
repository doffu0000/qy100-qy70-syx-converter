from pathlib import Path

# ── Folder paths ──────────────────────────────────────────────────────────────
BASE = Path(r"C:\Users\sheam\Desktop\QY100\SYX Converter")
QY70_IN  = BASE / "QY70 SYX To Be Converted"
QY100_IN = BASE / "QY100 SYX To Be Converted"
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

# ── Main ──────────────────────────────────────────────────────────────────────
def process_folder(src_folder: Path, convert_fn, suffix_from: str, suffix_to: str):
    files = list(src_folder.glob("*.syx")) + list(src_folder.glob("*.SYX"))
    if not files:
        print(f"  No .syx files found in {src_folder.name}")
        return

    for src in files:
        stem = src.stem  # e.g. "Dip_QY70"
        if suffix_from in stem:
            out_stem = stem.replace(suffix_from, suffix_to)
        else:
            out_stem = stem + suffix_to  # fallback

        dst = OUT_DIR / (out_stem + ".syx")

        result = convert_fn(src.read_bytes())
        if result is None:
            print(f"  [SKIP]  {src.name}  — no convertible bulk messages found")
            continue

        dst.write_bytes(result)
        print(f"  [OK]    {src.name}  →  {dst.name}")

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("QY100 → QY70  (reading from 'QY100 SYX To Be Converted')")
    print('='*60)
    process_folder(QY100_IN, convert_qy100_to_qy70, "_QY100", "_QY70")

    print(f"\n{'='*60}")
    print("QY70  → QY100 (reading from 'QY70 SYX To Be Converted')")
    print('='*60)
    process_folder(QY70_IN, convert_qy70_to_qy100, "_QY70", "_QY100")

    print(f"\nDone. Converted files are in:\n  {OUT_DIR}\n")

if __name__ == "__main__":
    main()