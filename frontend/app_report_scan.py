"""[DEPRECATED v3.3] 공사일보 스캔 앱 — app_mobile.py에 통합됨.

v3.3부터 이 파일은 사용하지 않습니다.
모든 기능이 app_mobile.py (port 8501)에 통합되었습니다.

  - 공사일보 촬영/업로드 → STEP 1
  - AI 자동 추출 결과 확인/수정 → STEP 2
  - 제출 → STEP 3

이 파일은 참조용으로만 유지되며, docker-compose에서 report-scanner 서비스가 제거되었습니다.
"""
raise SystemExit(
    "app_report_scan.py는 v3.3에서 app_mobile.py로 통합되었습니다.\n"
    "http://NAS_IP:8501 을 사용하세요."
)
