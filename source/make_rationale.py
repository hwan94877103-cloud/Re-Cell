"""KS 적용 근거표 (PDF + XLSX) - ks_spec.py의 같은 값으로 만든다 (도면 값과 어긋나지 않게)."""
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

import ks_spec as K

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'drawings' / 'out'
OUT.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont('NG', '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'))
pdfmetrics.registerFont(TTFont('NGB', '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf'))

SHEET = {'공통': 'D-04 전체', '03-001': 'D-04 1/5', '03-007': 'D-04 2/5', '03-010': 'D-04 2/5', '03-004': 'D-04 3/5',
         '03-008': 'D-04 3/5', '03-002': 'D-04 4/5', '03-003': 'D-04 5/5', '03-011': 'D-04 5/5', '미적용': '-'}
STATUS_TXT = {'적용': '적용', '※': '적용 (※ 선정 후 확정)', '가정': '적용 (가정)', '미적용': '적용 안 함'}

CHANGES = [
    ['누름판 볼트 M5×18 → M4×18', 'M5 머리 dk 최대 8.72 (16항) > 누름판 폭 8. M4는 7.22로 판 위에 다 얹힘. '
                                  '바닥 물림 6 = 1.5d로 좋아짐', '노즈 H1·누름판 Ø4.5, 하우징 K1 M4, 볼트 03-201'],
    ['노즐 블록 O링 홈 → P6 평면 홈', 'R03 초기 홈(Ø4/Ø7, 깊이 0.8)은 규격집 36항에 없는 치수. P6 내압용 D 9.2, G 2.5, H 1.4로 맞춤',
     '03-010, O링 03-213 추가'],
    ['IR 클램프 Ø18.2+0.1 → Ø18 H8', '센서 공차에 따라 덜 물릴 수 있음. H8/h8(틈새 0~0.054)이면 조임 여유 0.5 안에서 확실히 물림',
     '03-008·009'],
    ['노즈 IR 구멍 Ø18.4 → Ø19', '클램프가 볼트 여유 안에서 떠 있어 반경 틈 0.2로는 센서가 노즈에 닿을 수 있음',
     '03-001 H3'],
    ['피팅 포트에 보스 Ø11×4 추가', '바닥 6에서 불완전 나사부(17항 a 2.4)를 빼면 완전 나사 2.6 → M5 피팅 나사에 부족', '03-002 K3, 피팅·냉각 호스 4 mm 위로'],
]


def plain(s):
    """Symbols the PDF/Excel fonts lack -> words (the drawings keep the symbols)."""
    s = str(s)
    for a, b in (('⌖ ', '위치도 '), ('⌖', '위치도 '), ('⌴', '카운터보어 '), ('↧', '깊이 '), ('▱ ', '평면도 '),
                 ('// ', '평행도 '), ('⊥ ', '직각도 '), ('->', '→')):
        s = s.replace(a, b)
    return s


def rows_by_group():
    groups = {}
    for r in K.rows():
        groups.setdefault(r[0], []).append(r)
    return groups


def sheet_of(group):
    for k, v in SHEET.items():
        if group.startswith(k):
            return v
    return '-'


