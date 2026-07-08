# 카카오톡 완전 통합 설정 가이드 (v3.6)

현장 담당자가 **카카오톡 채팅방에서 일보 사진만 보내면** AI가 읽어서 DB에 저장되는 구조를 만듭니다.

```
담당자 카톡 → 카카오톡 채널 챗봇 → (오픈빌더 스킬) → Cloudflare Tunnel
                                                        ↓ HTTPS
                                              NAS Docker: POST /kakao/skill
                                                        ↓
                                       Vision AI 파싱 → .scheduler DB 저장
```

---

## 1단계 — 도메인 + Cloudflare Tunnel (약 30분, 연 ~1만원)

오픈빌더 스킬서버는 **공인 HTTPS 주소**가 필요합니다. NAS 포트포워딩 없이 Cloudflare Tunnel로 해결합니다.

1. 도메인 구입 (예: 가비아/Cloudflare Registrar, `mysite.co.kr` 등)
2. [Cloudflare](https://dash.cloudflare.com) 가입 → 도메인 추가 → 네임서버를 Cloudflare로 변경
3. **Zero Trust → Networks → Tunnels → Create a tunnel** (Cloudflared 방식)
   - 터널 이름: `scheduler`
   - 발급된 **토큰 복사** → NAS의 `.env` 파일에 `TUNNEL_TOKEN=eyJ...` 추가
4. Public Hostname 추가:
   - Subdomain: `site` / Domain: `mysite.co.kr`
   - Service: `http://api:8000` (Docker 내부 주소)
5. NAS에서 기동:
   ```bash
   docker-compose -f infrastructure/docker/docker-compose.yml --profile kakao up -d
   ```
6. 확인: 브라우저에서 `https://site.mysite.co.kr/health` → `{"status":"ok"}`

## 2단계 — 카카오톡 채널 + 챗봇 개설 (무료, 약 1시간)

1. [카카오 비즈니스](https://business.kakao.com) → **채널 개설** (예: "OO건설 홍은동현장")
2. [챗봇 관리자센터](https://i.kakao.com) → 봇 만들기 → 위 채널과 연결
3. **스킬 등록**: 설정 → 스킬 목록 → 스킬 추가
   - 이름: `스케줄러`
   - URL: `https://site.mysite.co.kr/kakao/skill`
4. **시나리오 블록 구성** (모두 같은 스킬 연결):

   | 블록 | 설정 |
   |------|------|
   | 폴백 블록 | 스킬 연결 + 응답은 "스킬데이터 사용" — 텍스트 보고·등록·현황이 모두 여기서 처리됨 |
   | 일보 사진 블록 | 패턴발화 "일보" + **파라미터에 `@sys.plugin.secureimage` 플러그인** 추가(파라미터명 `secureimage`) → 사용자가 사진 전송 가능 |
   | (선택) AI 챗봇 콜백 | 봇 설정에서 콜백 활성화 시 사진 파싱 완료 즉시 자동 회신 — 미설정 시 사용자가 "결과" 입력으로 확인 |

5. **배포** 버튼 → 채널 검색해서 친구 추가 → 대화 시작

## 3단계 — 담당자 등록 (각자 카톡에서 1회)

채널 채팅방에서:
```
등록 기계설비 김기계
```
→ 이후 발신자가 자동 식별됩니다.

## 사용법 (담당자)

| 입력 | 결과 |
|------|------|
| 📷 일보 사진 전송 | AI 파싱 → DB 저장 → 요약 회신 |
| `위생배관 70% 8명 자재 도착` | 해당 활동 실적 저장 |
| `현황` | 오늘 브리핑 카드 |
| `결과` | (사진 처리 후) 저장 결과 확인 |

## 소장용 — PlayMCP로 브리핑 받기 (선택)

1. PC에서 [playmcp.kakao.com](https://playmcp.kakao.com) → 카카오톡 도구 → "Claude와 연결" → OAuth 동의
2. Claude Desktop에서:
   > "카톡용 브리핑 만들어서 내 카톡으로 보내줘"
   - `get_kakao_briefing` MCP tool이 텍스트 생성 → PlayMCP가 **내 카톡방**으로 전송
3. 받은 메시지를 현장 단체방에 전달(1탭)

**PlayMCP 한계**: 본인 카톡방 전송만 가능(단톡방 직접 발송 불가), PC 전용, 자동 발송 불가.

## 다음 단계 (Phase 3 — 별도 진행)

- **알림톡 자동 푸시**: 2단계에서 만든 채널을 비즈니스 채널로 전환 + 딜러사(비즈고/다이렉트센드 등) 가입 → 17시 미제출 리마인더 자동 발송 (~7.5원/건)
- 템플릿 검수 1~3영업일 소요

## 문제 해결

| 증상 | 원인/해결 |
|------|----------|
| cloudflared 재시작 반복 | `.env`에 TUNNEL_TOKEN 미설정 |
| 챗봇 "응답 없음" | 스킬 URL 오타 또는 터널 다운 — `/health` 확인 |
| 사진 보냈는데 파싱 안 됨 | 일보 사진 블록에 secureimage 플러그인 미설정 |
| "❌ 사진 다운로드 실패" | 이미지 URL 10분 만료 — 다시 전송 |
| AI 파싱 실패 | NAS `.env`의 GEMINI_API_KEY 확인 |
