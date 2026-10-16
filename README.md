# Re:Cell 리셀 · 셀을 살리는 폐배터리 해체 로봇

제2회 ZYXCAD AX 경진대회 · 설계 부문 · 주제 2 FUTURE ROBOT · 팀 **POBIG**

접착제로 붙은 전기차 배터리(CTP) 셀을 부수지 않고 하나씩 떼어내 재사용하는 해체 로봇.
떼어낼 셀 아래만 데우는 구역 가열로 접착을 풀고, 흡착 공구로 셀을 들어 올림.

![cover](images/renders/cover.png)

## 폴더 구성

| 폴더 | 내용 |
|---|---|
| `docs/` | 작품 소개서 PDF, 도면 해설 페이지(`CTP_R03_explainer.html`), 공정 개념 영상 |
| `drawings/dwg/` | ZYXCAD AX로 정리한 도면. `ReCell_POBIG_도면_12장.dwg`(12장 통합)와 시트별 DWG |
| `drawings/dxf/` | 도면 원본 DXF 12장 |
| `drawings/pdf/` | 도면 12장 통합 PDF |
| `3d/` | 조립 3D 모델 (STEP, GLB) |
| `images/` | 공정 이미지 6장, 렌더링 이미지 |
| `reports/` | KS 적용 근거표, 강도 검토, 부품표, 질량표, 검사 기록 |
| `source/` | 3D 모델 · 도면 초안 · 해설 페이지 · 공정 시뮬레이션을 만든 Python 코드 (CadQuery 기반) |

## 도면 목록

| 도번 | 장수 | 내용 |
|---|---|---|
| D-01 | 1 | 전체 구조 · 공정 배치도 |
| D-02 | 3 | 03 셀 분리 공구 조립도, 부품표 |
| D-03 | 2 | 셀 · 냉각판 · 가열 작업대 단면도 |
| D-04 | 5 | 03 공구 가공 부품도 |
| D-09 | 1 | 02 절단 · 흡착 공구 외형도 |

## 도면 해설 페이지

`docs/CTP_R03_explainer.html`을 브라우저로 열면 도면, 3D 모델, 공정 순서, 공정 시뮬레이션을 볼 수 있음.

## 참고

- 모든 치수와 배치는 설계 가정값 (공개된 셀 치수 기반의 가상 CTP 팩)
- 공정 · 표지 이미지는 팀 CAD 모델을 참고해 생성형 AI(ChatGPT)로 만든 콘셉트 이미지
- 설계 도구: ZYXCAD AX, 생성형 AI(Claude, ChatGPT)
