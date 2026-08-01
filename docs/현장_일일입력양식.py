"""현장 담당자별 일일 입력 Excel 양식 생성 스크립트."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation


# 공통 스타일
THIN = Side(border_style="thin", color="000000")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

TITLE_FONT = Font(name="맑은 고딕", size=16, bold=True, color="FFFFFF")
TITLE_FILL = PatternFill("solid", start_color="2F5496")

HEADER_FONT = Font(name="맑은 고딕", size=11, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", start_color="4472C4")

SUBHEADER_FONT = Font(name="맑은 고딕", size=10, bold=True)
SUBHEADER_FILL = PatternFill("solid", start_color="D9E1F2")

INFO_FONT = Font(name="맑은 고딕", size=10)
INFO_FILL = PatternFill("solid", start_color="FFF2CC")

REQUIRED_FILL = PatternFill("solid", start_color="FCE4D6")  # 필수 입력 항목
OPTIONAL_FILL = PatternFill("solid", start_color="E2EFDA")  # 선택 입력
EXAMPLE_FILL = PatternFill("solid", start_color="F2F2F2")  # 예시

CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)


def style_title(cell):
    cell.font = TITLE_FONT
    cell.fill = TITLE_FILL
    cell.alignment = CENTER
    cell.border = BORDER


def style_header(cell):
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = CENTER
    cell.border = BORDER


def style_subheader(cell):
    cell.font = SUBHEADER_FONT
    cell.fill = SUBHEADER_FILL
    cell.alignment = CENTER
    cell.border = BORDER


def style_cell(cell, fill=None, align=None):
    cell.font = INFO_FONT
    cell.alignment = align or LEFT
    cell.border = BORDER
    if fill:
        cell.fill = fill


def add_legend(ws, row, col=1):
    """범례 추가"""
    legend = [
        ("■", REQUIRED_FILL, "필수 입력"),
        ("■", OPTIONAL_FILL, "선택 입력"),
        ("■", EXAMPLE_FILL, "예시 / 자동계산"),
    ]
    for i, (mark, fill, text) in enumerate(legend):
        c = ws.cell(row=row, column=col + i * 3, value=mark)
        c.fill = fill
        c.alignment = CENTER
        c.border = BORDER
        ws.cell(row=row, column=col + i * 3 + 1, value=text).font = INFO_FONT


wb = Workbook()


# ============================================================
# Sheet 0: 표지/사용 안내
# ============================================================
ws = wb.active
ws.title = "📋 사용안내"

ws.merge_cells("B2:G3")
c = ws["B2"]
c.value = "현장 담당자별 일일 입력 양식"
style_title(c)

ws["B5"] = "프로젝트명"
ws["C5"] = "홍은동 355번지 가로주택정비사업"
ws["B6"] = "현장주소"
ws["C6"] = "서울시 서대문구 홍은동 355"
ws["B7"] = "작성일"
ws["C7"] = "2028-06-15 (목)"
ws["B8"] = "공사기간"
ws["C8"] = "2028-01-01 ~ 2029-06-30 (18개월)"

for r in range(5, 9):
    style_subheader(ws.cell(row=r, column=2))
    style_cell(ws.cell(row=r, column=3))

ws.merge_cells("B10:G10")
c = ws["B10"]
c.value = "📑 시트 구성"
style_header(c)

sheets_info = [
    ("1. 건축담당 일보", "건축공종 시공 실적, 인원/장비, 작업위치, 안전사고", "매일 18:00"),
    ("2. 설비담당 일보", "기계/전기/소방 설비 시공 실적, 자재 사용량", "매일 18:00"),
    ("3. 자재담당 일보", "당일 입출고, 재고 현황, 발주 요청", "매일 17:00"),
    ("4. 안전담당 일보", "TBM, 위험요인, 사고, 보호구 점검, 교육", "매일 09:00/17:00"),
    ("5. 품질담당 일보", "검측 요청/결과, 콘크리트 타설, 시험성적", "매일 18:00"),
    ("6. 종합 (소장확인)", "전체 요약 + 결재란", "매일 19:00"),
]

ws["B11"] = "시트명"
ws["C11"] = "입력 내용"
ws["E11"] = "마감시간"
ws.merge_cells("C11:D11")
ws.merge_cells("E11:G11")
for col in (2, 3, 5):
    style_subheader(ws.cell(row=11, column=col))

for i, (name, desc, time) in enumerate(sheets_info, start=12):
    ws.cell(row=i, column=2, value=name)
    ws.merge_cells(start_row=i, start_column=3, end_row=i, end_column=4)
    ws.cell(row=i, column=3, value=desc)
    ws.merge_cells(start_row=i, start_column=5, end_row=i, end_column=7)
    ws.cell(row=i, column=5, value=time)
    for col in (2, 3, 5):
        style_cell(ws.cell(row=i, column=col))

ws.merge_cells("B19:G19")
c = ws["B19"]
c.value = "✏️ 입력 규칙"
style_header(c)

rules = [
    "1. 필수 입력 항목(주황)은 반드시 작성 후 저장",
    "2. 선택 입력(연두)은 해당사항 있을 때만 작성",
    "3. 회색 셀은 예시 또는 자동계산 - 직접 수정 금지",
    "4. 날짜 형식: YYYY-MM-DD (예: 2028-06-15)",
    "5. 시간 형식: HH:MM 24시간제 (예: 17:30)",
    "6. 인원/물량은 숫자만 입력 (단위는 헤더 참조)",
    "7. 특이사항/메모는 간결하게 작성 (50자 이내 권장)",
    "8. 모바일 입력은 빨강 별표(*) 필드만 입력 가능",
]
for i, rule in enumerate(rules, start=20):
    ws.merge_cells(start_row=i, start_column=2, end_row=i, end_column=7)
    c = ws.cell(row=i, column=2, value=rule)
    style_cell(c)

ws.column_dimensions["A"].width = 2
ws.column_dimensions["B"].width = 22
ws.column_dimensions["C"].width = 28
ws.column_dimensions["D"].width = 18
ws.column_dimensions["E"].width = 12
ws.column_dimensions["F"].width = 12
ws.column_dimensions["G"].width = 12

# 범례 추가
add_legend(ws, 30)


# ============================================================
# Sheet 1: 건축담당 일보
# ============================================================
ws = wb.create_sheet("1.건축담당")

ws.merge_cells("A1:N1")
c = ws["A1"]
c.value = "건축담당 일일 작업일보"
style_title(c)

# 기본정보
ws["A3"] = "작성자"
ws["B3"] = "건축팀 박과장"
ws["D3"] = "작성일자"
ws["E3"] = "2028-06-15"
ws["G3"] = "날씨(오전)"
ws["H3"] = "맑음"
ws["J3"] = "날씨(오후)"
ws["K3"] = "흐림"
ws["M3"] = "기온"
ws["N3"] = "28°C"

for col in (1, 4, 7, 10, 13):
    style_subheader(ws.cell(row=3, column=col))
for col in (2, 5, 8, 11, 14):
    style_cell(ws.cell(row=3, column=col), REQUIRED_FILL)

# 섹션 1: 공종별 시공실적
ws.merge_cells("A5:N5")
c = ws["A5"]
c.value = "① 공종별 시공 실적"
style_header(c)

headers1 = [
    ("공종/작업명", 18),  # A
    ("작업위치", 14),     # B
    ("협력업체", 14),     # C
    ("계획물량", 9),      # D
    ("실적물량", 9),      # E
    ("단위", 6),          # F
    ("달성률(%)", 9),     # G
    ("목수", 6),          # H
    ("철근", 6),          # I
    ("형틀", 6),          # J
    ("잡부", 6),          # K
    ("총인원", 7),        # L
    ("작업시간(h)", 9),   # M
    ("특이사항", 22),     # N
]
for i, (h, w) in enumerate(headers1, start=1):
    c = ws.cell(row=6, column=i, value=h)
    style_header(c)
    ws.column_dimensions[get_column_letter(i)].width = w

# 예시 + 입력행
example_arch = [
    ["골조공사(지하)", "B2층 3~5축", "(주)대한건설", 100, 95, "㎡", None, 6, 5, 4, 3, None, 7.0, "벽체 타설 완료"],
    ["골조공사(지상)", "1층 1~3축", "(주)대한건설", 80, 60, "㎡", None, 4, 4, 2, 2, None, 7.5, "기둥 배근 진행중"],
]
for ri, row in enumerate(example_arch, start=7):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        if ci in (7, 12):  # 달성률, 총인원 자동계산
            style_cell(c, EXAMPLE_FILL, CENTER)
        else:
            style_cell(c, REQUIRED_FILL, CENTER if ci != 14 else LEFT)
    # 달성률 = 실적/계획
    ws.cell(row=ri, column=7).value = f"=IF(D{ri}=0,0,E{ri}/D{ri}*100)"
    ws.cell(row=ri, column=7).number_format = "0.0"
    # 총인원 = 목수+철근+형틀+잡부
    ws.cell(row=ri, column=12).value = f"=SUM(H{ri}:K{ri})"

# 빈 입력 행 8줄
for ri in range(9, 17):
    for ci in range(1, 15):
        c = ws.cell(row=ri, column=ci)
        if ci in (7, 12):
            style_cell(c, EXAMPLE_FILL, CENTER)
        else:
            style_cell(c, REQUIRED_FILL, CENTER if ci != 14 else LEFT)
    ws.cell(row=ri, column=7).value = f"=IF(D{ri}=0,0,E{ri}/D{ri}*100)"
    ws.cell(row=ri, column=7).number_format = "0.0"
    ws.cell(row=ri, column=12).value = f"=SUM(H{ri}:K{ri})"

# 합계 행
ws.cell(row=17, column=1, value="합계").font = Font(name="맑은 고딕", bold=True)
ws.cell(row=17, column=1).fill = SUBHEADER_FILL
ws.cell(row=17, column=1).alignment = CENTER
ws.cell(row=17, column=1).border = BORDER
for col_letter, col_idx in [("D", 4), ("E", 5), ("H", 8), ("I", 9), ("J", 10), ("K", 11), ("L", 12)]:
    c = ws.cell(row=17, column=col_idx, value=f"=SUM({col_letter}7:{col_letter}16)")
    c.font = Font(name="맑은 고딕", bold=True)
    c.fill = SUBHEADER_FILL
    c.alignment = CENTER
    c.border = BORDER

# 섹션 2: 장비 가동
ws.merge_cells("A19:N19")
c = ws["A19"]
c.value = "② 장비 가동 실적"
style_header(c)

eq_headers = [("장비명", 14), ("가동시간(h)", 11), ("가동률(%)", 10),
              ("연료(L)", 9), ("정비/고장", 22), ("운전원", 12)]
for i, (h, w) in enumerate(eq_headers, start=1):
    c = ws.cell(row=20, column=i, value=h)
    style_header(c)

example_eq = [
    ["타워크레인 1호", 7.5, None, None, "이상없음", "김기사"],
    ["콘크리트펌프카", 4.0, None, 65, "이상없음", "외주"],
]
for ri, row in enumerate(example_eq, start=21):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        if ci == 3:
            style_cell(c, EXAMPLE_FILL, CENTER)
        else:
            style_cell(c, OPTIONAL_FILL, CENTER if ci != 5 else LEFT)
    ws.cell(row=ri, column=3).value = f"=B{ri}/8*100"
    ws.cell(row=ri, column=3).number_format = "0.0"

for ri in range(23, 27):
    for ci in range(1, 7):
        c = ws.cell(row=ri, column=ci)
        if ci == 3:
            style_cell(c, EXAMPLE_FILL, CENTER)
        else:
            style_cell(c, OPTIONAL_FILL, CENTER if ci != 5 else LEFT)
    ws.cell(row=ri, column=3).value = f"=IF(B{ri}=0,0,B{ri}/8*100)"
    ws.cell(row=ri, column=3).number_format = "0.0"

# 섹션 3: 안전 / 내일 계획
ws.merge_cells("A28:N28")
c = ws["A28"]
c.value = "③ 안전 · 내일 계획"
style_header(c)

ws["A29"] = "안전사고 여부"
ws.merge_cells("B29:D29")
ws["B29"] = "이상없음"
ws["E29"] = "TBM 실시"
ws.merge_cells("F29:G29")
ws["F29"] = "07:30 실시"
ws["H29"] = "위험요인"
ws.merge_cells("I29:N29")
ws["I29"] = "개구부 덮개 미설치 발견 → 즉시 조치 완료"

ws.merge_cells("A30:A31")
ws["A30"] = "내일 계획"
ws.merge_cells("B30:N30")
ws["B30"] = "1층 1~3축 기둥 배근 마무리 + 4~5축 거푸집"
ws.merge_cells("B31:N31")
ws["B31"] = "지상 타설 협의 필요 (기상 상태 따라)"

for col in (1, 5, 8):
    style_subheader(ws.cell(row=29, column=col))
style_subheader(ws.cell(row=30, column=1))
for cell_ref in ("B29", "F29", "I29", "B30", "B31"):
    style_cell(ws[cell_ref], REQUIRED_FILL)

# 결재란
ws.merge_cells("A33:C33")
ws["A33"] = "작성자"
style_subheader(ws["A33"])
ws.merge_cells("D33:F33")
ws["D33"] = "공무팀장"
style_subheader(ws["D33"])
ws.merge_cells("G33:I33")
ws["G33"] = "공사부장"
style_subheader(ws["G33"])
ws.merge_cells("J33:N33")
ws["J33"] = "현장소장"
style_subheader(ws["J33"])

ws.merge_cells("A34:C36")
ws.merge_cells("D34:F36")
ws.merge_cells("G34:I36")
ws.merge_cells("J34:N36")
for cell_ref in ("A34", "D34", "G34", "J34"):
    style_cell(ws[cell_ref])

# 데이터 검증: 날씨
dv_weather = DataValidation(type="list", formula1='"맑음,흐림,비,눈,안개,바람"', allow_blank=True)
ws.add_data_validation(dv_weather)
dv_weather.add("H3")
dv_weather.add("K3")

dv_safety = DataValidation(type="list", formula1='"이상없음,경미,중경상,중대재해"', allow_blank=True)
ws.add_data_validation(dv_safety)
dv_safety.add("B29")

ws.row_dimensions[6].height = 30
ws.freeze_panes = "A7"


# ============================================================
# Sheet 2: 설비담당 일보 (기계/전기/소방)
# ============================================================
ws = wb.create_sheet("2.설비담당")

ws.merge_cells("A1:M1")
c = ws["A1"]
c.value = "설비담당 일일 작업일보 (기계/전기/소방)"
style_title(c)

ws["A3"] = "작성자"
ws["B3"] = "기계팀 이대리"
ws["D3"] = "작성일자"
ws["E3"] = "2028-06-15"
ws["G3"] = "공종 구분"
ws["H3"] = "기계설비"
ws["J3"] = "날씨"
ws["K3"] = "맑음"
ws["L3"] = "특이"
ws["M3"] = "없음"

for col in (1, 4, 7, 10, 12):
    style_subheader(ws.cell(row=3, column=col))
for col in (2, 5, 8, 11, 13):
    style_cell(ws.cell(row=3, column=col), REQUIRED_FILL)

# 시공실적
ws.merge_cells("A5:M5")
c = ws["A5"]
c.value = "① 설비 시공 실적"
style_header(c)

mech_headers = [
    ("작업명", 18), ("작업위치", 14), ("협력업체", 14),
    ("계획물량", 9), ("실적물량", 9), ("단위", 6), ("달성률(%)", 9),
    ("기술자", 7), ("기능공", 7), ("보조", 7), ("총인원", 7),
    ("자재사용량", 11), ("특이사항", 20),
]
for i, (h, w) in enumerate(mech_headers, start=1):
    c = ws.cell(row=6, column=i, value=h)
    style_header(c)
    ws.column_dimensions[get_column_letter(i)].width = w

example_mech = [
    ["기계설비 슬리브", "B1층 천장", "(주)한국설비", 50, 42, "EA", None, 1, 2, 1, None, "STS 25Φ 12m", "정상"],
    ["위생배관 입상", "1~3층 PD", "(주)한국설비", 60, 25, "m", None, 1, 1, 1, None, "STS 50Φ 8m", "자재 일부 부족"],
]
for ri, row in enumerate(example_mech, start=7):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        if ci in (7, 11):
            style_cell(c, EXAMPLE_FILL, CENTER)
        else:
            style_cell(c, REQUIRED_FILL, CENTER if ci != 13 else LEFT)
    ws.cell(row=ri, column=7).value = f"=IF(D{ri}=0,0,E{ri}/D{ri}*100)"
    ws.cell(row=ri, column=7).number_format = "0.0"
    ws.cell(row=ri, column=11).value = f"=SUM(H{ri}:J{ri})"

for ri in range(9, 17):
    for ci in range(1, 14):
        c = ws.cell(row=ri, column=ci)
        if ci in (7, 11):
            style_cell(c, EXAMPLE_FILL, CENTER)
        else:
            style_cell(c, REQUIRED_FILL, CENTER if ci != 13 else LEFT)
    ws.cell(row=ri, column=7).value = f"=IF(D{ri}=0,0,E{ri}/D{ri}*100)"
    ws.cell(row=ri, column=7).number_format = "0.0"
    ws.cell(row=ri, column=11).value = f"=SUM(H{ri}:J{ri})"

# 합계
ws.cell(row=17, column=1, value="합계").font = Font(name="맑은 고딕", bold=True)
ws.cell(row=17, column=1).fill = SUBHEADER_FILL
ws.cell(row=17, column=1).alignment = CENTER
ws.cell(row=17, column=1).border = BORDER
for col_letter, col_idx in [("D", 4), ("E", 5), ("H", 8), ("I", 9), ("J", 10), ("K", 11)]:
    c = ws.cell(row=17, column=col_idx, value=f"=SUM({col_letter}7:{col_letter}16)")
    c.font = Font(name="맑은 고딕", bold=True)
    c.fill = SUBHEADER_FILL
    c.alignment = CENTER
    c.border = BORDER

# 시운전/검사
ws.merge_cells("A19:M19")
c = ws["A19"]
c.value = "② 시운전 · 시험 · 검사 (해당시)"
style_header(c)

test_headers = [("종류", 16), ("위치", 14), ("기준값", 12), ("측정값", 12),
                ("판정", 10), ("입회자", 14)]
for i, (h, w) in enumerate(test_headers, start=1):
    c = ws.cell(row=20, column=i, value=h)
    style_header(c)

for ri in range(21, 25):
    for ci in range(1, 7):
        c = ws.cell(row=ri, column=ci)
        style_cell(c, OPTIONAL_FILL, CENTER)

# 안전/내일 계획
ws.merge_cells("A26:M26")
c = ws["A26"]
c.value = "③ 안전 · 내일 계획"
style_header(c)

ws["A27"] = "안전사고"
ws.merge_cells("B27:D27")
ws["B27"] = "이상없음"
ws["E27"] = "TBM"
ws.merge_cells("F27:G27")
ws["F27"] = "07:30 실시"
ws["H27"] = "보호구"
ws.merge_cells("I27:M27")
ws["I27"] = "안전모/안전대/안전화 100% 착용 확인"

ws.merge_cells("A28:A29")
ws["A28"] = "내일 계획"
ws.merge_cells("B28:M28")
ws["B28"] = "B1층 슬리브 작업 마무리, 위생배관 PD 입상 50Φ 진행"
ws.merge_cells("B29:M29")
ws["B29"] = "자재 STS 50Φ 추가 발주 협조 요청"

for col in (1, 5, 8):
    style_subheader(ws.cell(row=27, column=col))
style_subheader(ws.cell(row=28, column=1))
for cell_ref in ("B27", "F27", "I27", "B28", "B29"):
    style_cell(ws[cell_ref], REQUIRED_FILL)

dv_disc = DataValidation(
    type="list",
    formula1='"기계설비,전기설비,소방설비,통신,자동제어,위생,공조"',
    allow_blank=False,
)
ws.add_data_validation(dv_disc)
dv_disc.add("H3")

dv_pass = DataValidation(type="list", formula1='"합격,불합격,재시험"', allow_blank=True)
ws.add_data_validation(dv_pass)
for r in range(21, 25):
    dv_pass.add(f"E{r}")

ws.row_dimensions[6].height = 30
ws.freeze_panes = "A7"


# ============================================================
# Sheet 3: 자재담당 일보
# ============================================================
ws = wb.create_sheet("3.자재담당")

ws.merge_cells("A1:L1")
c = ws["A1"]
c.value = "자재담당 일일 입출고 일보"
style_title(c)

ws["A3"] = "작성자"
ws["B3"] = "자재팀 최주임"
ws["D3"] = "작성일자"
ws["E3"] = "2028-06-15"
ws["G3"] = "결재"
ws["H3"] = "공무팀장"
ws["J3"] = "검측감리"
ws["K3"] = "필요시"

for col in (1, 4, 7, 10):
    style_subheader(ws.cell(row=3, column=col))
for col in (2, 5, 8, 11):
    style_cell(ws.cell(row=3, column=col), REQUIRED_FILL)

# 섹션 1: 입고
ws.merge_cells("A5:L5")
c = ws["A5"]
c.value = "① 당일 입고 자재"
style_header(c)

in_headers = [
    ("자재명/규격", 22), ("발주번호", 12), ("입고시간", 10),
    ("계획수량", 10), ("입고수량", 10), ("단위", 6),
    ("납품업체", 16), ("차량번호", 11), ("검수결과", 10),
    ("불량수량", 9), ("보관위치", 12), ("비고", 18),
]
for i, (h, w) in enumerate(in_headers, start=1):
    c = ws.cell(row=6, column=i, value=h)
    style_header(c)
    ws.column_dimensions[get_column_letter(i)].width = w

example_in = [
    ["레미콘 25-24-15", "PO-2806-01", "09:30", 25, 25, "㎥",
     "삼표레미콘", "서울 56가 5601", "합격", 0, "현장반입", "B2층 타설용"],
    ["철근 HD16", "PO-2806-02", "14:00", 3.0, 2.5, "ton",
     "동부제철", "서울 79바 8821", "합격", 0, "야적장 B", "부족분 재발주 필요"],
]
for ri, row in enumerate(example_in, start=7):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        style_cell(c, REQUIRED_FILL, CENTER if ci != 12 else LEFT)

for ri in range(9, 17):
    for ci in range(1, 13):
        c = ws.cell(row=ri, column=ci)
        style_cell(c, REQUIRED_FILL, CENTER if ci != 12 else LEFT)

# 섹션 2: 출고/사용
ws.merge_cells("A18:L18")
c = ws["A18"]
c.value = "② 당일 출고 / 사용 자재"
style_header(c)

out_headers = [
    ("자재명/규격", 22), ("요청부서", 12), ("출고시간", 10),
    ("출고수량", 10), ("단위", 6), ("사용 공종", 18),
    ("작업위치", 14), ("불출자", 10), ("수령자", 10),
    ("반품수량", 9), ("잔여재고", 10), ("비고", 18),
]
for i, (h, w) in enumerate(out_headers, start=1):
    c = ws.cell(row=19, column=i, value=h)
    style_header(c)

for ri in range(20, 28):
    for ci in range(1, 13):
        c = ws.cell(row=ri, column=ci)
        style_cell(c, REQUIRED_FILL, CENTER if ci != 12 else LEFT)

# 섹션 3: 재고 현황
ws.merge_cells("A29:L29")
c = ws["A29"]
c.value = "③ 주요 자재 재고 현황 (마감 기준)"
style_header(c)

stock_headers = [
    ("자재명/규격", 22), ("재고수량", 10), ("단위", 6),
    ("최소재고", 10), ("부족여부", 10), ("발주필요량", 10),
    ("보관위치", 12), ("입고예정일", 12), ("발주처", 16),
    ("상태", 10), ("담당자", 10), ("비고", 18),
]
for i, (h, w) in enumerate(stock_headers, start=1):
    c = ws.cell(row=30, column=i, value=h)
    style_header(c)

example_stock = [
    ["철근 HD16", 0.5, "ton", 2.0, None, None, "야적장 B", "2028-06-17", "동부제철", "부족", "최주임", "긴급발주"],
    ["레미콘 25-24-15", 0, "㎥", 0, None, None, "현장반입", "2028-06-16", "삼표레미콘", "당일발주", "최주임", ""],
]
for ri, row in enumerate(example_stock, start=31):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        if ci in (5, 6):
            style_cell(c, EXAMPLE_FILL, CENTER)
        else:
            style_cell(c, OPTIONAL_FILL, CENTER if ci != 12 else LEFT)
    ws.cell(row=ri, column=5).value = f'=IF(B{ri}<D{ri},"부족","정상")'
    ws.cell(row=ri, column=6).value = f"=MAX(0,D{ri}-B{ri})"

for ri in range(33, 41):
    for ci in range(1, 13):
        c = ws.cell(row=ri, column=ci)
        if ci in (5, 6):
            style_cell(c, EXAMPLE_FILL, CENTER)
        else:
            style_cell(c, OPTIONAL_FILL, CENTER if ci != 12 else LEFT)
    ws.cell(row=ri, column=5).value = f'=IF(B{ri}="","",IF(B{ri}<D{ri},"부족","정상"))'
    ws.cell(row=ri, column=6).value = f'=IF(B{ri}="","",MAX(0,D{ri}-B{ri}))'

dv_pass2 = DataValidation(type="list", formula1='"합격,불합격,일부불합격,재검사"', allow_blank=True)
ws.add_data_validation(dv_pass2)
for r in range(7, 17):
    dv_pass2.add(f"I{r}")

dv_stat = DataValidation(type="list", formula1='"정상,부족,긴급발주,당일발주,입고예정,단종"', allow_blank=True)
ws.add_data_validation(dv_stat)
for r in range(31, 41):
    dv_stat.add(f"J{r}")

ws.row_dimensions[6].height = 30
ws.row_dimensions[19].height = 30
ws.row_dimensions[30].height = 30
ws.freeze_panes = "A7"


# ============================================================
# Sheet 4: 안전담당 일보
# ============================================================
ws = wb.create_sheet("4.안전담당")

ws.merge_cells("A1:K1")
c = ws["A1"]
c.value = "안전담당 일일 안전관리 일지"
style_title(c)

ws["A3"] = "작성자"
ws["B3"] = "안전팀 정과장"
ws["D3"] = "작성일자"
ws["E3"] = "2028-06-15"
ws["G3"] = "재해등급"
ws["H3"] = "무재해"
ws["J3"] = "무재해일수"
ws["K3"] = 47

for col in (1, 4, 7, 10):
    style_subheader(ws.cell(row=3, column=col))
for col in (2, 5, 8, 11):
    style_cell(ws.cell(row=3, column=col), REQUIRED_FILL)

# 섹션 1: TBM / 안전조회
ws.merge_cells("A5:K5")
c = ws["A5"]
c.value = "① TBM (Tool Box Meeting) / 안전조회"
style_header(c)

tbm_headers = [
    ("시간", 10), ("공종", 14), ("협력업체", 16),
    ("참석인원", 9), ("주제", 24), ("위험요인 공유", 24),
    ("주관자", 10),
]
for i, (h, w) in enumerate(tbm_headers, start=1):
    c = ws.cell(row=6, column=i, value=h)
    style_header(c)
    ws.column_dimensions[get_column_letter(i)].width = w
# 나머지 컬럼 폭
for col_letter, w in [("H", 10), ("I", 10), ("J", 10), ("K", 16)]:
    ws.column_dimensions[col_letter].width = w

example_tbm = [
    ["07:30", "건축", "(주)대한건설", 18, "고소작업 안전수칙", "개구부 덮개 점검 강조", "정과장"],
    ["07:30", "기계설비", "(주)한국설비", 5, "용접작업 화재 예방", "소화기 비치 확인", "이대리"],
]
for ri, row in enumerate(example_tbm, start=7):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        style_cell(c, REQUIRED_FILL, CENTER if ci not in (5, 6) else LEFT)

for ri in range(9, 13):
    for ci in range(1, 8):
        c = ws.cell(row=ri, column=ci)
        style_cell(c, REQUIRED_FILL, CENTER if ci not in (5, 6) else LEFT)

# 섹션 2: 위험요인 점검
ws.merge_cells("A14:K14")
c = ws["A14"]
c.value = "② 위험요인 점검 / 시정조치"
style_header(c)

risk_headers = [
    ("시간", 10), ("위치", 14), ("위험요인", 24),
    ("위험등급", 10), ("조치내용", 24), ("조치시간", 10),
    ("확인자", 10),
]
for i, (h, w) in enumerate(risk_headers, start=1):
    c = ws.cell(row=15, column=i, value=h)
    style_header(c)

example_risk = [
    ["09:00", "B2층 슬래브", "개구부 덮개 미설치 (3개소)", "상", "즉시 합판 덮개 설치 + 안전테이프", "09:30", "박과장"],
    ["14:00", "1층 거푸집", "안전난간 일부 파손", "중", "교체 작업 지시 (당일 완료)", "16:00", "박과장"],
]
for ri, row in enumerate(example_risk, start=16):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        style_cell(c, REQUIRED_FILL, CENTER if ci not in (3, 5) else LEFT)

for ri in range(18, 23):
    for ci in range(1, 8):
        c = ws.cell(row=ri, column=ci)
        style_cell(c, REQUIRED_FILL, CENTER if ci not in (3, 5) else LEFT)

# 섹션 3: 보호구 / 안전시설
ws.merge_cells("A24:K24")
c = ws["A24"]
c.value = "③ 보호구 착용 / 안전시설 점검"
style_header(c)

ppe_headers = [
    ("구분", 14), ("점검대상", 12), ("점검수량", 10),
    ("이상수량", 10), ("착용률(%)", 11), ("조치사항", 24),
]
for i, (h, w) in enumerate(ppe_headers, start=1):
    c = ws.cell(row=25, column=i, value=h)
    style_header(c)

example_ppe = [
    ["보호구", "안전모", 47, 0, None, "전원 착용 확인"],
    ["보호구", "안전대(고소)", 12, 1, None, "1명 미착용 시정"],
    ["보호구", "안전화", 47, 0, None, "전원 착용"],
    ["시설", "추락방지망", 5, 0, None, "정상"],
    ["시설", "개구부 덮개", 23, 3, None, "3개소 덮개 설치"],
    ["시설", "안전난간", 18, 1, None, "1개소 교체"],
]
for ri, row in enumerate(example_ppe, start=26):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        if ci == 5:
            style_cell(c, EXAMPLE_FILL, CENTER)
        else:
            style_cell(c, REQUIRED_FILL, CENTER if ci != 6 else LEFT)
    ws.cell(row=ri, column=5).value = f'=IF(C{ri}=0,0,(C{ri}-D{ri})/C{ri}*100)'
    ws.cell(row=ri, column=5).number_format = "0.0"

# 섹션 4: 안전교육
ws.merge_cells("A33:K33")
c = ws["A33"]
c.value = "④ 안전교육 실시 (해당시)"
style_header(c)

edu_headers = [
    ("교육종류", 16), ("대상", 14), ("인원", 8),
    ("시간", 10), ("강사", 12), ("교육내용", 28), ("자료", 10),
]
for i, (h, w) in enumerate(edu_headers, start=1):
    c = ws.cell(row=34, column=i, value=h)
    style_header(c)

example_edu = [
    ["신규채용교육", "신규입장자", 2, "1.0h", "정과장", "현장규칙, 위험요인, 비상연락망", "교재 1식"],
]
for ri, row in enumerate(example_edu, start=35):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        style_cell(c, OPTIONAL_FILL, CENTER if ci != 6 else LEFT)

for ri in range(36, 40):
    for ci in range(1, 8):
        c = ws.cell(row=ri, column=ci)
        style_cell(c, OPTIONAL_FILL, CENTER if ci != 6 else LEFT)

# 섹션 5: 사고 발생시
ws.merge_cells("A41:K41")
c = ws["A41"]
c.value = "⑤ 사고 발생 시 보고 (해당시)"
style_header(c)

acc_labels = [
    ("발생시간", "B42"), ("발생장소", "E42"), ("재해종류", "H42"),
    ("재해자", "B43"), ("소속", "E43"), ("상해정도", "H43"),
    ("사고경위", "B44"), ("조치사항", "B45"), ("재발방지", "B46"),
]
for label, ref in acc_labels:
    row = int(ref[1:])
    ws.cell(row=row, column=1, value="").border = BORDER
    # label cell
    if ref.startswith("B") and label in ("사고경위", "조치사항", "재발방지"):
        ws.cell(row=row, column=1, value=label)
        style_subheader(ws.cell(row=row, column=1))
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=11)
        style_cell(ws.cell(row=row, column=2), OPTIONAL_FILL)
    else:
        col = "ADG".index(ref[0]) if ref[0] in "ADG" else 0
        # 라벨/값 쌍 처리
        if ref == "B42":
            ws["A42"] = "발생시간"; style_subheader(ws["A42"])
            style_cell(ws["B42"], OPTIONAL_FILL)
            ws["D42"] = "발생장소"; style_subheader(ws["D42"])
            ws.merge_cells("E42:G42"); style_cell(ws["E42"], OPTIONAL_FILL)
            ws["H42"] = "재해종류"; style_subheader(ws["H42"])
            ws.merge_cells("I42:K42"); style_cell(ws["I42"], OPTIONAL_FILL)
        elif ref == "B43":
            ws["A43"] = "재해자"; style_subheader(ws["A43"])
            style_cell(ws["B43"], OPTIONAL_FILL)
            ws["D43"] = "소속"; style_subheader(ws["D43"])
            ws.merge_cells("E43:G43"); style_cell(ws["E43"], OPTIONAL_FILL)
            ws["H43"] = "상해정도"; style_subheader(ws["H43"])
            ws.merge_cells("I43:K43"); style_cell(ws["I43"], OPTIONAL_FILL)

dv_grade = DataValidation(type="list", formula1='"상,중,하"', allow_blank=True)
ws.add_data_validation(dv_grade)
for r in range(16, 23):
    dv_grade.add(f"D{r}")

dv_acc = DataValidation(
    type="list",
    formula1='"무재해,경상(1일이상),중경상(3일이상),중상(8일이상),중대재해,사망"',
    allow_blank=True,
)
ws.add_data_validation(dv_acc)
dv_acc.add("H3")

ws.row_dimensions[6].height = 30
ws.row_dimensions[15].height = 30
ws.row_dimensions[25].height = 30
ws.row_dimensions[34].height = 30
ws.freeze_panes = "A7"


# ============================================================
# Sheet 5: 품질담당 일보
# ============================================================
ws = wb.create_sheet("5.품질담당")

ws.merge_cells("A1:K1")
c = ws["A1"]
c.value = "품질담당 일일 품질관리 일지"
style_title(c)

ws["A3"] = "작성자"
ws["B3"] = "품질팀 송과장"
ws["D3"] = "작성일자"
ws["E3"] = "2028-06-15"
ws["G3"] = "감리"
ws["H3"] = "홍팀장"
ws["J3"] = "공사부장"
ws["K3"] = "박부장"

for col in (1, 4, 7, 10):
    style_subheader(ws.cell(row=3, column=col))
for col in (2, 5, 8, 11):
    style_cell(ws.cell(row=3, column=col), REQUIRED_FILL)

# 섹션 1: 검측
ws.merge_cells("A5:K5")
c = ws["A5"]
c.value = "① 검측 요청 / 결과"
style_header(c)

insp_headers = [
    ("검측번호", 11), ("공종", 14), ("검측종류", 16), ("위치", 14),
    ("요청시간", 10), ("실시시간", 10), ("검측자", 10),
    ("판정", 10), ("불량건수", 9), ("조치", 18), ("비고", 16),
]
for i, (h, w) in enumerate(insp_headers, start=1):
    c = ws.cell(row=6, column=i, value=h)
    style_header(c)
    ws.column_dimensions[get_column_letter(i)].width = w

example_insp = [
    ["I-280615-01", "건축", "지하 골조 콘크리트 타설검사", "B2층 3~5축",
     "08:30", "09:00", "홍팀장", "합격", 0, "정상", ""],
    ["I-280615-02", "기계설비", "슬리브 설치검사", "B1층 천장",
     "10:00", "10:30", "박부장", "재검측", 2, "위치 재조정", "16:00 재검 예정"],
]
for ri, row in enumerate(example_insp, start=7):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        style_cell(c, REQUIRED_FILL, CENTER if ci not in (10, 11) else LEFT)

for ri in range(9, 15):
    for ci in range(1, 12):
        c = ws.cell(row=ri, column=ci)
        style_cell(c, REQUIRED_FILL, CENTER if ci not in (10, 11) else LEFT)

# 섹션 2: 콘크리트 타설 기록
ws.merge_cells("A16:K16")
c = ws["A16"]
c.value = "② 콘크리트 타설 기록 (해당시)"
style_header(c)

conc_headers = [
    ("타설번호", 12), ("위치", 14), ("배합강도", 11), ("슬럼프(cm)", 11),
    ("물량(㎥)", 10), ("타설 시작", 11), ("타설 완료", 11),
    ("타설 인원", 9), ("양생 시작", 11), ("탈형 예정", 11), ("비고", 16),
]
for i, (h, w) in enumerate(conc_headers, start=1):
    c = ws.cell(row=17, column=i, value=h)
    style_header(c)

example_conc = [
    ["C-280615-01", "B2층 3~5축 벽체", "25-24-15", 15, 25, "09:30",
     "13:00", 8, "13:00", "2028-06-18", "이상없음"],
]
for ri, row in enumerate(example_conc, start=18):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        style_cell(c, OPTIONAL_FILL, CENTER if ci != 11 else LEFT)

for ri in range(19, 22):
    for ci in range(1, 12):
        c = ws.cell(row=ri, column=ci)
        style_cell(c, OPTIONAL_FILL, CENTER if ci != 11 else LEFT)

# 섹션 3: 시험성적 / 자재
ws.merge_cells("A23:K23")
c = ws["A23"]
c.value = "③ 시험성적 / 자재 시험 (해당시)"
style_header(c)

mat_headers = [
    ("시험번호", 12), ("자재명", 16), ("시험종류", 16),
    ("시료채취일", 11), ("시험일", 11), ("기준값", 11), ("측정값", 11),
    ("판정", 10), ("시험기관", 14), ("성적서", 10), ("비고", 16),
]
for i, (h, w) in enumerate(mat_headers, start=1):
    c = ws.cell(row=24, column=i, value=h)
    style_header(c)

example_mat = [
    ["T-280615-01", "레미콘 25-24-15", "압축강도(7일)", "2028-06-08",
     "2028-06-15", "≥17.5MPa", "21.3MPa", "합격", "한국시험원", "수령", ""],
]
for ri, row in enumerate(example_mat, start=25):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        style_cell(c, OPTIONAL_FILL, CENTER if ci != 11 else LEFT)

for ri in range(26, 30):
    for ci in range(1, 12):
        c = ws.cell(row=ri, column=ci)
        style_cell(c, OPTIONAL_FILL, CENTER if ci != 11 else LEFT)

# 섹션 4: 부적합 사항
ws.merge_cells("A31:K31")
c = ws["A31"]
c.value = "④ 부적합 사항 / 재시공 (해당시)"
style_header(c)

ncr_headers = [
    ("NCR번호", 12), ("공종", 14), ("위치", 14), ("부적합 내용", 24),
    ("재시공 물량", 11), ("발견일", 11), ("조치완료일", 11),
    ("책임자", 10), ("비용추가", 10), ("결과", 11), ("비고", 14),
]
for i, (h, w) in enumerate(ncr_headers, start=1):
    c = ws.cell(row=32, column=i, value=h)
    style_header(c)

for ri in range(33, 38):
    for ci in range(1, 12):
        c = ws.cell(row=ri, column=ci)
        style_cell(c, OPTIONAL_FILL, CENTER if ci not in (4, 11) else LEFT)

dv_judge = DataValidation(
    type="list",
    formula1='"합격,불합격,재검측,조건부합격"',
    allow_blank=True,
)
ws.add_data_validation(dv_judge)
for r in range(7, 15):
    dv_judge.add(f"H{r}")
for r in range(25, 30):
    dv_judge.add(f"H{r}")

ws.row_dimensions[6].height = 30
ws.row_dimensions[17].height = 30
ws.row_dimensions[24].height = 30
ws.row_dimensions[32].height = 30
ws.freeze_panes = "A7"


# ============================================================
# Sheet 6: 종합 / 소장 확인
# ============================================================
ws = wb.create_sheet("6.종합_소장확인")

ws.merge_cells("A1:I1")
c = ws["A1"]
c.value = "현장 종합 일보 (소장 확인용)"
style_title(c)

ws["A3"] = "작성일자"
ws["B3"] = "2028-06-15 (목)"
ws["D3"] = "확인자"
ws["E3"] = "박상무 (현장소장)"
ws["G3"] = "확인시각"
ws["H3"] = "19:00"

for col in (1, 4, 7):
    style_subheader(ws.cell(row=3, column=col))
for col in (2, 5, 8):
    style_cell(ws.cell(row=3, column=col), REQUIRED_FILL)

# 요약 지표
ws.merge_cells("A5:I5")
c = ws["A5"]
c.value = "📊 당일 핵심 지표 요약"
style_header(c)

kpi_headers = [
    ("구분", 16), ("계획", 12), ("실적", 12), ("달성률", 10),
    ("누계 계획", 12), ("누계 실적", 12), ("누계 달성률", 11),
    ("상태", 10), ("비고", 20),
]
for i, (h, w) in enumerate(kpi_headers, start=1):
    c = ws.cell(row=6, column=i, value=h)
    style_header(c)
    ws.column_dimensions[get_column_letter(i)].width = w

kpi_rows = [
    ("건축 (㎡)", 180, 155, None, 12500, 11800, None, None, "지상 골조 진행중"),
    ("기계설비 (point)", 110, 67, None, 5800, 5200, None, None, "STS 자재 부족"),
    ("전기설비 (point)", 60, 55, None, 3200, 2950, None, None, "정상"),
    ("소방설비 (point)", 40, 38, None, 2100, 1980, None, None, "정상"),
    ("투입 인원 (명)", 50, 47, None, None, None, None, None, "협력 3개사"),
    ("안전사고 (건)", 0, 0, "-", None, None, "-", "무재해", "47일차"),
]
for ri, row in enumerate(kpi_rows, start=7):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        if ci in (4, 7, 8):
            style_cell(c, EXAMPLE_FILL, CENTER)
        else:
            style_cell(c, REQUIRED_FILL, CENTER if ci != 9 else LEFT)
    if ri <= 10:
        ws.cell(row=ri, column=4).value = f"=IF(B{ri}=0,0,C{ri}/B{ri}*100)"
        ws.cell(row=ri, column=4).number_format = "0.0"
        ws.cell(row=ri, column=7).value = f'=IF(E{ri}="",0,IF(E{ri}=0,0,F{ri}/E{ri}*100))'
        ws.cell(row=ri, column=7).number_format = "0.0"
        ws.cell(row=ri, column=8).value = (
            f'=IF(D{ri}=0,"-",IF(D{ri}>=95,"우수",'
            f'IF(D{ri}>=80,"정상",IF(D{ri}>=60,"부진","위험"))))'
        )

# 주요 이슈
ws.merge_cells("A14:I14")
c = ws["A14"]
c.value = "🚨 주요 이슈 / 의사결정 필요 사항"
style_header(c)

issue_headers = [
    ("우선순위", 10), ("구분", 12), ("내용", 36),
    ("영향", 18), ("필요 의사결정", 24), ("기한", 11), ("담당", 10),
]
for i, (h, w) in enumerate(issue_headers, start=1):
    c = ws.cell(row=15, column=i, value=h)
    style_header(c)
ws.column_dimensions["H"].width = 12
ws.column_dimensions["I"].width = 12

example_issues = [
    ["긴급", "자재", "철근 HD16 잔량 0.5톤 (최소 2톤 필요)",
     "내일 배근 작업 차질 우려", "긴급 발주 승인", "2028-06-15", "공무"],
    ["높음", "지연", "위생배관 PD 입상 작업 생산성 42%",
     "공기 5일 지연 가능성", "협력업체 인력 추가 투입", "2028-06-16", "기계담당"],
    ["중간", "설계변경", "지하주차장 구배 변경 (발주처)",
     "원가 +5,500만, 공기 +7일", "CO 승인 절차 진행", "2028-06-17", "공무"],
]
for ri, row in enumerate(example_issues, start=16):
    for ci, val in enumerate(row, start=1):
        c = ws.cell(row=ri, column=ci, value=val)
        style_cell(c, REQUIRED_FILL, CENTER if ci not in (3, 4, 5) else LEFT)

for ri in range(19, 23):
    for ci in range(1, 8):
        c = ws.cell(row=ri, column=ci)
        style_cell(c, OPTIONAL_FILL, CENTER if ci not in (3, 4, 5) else LEFT)

# 소장 의견
ws.merge_cells("A24:I24")
c = ws["A24"]
c.value = "✍️ 현장소장 의견 / 지시사항"
style_header(c)

ws.merge_cells("A25:I27")
c = ws["A25"]
c.value = (
    "1) 철근 HD16 긴급 발주 즉시 진행 (공무팀장 책임)\n"
    "2) 위생배관 협력업체 안전관리자와 협의하여 인력 보강 검토\n"
    "3) 발주처 설계변경 건은 본사 협의 후 CO 처리"
)
style_cell(c, INFO_FILL, LEFT)

# 결재
ws.merge_cells("A29:C29")
ws["A29"] = "공무"; style_subheader(ws["A29"])
ws.merge_cells("D29:F29")
ws["D29"] = "공사부장"; style_subheader(ws["D29"])
ws.merge_cells("G29:I29")
ws["G29"] = "현장소장"; style_subheader(ws["G29"])

ws.merge_cells("A30:C32")
ws.merge_cells("D30:F32")
ws.merge_cells("G30:I32")
for cell_ref in ("A30", "D30", "G30"):
    style_cell(ws[cell_ref])

dv_pri = DataValidation(type="list", formula1='"긴급,높음,중간,낮음"', allow_blank=True)
ws.add_data_validation(dv_pri)
for r in range(16, 23):
    dv_pri.add(f"A{r}")

dv_cat = DataValidation(
    type="list",
    formula1='"자재,지연,설계변경,안전,품질,인력,장비,기상,발주처,기타"',
    allow_blank=True,
)
ws.add_data_validation(dv_cat)
for r in range(16, 23):
    dv_cat.add(f"B{r}")

ws.row_dimensions[6].height = 30
ws.row_dimensions[15].height = 30
ws.row_dimensions[25].height = 60
ws.row_dimensions[30].height = 50
ws.freeze_panes = "A7"


# 저장
out_path = r"C:\Users\User\Documents\Codex\2026-05-19\smart-scheduler-mcp\docs\현장_일일입력양식.xlsx"
wb.save(out_path)
print(f"Saved: {out_path}")
