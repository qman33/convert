# convert

A small command-line tool to convert files to another format. The output file is saved next to the source file with a new extension.

Supports audio, video, PNG/ICO icons, and MonoGame/XNA texture (XNB) files.

## Setup

```cmd
pip install -r requirements.txt
```

Requires Python on your PATH. Audio and video conversions also need ffmpeg (bundled via `imageio-ffmpeg`).

## Usage

Two ways to run it:

```cmd
convert <from> <to> <path\to\file>
convert <to> <path\to\file>
```

The second form guesses `<from>` from the file extension. For example, `convert ogg C:\path\to\file.mp3` is the same as `convert mp3 ogg C:\path\to\file.mp3`.

Examples:

```cmd
convert mp3 ogg C:\path\to\file.mp3
convert mp3 wav C:\path\to\file.mp3
convert wav mp3 C:\path\to\file.wav
convert mp4 ogv C:\path\to\file.mp4
convert xnb png C:\path\to\texture.xnb
convert png xnb C:\path\to\texture.png
convert png ico C:\path\to\icon.png
convert ico png C:\path\to\icon.ico
convert ogg C:\path\to\file.mp3
```

Run from this folder, or pass the full path to `convert.cmd`.

If the output file already exists, it is replaced.

## Supported conversions

| From | To |
|------|----|
| mp3 | ogg, wav |
| ogg | mp3 |
| wav | mp3 |
| mp4 | ogv |
| ogv | mp4 |
| png | ico, xnb |
| ico | png |
| xnb | png |

Run `convert` with no arguments to print the full list.

## Icon conversions

PNG and ICO conversions keep transparency. ICO files can include multiple sizes; converting ICO to PNG uses the largest embedded image.

## XNB texture conversions

Supports MonoGame/XNA 4 PC `Texture2D` files only:

- XNB version 4/5, common PC platforms (`w`, `d`, etc.)
- `SurfaceFormat.Color` (BGRA8888) and DXT1/DXT5 compressed textures
- Single mip level
- Compressed input supported (LZX and LZ4)
- PNG to XNB output is uncompressed

Limitations:

- Only `Texture2D` image assets can be converted to PNG (not maps, fonts, audio, etc.)
- Map files using `xTile.Pipeline.TideReader` (common in Stardew Valley) are not textures
- DXT3 surface format is not supported yet
- Other surface formats (Bgr565, Bgra4444, etc.) are not supported

Alpha is converted between premultiplied XNB pixels and straight-alpha PNG for editing.
