# On the Linux runner: install free look-alike fonts under the Windows family names Chrome asks for,
# so frames match the laptop (Windows Chrome: Arial 400/700, Arial Black for 800-900, Comic Sans MS, Georgia).
# Windows fonts themselves are never uploaded.
import glob, os, sys
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.expanduser('~/.fonts'); os.makedirs(OUT, exist_ok=True)
LIB = '/usr/share/fonts/truetype/liberation'

def rename(src, family, style, weight, out_name):
    f = TTFont(src)
    nm = f['name']
    for rec in list(nm.names):
        if rec.nameID in (16, 17, 21, 22, 25): nm.removeNames(nameID=rec.nameID)
    full = family if style == 'Regular' else f'{family} {style}'
    for nid, val in ((1, family), (2, style), (4, full), (6, full.replace(' ', '') + '-cloud')):
        nm.setName(val, nid, 3, 1, 0x409); nm.setName(val, nid, 1, 0, 0)
    f['OS/2'].usWeightClass = weight
    sel = f['OS/2'].fsSelection & ~0b1100001
    if 'Bold' in style and weight >= 700: sel |= 0b100000
    if 'Italic' in style: sel |= 0b1
    if style == 'Regular': sel |= 0b1000000
    f['OS/2'].fsSelection = sel
    f.save(os.path.join(OUT, out_name)); print('font', full, weight, '<-', os.path.basename(src))

F = os.path.join(HERE, 'fonts')
rename(f'{LIB}/LiberationSans-Regular.ttf', 'Arial', 'Regular', 400, 'cl_arial.ttf')
rename(f'{LIB}/LiberationSans-Bold.ttf', 'Arial', 'Bold', 700, 'cl_arialbd.ttf')
rename(f'{LIB}/LiberationSans-Italic.ttf', 'Arial', 'Italic', 400, 'cl_ariali.ttf')
rename(f'{LIB}/LiberationSans-BoldItalic.ttf', 'Arial', 'Bold Italic', 700, 'cl_arialbi.ttf')
rename(f'{F}/ArchivoBlack-Regular.ttf', 'Arial', 'Black', 800, 'cl_ariblk.ttf')  # 800 so fontconfig picks it for both 800 and 900 (Windows uses Arial Black for both)
rename(f'{F}/ComicNeue-Regular.ttf', 'Comic Sans MS', 'Regular', 400, 'cl_comic.ttf')
rename(f'{F}/ComicNeue-Bold.ttf', 'Comic Sans MS', 'Bold', 700, 'cl_comicbd.ttf')
rename(f'{F}/Gelasio-Regular.ttf', 'Georgia', 'Regular', 400, 'cl_georgia.ttf')
rename(f'{F}/Gelasio-Bold.ttf', 'Georgia', 'Bold', 700, 'cl_georgiab.ttf')
rename(f'{F}/Gelasio-Italic.ttf', 'Georgia', 'Italic', 400, 'cl_georgiai.ttf')
