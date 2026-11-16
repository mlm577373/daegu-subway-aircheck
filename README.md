# 대구 도시철도 미세먼지 분석

2026 대구광역시 기후·환경·탄소중립 공공데이터 AI 활용대회 제출 완료 프로젝트.

## 최종 결과물

- [보고서 PPT](최종제출본/보고서.pptx)
- [분석근거 Word](최종제출본/분석근거_정리본.docx)
- [인터랙티브 지도](최종제출본/시각화_인터랙티브지도.html): 브라우저로 열면 동작
- [붙임 1~5 최신 작성본](최종제출본/공모전_붙임1-5_수정본.docx): 프로젝트에서 작성한 최신 사본. 별도로 서명·수정하여 실제 접수한 파일과는 다를 수 있음

## 자료와 코드

- data/: 수집 원자료, 출처 메타데이터, 전처리 및 시간별 결합자료
- data/_scripts/: 최종 분석과 수집·전처리·검증 코드
- outputs/management_map/: 관리 위험도, 반복 시간대, 가중치 민감도 및 지도 근거
- outputs/operation_change/: 시간표 개편 관련 분석과 검증
- outputs/inspection_candidates/tables/all_station_metrics.csv: 지도 검증 코드의 비교 근거표
- outputs/submission_draft/_build/: 최신 PPT 생성 코드와 필수 입력만 보존. 기존 코드 경로 호환을 위해 폴더 이름 유지
- outputs/_submission_draft_validation/deck_validation_v6.json: 생성 시점 PPT 검증. 사용자가 이후 편집한 최종 PPT의 검증 기록은 아님

주 관리 위험도는 2022~2024년 연간 자료를 사용하며, 2025·2026년은 확보 기간의 보조 검토에 사용했다.
주요 재현 코드는 baseline_management.py, build_management_map.py, check_risk_weights.py, analyze_operation_change.py, finalize_operation_change.py다. 수집 및 자료 준비 코드도 보존했다. 코드 실행은 결과를 갱신할 수 있으므로 제출 파일은 별도 보존한다.

## 실행 환경과 재현 절차

Python 3.12 환경에서 분석했다. 프로젝트 루트에서 다음과 같이 설치한다.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

원자료와 대용량 중간자료는 Git에서 제외했다. 따라서 새로 내려받은 저장소에는 분석 실행에 필요한 데이터가 없다. 로컬 백업의 `data/`를 같은 경로에 복원하거나, 아래 출처에서 자료를 수집하고 전처리해야 한다. 데이터는 저장소에 자동으로 포함되지 않는다.

| 필요한 자료 | 경로 또는 설명 |
|---|---|
| 연도별 결합자료 | `data/merged/merged_hourly_2022.csv` ~ `merged_hourly_2026.csv` |
| 역 좌표·매칭표 | `data/mapping/` |
| 기상·달력 | `data/weather/weather_hourly_2022_2024.csv`, `data/calendar/calendar_2022_2024.csv` |
| 개편 전후 시간표 | `data/timetable_change/sources/`, 파싱한 시간대별 운행 자료 |

원자료 출처는 [InAir](https://www.inair.or.kr/info/excel.html), [AirKorea](https://www.airkorea.or.kr/web/last_amb_hour_data), [대구교통공사 승하차](https://www.data.go.kr/data/15002503/fileData.do), [NOAA](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)이며, 상세 출처는 최종 분석근거 Word 9절에 있다. 다운로드 시점에 따라 공개 이력과 응답이 달라질 수 있다. 데이터별 재배포 조건은 원 제공처를 따른다.

자료를 복원한 다음, 다음 순서로 실행한다. 아래 단계는 저장된 결과를 갱신할 수 있다.

```powershell
python data/_scripts/build_management_map.py
python data/_scripts/check_risk_weights.py
python data/_scripts/verify_management_map.py
python data/_scripts/render_management_figures.py
python data/_scripts/analyze_operation_change.py
python data/_scripts/finalize_operation_change.py
```

결합자료를 원자료에서 다시 만들 때는 `prepare_data.py`, `prepare_join_coordinates.py`, `build_mapping_tables.py`, `merge_observations.py`의 입력 경로를 확인한다. 기상·달력 준비는 `prepare_extended_factors.py`, 시간표 파싱은 `prepare_operation_timetables.py`가 담당한다. 자동 수집 스크립트는 원본 다운로드를 수행하므로 분석 결과 확인만 필요하면 실행하지 않아도 된다.

PPT 생성은 Codex에 포함된 `@oai/artifact-tool`과 전용 검증 도구를 사용했다. 최신 생성 코드에는 Windows 로컬 런타임 경로가 들어 있으므로 일반 Node.js 환경에서 바로 실행되지 않는다. Word 생성에는 `python-docx`, 미리보기에는 Windows Word COM을 사용했다. Noto Sans KR·Noto Serif KR 서체가 필요하며, 일부 분석 그림은 맑은 고딕의 Windows 경로를 참조한다. 최종 제출 PPT는 생성 후 사용자가 편집했으므로 빌더 실행 결과와 완전히 동일하지 않을 수 있다.

## 정리와 복구 기록

2026년 11월 16일, 이전 보고서·PPT·양식 초안, 렌더 미리보기, 초기 탐색 산출물, 임시 DB와 차트 파일 등 445개 파일을 작업 폴더에서 제거했다. 제거 전 압축본과 SHA256을 대조했으며, 남겨둔 기존 파일도 모두 체크섬을 확인했다.

- outputs/_archive/post_submission_20261116_221002.zip: 이번 정리 복구용 압축본. 원래 경로와 SHA256 포함
- outputs/post_submission_cleanup.json: 정리 대상·사유와 보존 파일 체크섬. 이 목록 중 공통 수집 모듈과 검증 근거표 2개는 추가 보존
- outputs/post_submission_cleanup_result.json: 실제 제거 결과
- outputs/_archive/cleanup_20261114.zip: 이전 정리 백업

복구할 때는 압축본에서 필요한 항목만 원래 상대 경로로 꺼낸다. 원자료와 최종 분석 산출물은 현재 폴더에 유지했다.