def build_pdf(path):
    st = dict(
        h1=ParagraphStyle('h1', fontName='NGB', fontSize=15, leading=19, spaceAfter=2 * mm),
        h2=ParagraphStyle('h2', fontName='NGB', fontSize=11, leading=14, spaceBefore=4 * mm, spaceAfter=2 * mm),
        p=ParagraphStyle('p', fontName='NG', fontSize=8.6, leading=11.5),
        c=ParagraphStyle('c', fontName='NG', fontSize=7.8, leading=10.0),
        cb=ParagraphStyle('cb', fontName='NGB', fontSize=7.8, leading=10.0),
        cc=ParagraphStyle('cc', fontName='NG', fontSize=7.8, leading=10.0, alignment=TA_CENTER),
    )
    esc = lambda s: plain(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    P = lambda s, k='c': Paragraph(esc(s), st[k])
    head_bg = colors.HexColor('#e9edf0')
    grid = colors.HexColor('#9aa3a8')

    def table(data, widths, header_rows=1, zebra=False):
        t = Table(data, colWidths=widths, repeatRows=header_rows)
        sty = [('GRID', (0, 0), (-1, -1), 0.4, grid), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
               ('BACKGROUND', (0, 0), (-1, header_rows - 1), head_bg),
               ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
               ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]
        t.setStyle(TableStyle(sty))
        return t

    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title='KS 적용 근거표 - 03 셀 분리 공구 (R03)',
                            author='CTP 폐배터리 해체 로봇')

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont('NG', 7.5)
        canvas.setFillColor(colors.HexColor('#5a6268'))
        canvas.drawString(14 * mm, 7 * mm, 'CTP 폐배터리 해체 로봇 · D-04 KS 적용 근거표 (R03) · 모든 값은 설계 가정, CAD 계산 대조만 수행 (검증 아님)')
        canvas.drawRightString(landscape(A4)[0] - 14 * mm, 7 * mm, f'{doc_.page}')
        canvas.restoreState()

    W = [44 * mm, 52 * mm, 40 * mm, 110 * mm, 23 * mm]
    story = [Paragraph('KS 적용 근거표 - 03 셀 분리 공구 부품도 (D-04, R03)', st['h1']),
             P('기준 자료: 2025 국가기술자격 CAD 실기시험용 KS 기계제도 규격 (이하 규격집, 항 번호로 인용). 규격집은 시험용 발췌본이며 '
               'KS 원문 대조는 하지 않았다. 도면의 공차·거칠기·끼워맞춤 값과 이 표의 값은 같은 파일(ks_spec.py)에서 나온다.', 'p'),
             P('상태: 적용 = 이번 도면에 넣음 / ※ = 구매품 선정 후 값이 바뀔 수 있음 / 가정 = 재료·처리 같은 설계 가정 / 적용 안 함 = 넣지 않은 이유를 적음. '
               '실물 측정·강도·밀봉·절연 시험은 하지 않았다.', 'p')]

    groups = rows_by_group()
    order = ['공통'] + [g for g in groups if g not in ('공통', '미적용')] + ['미적용']
    titles = {'공통': '1. 공통 기준 (모든 부품)', '미적용': '3. 넣지 않은 것과 이유'}
    first_part = True
    for g in order:
        lead = []
        if g in ('공통', '미적용'):
            story.append(Paragraph(titles[g], st['h2']))
        elif first_part:
            lead = [Paragraph('2. 부품별 지시와 이유', st['h2'])]
            first_part = False
        data = [[P('형체', 'cb'), P('도면 지시', 'cb'), P('규격 근거', 'cb'), P('이유', 'cb'), P('상태', 'cb')]]
        for r in groups[g]:
            data.append([P(r[1]), P(r[2]), P(r[3]), P(r[4]), P(STATUS_TXT.get(r[5], r[5]), 'cc')])
        if g not in ('공통', '미적용'):
            cap = Paragraph(f'{g}  <font name="NG" size="8">({sheet_of(g)})</font>', ParagraphStyle(
                'cap', fontName='NGB', fontSize=9.5, leading=12, spaceBefore=2.5 * mm, spaceAfter=1.2 * mm))
            story.append(KeepTogether(lead + [cap, table(data, W)]))
        else:
            story.append(table(data, W))

    story.append(PageBreak())
    story.append(Paragraph('4. 계산 검사 (CAD·수계산 대조, 검증 아님)', st['h2']))
    data = [[P('항목', 'cb'), P('계산', 'cb'), P('기준', 'cb'), P('결과', 'cb')]]
    for item, calc, crit, ok in K.checks():
        data.append([P(item), P(calc), P(crit), P(ok, 'cc')])
    story.append(table(data, [92 * mm, 78 * mm, 76 * mm, 23 * mm]))
    story.append(Spacer(1, 3 * mm))
    story.append(P('검사 스크립트 verify_drawings.py가 같은 값으로 (1) 도면 DXF 글자에 지시값이 모두 들어 있는지, '
                   '(2) 3D 솔리드의 구멍 지름·위치·깊이가 지시값과 같은지, (3) 위 계산이 기준을 만족하는지를 확인한다.', 'p'))
    data = [[P('변경', 'cb'), P('이유 (규격집 표 대조에서 발견)', 'cb'), P('영향 부품', 'cb')]]
    for a, b, c in CHANGES:
        data.append([P(a), P(b), P(c)])
    story.append(KeepTogether([
        Paragraph('5. 이번 KS 개정으로 바뀐 3D (R03 초기 → R03 KS)', st['h2']),
        table(data, [62 * mm, 140 * mm, 67 * mm]), Spacer(1, 3 * mm),
        P('바뀐 뒤 확인: 솔리드 79개 유효, 정지 상태 겹침 0건, 도면 치수 = 솔리드 치수, 계산 검사 모두 OK. '
          '정비 공구 접근은 바뀌기 전과 같이 21곳 중 1곳 막힘 (냉각 호스 L 분리 후 접근).', 'p')]))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_xlsx(path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    wb = Workbook()
    ws = wb.active
    ws.title = '근거표'
    hdr = ['구분', '도면', '형체', '도면 지시', '규격 근거', '이유', '상태']
    ws.append(hdr)
    for r in K.rows():
        ws.append([plain(x) for x in [r[0], sheet_of(r[0]), r[1], r[2], r[3], r[4], STATUS_TXT.get(r[5], r[5])]])
    ws2 = wb.create_sheet('계산검사')
    ws2.append(['항목', '계산', '기준', '결과'])
    for r in K.checks():
        ws2.append([plain(x) for x in r])
    ws3 = wb.create_sheet('3D 변경')
    ws3.append(['변경', '이유', '영향 부품'])
    for r in CHANGES:
        ws3.append(r)
    thin = Side(style='thin', color='9AA3A8')
    for w, widths in ((ws, [16, 10, 30, 30, 26, 70, 18]), (ws2, [40, 36, 30, 8]), (ws3, [30, 80, 34])):
        for i, wd in enumerate(widths):
            w.column_dimensions[chr(65 + i)].width = wd
        for row in w.iter_rows():
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical='top')
                c.font = Font(name='맑은 고딕', size=10, bold=(c.row == 1))
                c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
                if c.row == 1:
                    c.fill = PatternFill('solid', fgColor='E9EDF0')
        w.freeze_panes = 'A2'
    wb.save(path)


if __name__ == '__main__':
    build_pdf(OUT / 'KS_적용_근거표_D-04_R03.pdf')
    build_xlsx(OUT / 'KS_적용_근거표_D-04_R03.xlsx')
    print('ok', OUT)
