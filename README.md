# QY100 / QY70 SysEx Converter

Converts Bulk Dump SysEx (`.syx`) files between the Yamaha QY100 and QY70, so patterns and songs made on one machine can be loaded on the other.

Two versions of the same converter are included:

- `syx_converter.html`, a standalone browser tool. Drop a `.syx` file in, get the converted file back. Runs entirely client side, no upload involved.
- `SYX_Converter.py`, a batch script that reads `.syx` files from local folders and writes the converted versions to an output folder.

## How it works

Pattern (`tr` type `2`) and song (`tr` type `1`) Bulk Dump SEQ Data blocks are converted; anything else in the file is left alone. Converting only changes the machine ID nibble in the address byte, the block type, address bytes, and data are all preserved as is. Checksums are recomputed using Yamaha's two's complement convention, verified against real QY100 hardware and against `protocol.py` in [qy100-toolkit](https://github.com/doffu0000/qy100-toolkit).

## Using the Python script

`SYX_Converter.py` expects three folders next to it:

- `QY100 SYX To Be Converted/`, QY100 files to convert to QY70 format
- `QY70 SYX To Be Converted/`, QY70 files to convert to QY100 format
- `Converted Files/`, where the output lands

Run it with `python SYX_Converter.py`.
