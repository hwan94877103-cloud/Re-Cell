"""Process-sequence storyboard from the captured figures (process/figs/P01..P12.png).
Writes a landscape (4 x 3) and a portrait (3 x 4) sheet as PNG, and the landscape sheet as PDF.
Text is kept to the step number, a short title and the tool on the gantry.

usage: python3 process_storyboard.py [PROCESS_DIR]"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from process_figs import FIGS, STORYBOARD  # noqa: E402

PROC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'process'
FD = '/usr/share/fonts/truetype/nanum/'
F_B = lambda s: ImageFont.truetype(FD + 'NanumBarunGothicBold.ttf', s)  # noqa: E731
F_R = lambda s: ImageFont.truetype(FD + 'NanumBarunGothic.ttf', s)  # noqa: E731
INK, MUTED, LINE, CHIP = (27, 32, 35), (104, 112, 118), (213, 218, 221), (236, 240, 242)
TOOLTXT = {'01': '01 (외형)', '02': '02', '03': '03', '-': ''}
BY_ID = {f['id']: f for f in FIGS}


def sheet(cols, rows, out_png, out_pdf=None):
    iw, ih = 900, 563
    m, gx, gy, lab, head = 64, 36, 34, 74, 138
    W = 2 * m + cols * iw + (cols - 1) * gx
    H = m + head + rows * (ih + lab) + (rows - 1) * gy + m // 2
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    d.text((m, m - 6), 'CTP 폐배터리 해체 공정 순서', font=F_B(46), fill=INK)
    d.text((m, m + 58), 'R03 · 시뮬레이션 화면에서 뽑은 그림 · 커버·나사·전장품·냉각수 포트는 가상 형상, 01은 외형만 · 모든 치수와 위치는 가정',
           font=F_R(25), fill=MUTED)
    for k, fid in enumerate(STORYBOARD):
        f = BY_ID[fid]
        c, r = k % cols, k // cols
        x = m + c * (iw + gx)
        y = m + head + r * (ih + lab + gy)
        pic = Image.open(PROC / 'figs' / f'{fid}.png').convert('RGB').resize((iw, ih), Image.LANCZOS)
        im.paste(pic, (x, y))
        d.rectangle((x, y, x + iw - 1, y + ih - 1), outline=LINE, width=2)
        ty = y + ih + 16
        code = f['no']
        d.text((x, ty), code, font=F_B(32), fill=INK)
        cw = d.textlength(code, font=F_B(32))
        d.text((x + cw + 16, ty + 2), f['title'], font=F_R(30), fill=INK)
        tt = TOOLTXT[f['tool']]
        if tt:
            tw = d.textlength(tt, font=F_B(24))
            bx1 = x + iw
            d.rounded_rectangle((bx1 - tw - 28, ty - 1, bx1, ty + 37), radius=8, fill=CHIP)
            d.text((bx1 - tw - 14, ty + 5), tt, font=F_B(24), fill=MUTED)
    im.save(out_png, optimize=True)
    if out_pdf:
        im.save(out_pdf, 'PDF', resolution=300.0)
    return im.size


if __name__ == '__main__':
    out = PROC / 'storyboard'
    out.mkdir(parents=True, exist_ok=True)
    print('landscape', sheet(4, 3, out / 'CTP_R03_process_storyboard_4x3.png', out / 'CTP_R03_process_storyboard_4x3.pdf'))
    print('portrait', sheet(3, 4, out / 'CTP_R03_process_storyboard_3x4.png'))
