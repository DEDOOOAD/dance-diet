from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


OUT = Path("docs/Server_Dance_diet_project_overview.pptx")
GIF = Path("test.gif")
EMU = 914400
SW, SH = 12192000, 6858000
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

C = {
    "ink": "111820",
    "ink2": "17212B",
    "paper": "F6F3EC",
    "white": "FFFFFF",
    "muted": "AEB8BF",
    "line": "32404B",
    "text": "18222D",
    "sub": "44525D",
    "teal": "2AA7A5",
    "green": "73B66B",
    "coral": "F26957",
    "gold": "E5B94B",
    "blue": "3B7DDD",
    "soft": "EEF3F4",
    "soft_gold": "F7EBC3",
}


def e(v: float) -> int:
    return int(v * EMU)


def x(s: str) -> str:
    return escape(s, {'"': "&quot;"})


class Slide:
    def __init__(self, bg: str = C["paper"]) -> None:
        self.bg = bg
        self.items: list[str] = []
        self.rels: list[tuple[str, str, str]] = []
        self.sid = 2
        self.rid = 2

    def _id(self) -> int:
        v = self.sid
        self.sid += 1
        return v

    def shape(self, x0: float, y0: float, w: float, h: float, fill: str, line: str | None = None, preset: str = "roundRect") -> None:
        sid = self._id()
        ln = f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else "<a:ln><a:noFill/></a:ln>"
        self.items.append(f"""
<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="shape{sid}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="{e(x0)}" y="{e(y0)}"/><a:ext cx="{e(w)}" cy="{e(h)}"/></a:xfrm>
<a:prstGeom prst="{preset}"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>{ln}</p:spPr></p:sp>""")

    def text(self, x0: float, y0: float, w: float, h: float, text: str | list[str], *, size: int = 16, color: str = C["text"], bold: bool = False, fill: str | None = None, line: str | None = None, align: str = "l", anchor: str = "t") -> None:
        sid = self._id()
        paras = [text] if isinstance(text, str) else text
        runs = []
        for p in paras:
            runs.append(f"""<a:p><a:pPr algn="{align}"/><a:r><a:rPr lang="ko-KR" sz="{size * 100}" b="{1 if bold else 0}">
<a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="Aptos"/><a:ea typeface="Malgun Gothic"/><a:cs typeface="Malgun Gothic"/></a:rPr><a:t>{x(p)}</a:t></a:r></a:p>""")
        fill_xml = "<a:noFill/>" if fill is None else f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
        line_xml = f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else "<a:ln><a:noFill/></a:ln>"
        self.items.append(f"""
<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="text{sid}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="{e(x0)}" y="{e(y0)}"/><a:ext cx="{e(w)}" cy="{e(h)}"/></a:xfrm>
<a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom>{fill_xml}{line_xml}</p:spPr>
<p:txBody><a:bodyPr wrap="square" anchor="{anchor}" lIns="91440" rIns="91440" tIns="45720" bIns="45720"><a:normAutofit fontScale="82000" lnSpcReduction="20000"/></a:bodyPr><a:lstStyle/>{''.join(runs)}</p:txBody></p:sp>""")

    def bullets(self, x0: float, y0: float, w: float, h: float, items: list[str], *, size: int = 15, fill: str = C["white"]) -> None:
        sid = self._id()
        runs = []
        for item in items:
            runs.append(f"""<a:p><a:pPr marL="228600" indent="-171450"><a:buChar char="•"/></a:pPr><a:r><a:rPr lang="ko-KR" sz="{size * 100}">
<a:solidFill><a:srgbClr val="{C['text']}"/></a:solidFill><a:latin typeface="Aptos"/><a:ea typeface="Malgun Gothic"/><a:cs typeface="Malgun Gothic"/></a:rPr><a:t>{x(item)}</a:t></a:r></a:p>""")
        self.items.append(f"""
<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="bullets{sid}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="{e(x0)}" y="{e(y0)}"/><a:ext cx="{e(w)}" cy="{e(h)}"/></a:xfrm>
<a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill><a:ln w="12700"><a:solidFill><a:srgbClr val="DFE4E8"/></a:solidFill></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap="square" anchor="t" lIns="137160" rIns="91440" tIns="91440" bIns="91440"><a:normAutofit fontScale="80000" lnSpcReduction="25000"/></a:bodyPr><a:lstStyle/>{''.join(runs)}</p:txBody></p:sp>""")

    def pic(self, x0: float, y0: float, w: float, h: float) -> None:
        if not GIF.exists():
            return
        sid = self._id()
        rid = f"rId{self.rid}"
        self.rid += 1
        self.rels.append((rid, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image", "../media/test.gif"))
        self.items.append(f"""
<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="test.gif"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>
<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
<p:spPr><a:xfrm><a:off x="{e(x0)}" y="{e(y0)}"/><a:ext cx="{e(w)}" cy="{e(h)}"/></a:xfrm><a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom><a:ln w="12700"><a:solidFill><a:srgbClr val="{C['line']}"/></a:solidFill></a:ln></p:spPr></p:pic>""")

    def xml(self) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}"><p:cSld>
<p:bg><p:bgPr><a:solidFill><a:srgbClr val="{self.bg}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{''.join(self.items)}</p:spTree>
</p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"""

    def rels_xml(self) -> str:
        rels = [("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout", "../slideLayouts/slideLayout1.xml"), *self.rels]
        body = "\n".join(f'<Relationship Id="{rid}" Type="{typ}" Target="{target}"/>' for rid, typ, target in rels)
        return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{body}</Relationships>'


def title(slide: Slide, text: str, sub: str = "") -> None:
    dark = slide.bg == C["ink"]
    slide.text(0.62, 0.35, 4.8, 0.3, sub, size=10, color=C["gold"] if dark else C["line"], bold=True)
    slide.text(0.58, 0.72, 9.8, 0.55, text, size=25, color=C["white"] if dark else C["text"], bold=True)
    slide.shape(0.62, 1.38, 0.95, 0.05, C["coral"], preset="rect")
    slide.shape(1.72, 1.38, 0.7, 0.05, C["teal"], preset="rect")
    slide.shape(2.55, 1.38, 0.42, 0.05, C["gold"], preset="rect")


def footer(slide: Slide, idx: int, total: int) -> None:
    col = C["muted"] if slide.bg == C["ink"] else C["line"]
    slide.text(0.62, 7.04, 4.3, 0.22, "Server_Dance-diet | project(프로젝트) PPT(파워포인트)", size=8, color=col)
    slide.text(11.7, 7.04, 0.8, 0.22, f"{idx:02d}/{total:02d}", size=8, color=col, align="r")


def card(slide: Slide, x0: float, y0: float, w: float, h: float, head: str, body: str, color: str) -> None:
    slide.shape(x0, y0, w, h, C["white"], "DFE4E8")
    slide.shape(x0, y0, 0.08, h, color, preset="rect")
    slide.text(x0 + 0.16, y0 + 0.14, w - 0.32, 0.28, head, size=13, bold=True)
    slide.text(x0 + 0.16, y0 + 0.55, w - 0.32, h - 0.62, body, size=10, color=C["sub"])


def pill(slide: Slide, x0: float, y0: float, w: float, text: str, color: str) -> None:
    slide.text(x0, y0, w, 0.34, text, size=10, color=C["white"], bold=True, fill=color, align="c", anchor="mid")


def build_slides() -> list[Slide]:
    slides: list[Slide] = []

    s = Slide(C["ink"])
    s.shape(8.55, -0.2, 4.9, 7.9, C["ink2"], preset="rect")
    s.text(0.72, 0.62, 4.8, 0.32, "PROJECT(프로젝트) PRESENTATION(발표 자료)", size=11, color=C["gold"], bold=True)
    s.text(0.66, 1.34, 7.6, 1.1, "Dance Diet Server", size=42, color=C["white"], bold=True)
    s.text(0.72, 2.62, 6.85, 0.95, "FastAPI(패스트API) 기반 app-facing API(앱 연동 인터페이스), realtime WebSocket(실시간 웹소켓), AI bridge(인공지능 브리지), Supabase(슈파베이스) data layer(데이터 계층)를 정리한 overview deck(개요 덱).", size=16, color="D8E1E6")
    pill(s, 0.72, 4.05, 2.05, "FastAPI(패스트API)", C["teal"])
    pill(s, 3.0, 4.05, 2.05, "WebSocket(웹소켓)", C["coral"])
    pill(s, 5.28, 4.05, 2.25, "Supabase(슈파베이스)", C["green"])
    s.pic(9.15, 1.0, 3.25, 3.25)
    s.text(9.1, 4.55, 3.25, 0.85, "test.gif demo asset(데모 자산)으로 pose analysis(포즈 분석) 방향성을 보여줍니다.", size=14, color="E9EEF2", align="c")
    s.text(0.72, 6.42, 4.5, 0.3, f"Generated(생성): {datetime.now(timezone.utc).strftime('%Y-%m-%d')}", size=10, color=C["muted"])
    slides.append(s)

    s = Slide()
    title(s, "Agenda(목차)", "Presentation Structure(발표 구성)")
    items = [
        ("01", "Project Context(프로젝트 맥락)", "goal(목표), user journey(사용자 여정), repository map(저장소 지도)"),
        ("02", "Architecture(아키텍처)", "data definition diagram(데이터 정의 구성도), runtime config(실행 설정), data flow(데이터 흐름)"),
        ("03", "API & Protocol(API와 프로토콜)", "REST endpoint(REST 엔드포인트), WebSocket protocol(웹소켓 프로토콜), AI bridge(인공지능 브리지)"),
        ("04", "Quality & Roadmap(품질과 로드맵)", "risk(리스크), test plan(테스트 계획), next sprint(다음 스프린트)"),
    ]
    y0 = 1.72
    for num, head, body in items:
        s.text(0.9, y0, 0.72, 0.5, num, size=16, color=C["white"], bold=True, fill=C["teal"], align="c", anchor="mid")
        s.text(1.84, y0, 3.45, 0.5, head, size=17, bold=True, anchor="mid")
        s.text(5.45, y0, 6.35, 0.5, body, size=13, color=C["sub"], fill=C["white"], line="DFE4E8", anchor="mid")
        y0 += 0.96
    s.text(0.9, 5.9, 10.9, 0.38, "Design note(디자인 메모): dense content(밀도 있는 내용)는 여러 slide(슬라이드)로 나누어 text overflow(텍스트 넘침)를 줄였습니다.", size=12, color=C["sub"], fill=C["soft"], align="c")
    slides.append(s)

    s = Slide()
    title(s, "One-page Summary(한 장 요약)", "Executive Summary(요약)")
    card(s, 0.65, 1.75, 2.85, 1.55, "Goal(목표)", "dance workout(댄스 운동)과 food intake(식단 섭취)를 mobile client(모바일 클라이언트)에서 기록합니다.", C["teal"])
    card(s, 3.8, 1.75, 2.85, 1.55, "Core(핵심)", "REST API(REST API) + WebSocket(웹소켓) + AI bridge(인공지능 브리지)로 request(요청)를 분리합니다.", C["coral"])
    card(s, 6.95, 1.75, 2.85, 1.55, "Data(데이터)", "Supabase(슈파베이스) table(테이블)과 bucket(버킷)으로 profile(프로필), food log(식단 기록), image(이미지)를 관리합니다.", C["green"])
    card(s, 10.1, 1.75, 2.55, 1.55, "Status(상태)", "general server(일반 서버)는 구현되어 있고 AI server(인공지능 서버)는 bridge(브리지) 대상으로 보입니다.", C["gold"])
    s.bullets(0.72, 4.0, 11.8, 1.7, [
        "current codebase(현재 코드베이스)는 app tab(앱 탭) payload(페이로드), profile update(프로필 수정), food upload(식단 업로드), live session(실시간 세션)을 포괄합니다.",
        "realtime frame(실시간 프레임)은 client(클라이언트) -> general server(일반 서버) -> AI server(인공지능 서버) -> client(클라이언트) 순서로 흐릅니다.",
        "next milestone(다음 마일스톤)은 AI server(인공지능 서버) 위치 정리, protocol(프로토콜) 통일, deployment readiness(배포 준비도) 강화입니다.",
    ])
    slides.append(s)

    s = Slide()
    title(s, "Product Goal(제품 목표)", "Why It Exists(존재 이유)")
    s.text(0.72, 1.7, 5.55, 0.82, "사용자가 춤을 추고, 먹은 음식을 찍고, 목표 calorie(칼로리)를 매일 확인하는 loop(루프)를 짧게 만듭니다.", size=24, bold=True)
    card(s, 0.74, 3.0, 3.75, 1.55, "Dance tracking(댄스 추적)", "camera frame(카메라 프레임)을 live stream(실시간 스트림)으로 보내 movement score(움직임 점수)와 burned calorie(소모 칼로리)를 받습니다.", C["coral"])
    card(s, 4.78, 3.0, 3.75, 1.55, "Food logging(식단 기록)", "meal image(식사 이미지)를 upload(업로드)하고 analysis result(분석 결과)를 DailyFoodLog table(테이블)에 저장합니다.", C["green"])
    card(s, 8.82, 3.0, 3.75, 1.55, "Mobile home(모바일 홈)", "home/profile/record/class tab(탭)에 필요한 payload(페이로드)를 REST endpoint(엔드포인트)로 제공합니다.", C["teal"])
    s.text(7.1, 1.72, 5.0, 0.65, "Main promise(핵심 약속): workout data(운동 데이터)와 food data(식단 데이터)를 한 화면에서 이어 봅니다.", size=15, bold=True, fill=C["soft_gold"])
    slides.append(s)

    s = Slide()
    title(s, "User Journey(사용자 여정)", "App-facing Flow(앱 연동 흐름)")
    lanes = [
        ("Onboarding(가입)", "signup request(가입 요청)\nprofile record(프로필 기록)", C["blue"]),
        ("Daily Home(일일 홈)", "target calorie(목표 칼로리)\nintake summary(섭취 요약)", C["teal"]),
        ("Dance Session(댄스 세션)", "start session(세션 시작)\nframe streaming(프레임 스트리밍)\nresult feedback(결과 피드백)", C["coral"]),
        ("Food Intake(식단 섭취)", "image upload(이미지 업로드)\nAI analysis(인공지능 분석)\nfood log(식단 기록)", C["green"]),
        ("Record Review(기록 확인)", "weekly/monthly view(주간/월간 보기)\nprogress check(진행 확인)", C["gold"]),
    ]
    x0 = 0.65
    for head, body, color in lanes:
        s.text(x0, 1.75, 2.2, 0.56, head, size=13, color=C["white"], bold=True, fill=color, align="c", anchor="mid")
        s.text(x0, 2.48, 2.2, 1.45, body, size=12, color=C["text"], fill=C["white"], line="DFE4E8", align="c", anchor="mid")
        if x0 < 9.7:
            s.shape(x0 + 2.25, 2.95, 0.34, 0.15, C["line"], preset="rightArrow")
        x0 += 2.45
    s.bullets(0.82, 4.65, 11.35, 1.08, [
        "server(서버)는 screen tab(화면 탭)별 payload(페이로드)를 제공하고, realtime feedback(실시간 피드백)은 WebSocket(웹소켓)으로 분리합니다.",
        "user value(사용자 가치)는 workout action(운동 행동)과 meal record(식사 기록)가 같은 calorie narrative(칼로리 맥락)로 이어지는 점입니다.",
    ], size=13)
    slides.append(s)

    s = Slide()
    title(s, "Tech Stack(기술 스택)", "Dependencies(의존성) & Roles(역할)")
    card(s, 0.78, 1.72, 3.55, 1.32, "API runtime(API 실행 환경)", "FastAPI(패스트API), uvicorn(유비콘), Pydantic(파이단틱), python-multipart(파이썬 멀티파트).", C["blue"])
    card(s, 4.62, 1.72, 3.55, 1.32, "Realtime(실시간)", "websockets(웹소켓 라이브러리), Starlette WebSocket(스타렛 웹소켓), request_lock(요청 잠금).", C["coral"])
    card(s, 8.46, 1.72, 3.55, 1.32, "Data layer(데이터 계층)", "Supabase(슈파베이스), storage bucket(스토리지 버킷), environment variable(환경 변수).", C["green"])
    card(s, 0.78, 3.55, 3.55, 1.32, "AI prototype(인공지능 프로토타입)", "MediaPipe(미디어파이프), OpenCV(오픈CV), NumPy(넘파이), pose landmark(포즈 랜드마크).", C["teal"])
    card(s, 4.62, 3.55, 3.55, 1.32, "Local tooling(로컬 도구)", "uv(유브이), pyproject.toml(파이프로젝트 설정), README(리드미), demo script(데모 스크립트).", C["gold"])
    card(s, 8.46, 3.55, 3.55, 1.32, "Client contract(클라이언트 계약)", "HTTP request(HTTP 요청), JSON response(JSON 응답), WebSocket message(웹소켓 메시지).", C["blue"])
    slides.append(s)

    s = Slide()
    title(s, "Repository Map(저장소 지도)", "Current Files(현재 파일)")
    card(s, 0.7, 1.7, 3.35, 1.34, "entrypoint(진입점)", "main.py\nuvicorn(유비콘)이 general server(일반 서버)를 실행합니다.", C["blue"])
    card(s, 4.35, 1.7, 3.75, 1.34, "general_server package(패키지)", "server.py, internal_services.py, session_manager.py\nREST API(REST API)와 session state(세션 상태)를 담당합니다.", C["teal"])
    card(s, 8.4, 1.7, 3.55, 1.34, "socket package(패키지)", "live_session_route.py, ai_outbound.py\nWebSocket(웹소켓) client(클라이언트)와 AI bridge(인공지능 브리지)를 연결합니다.", C["coral"])
    card(s, 0.7, 3.52, 3.35, 1.34, "shared package(패키지)", "schemas.py, db_connect.py, Bucket.py\nPydantic(파이단틱) schema(스키마), Supabase(슈파베이스) 연결, bucket name(버킷 이름).", C["green"])
    card(s, 4.35, 3.52, 3.75, 1.34, "demo scripts(데모 스크립트)", "live_session_client_test.py, kcal_cal.py, rocognize_gif.py\nOpenCV(오픈CV), MediaPipe(미디어파이프) 기반 prototype(프로토타입).", C["gold"])
    card(s, 8.4, 3.52, 3.55, 1.34, "docs mismatch(문서 차이)", "README(리드미)는 servers/ai_server path(경로)를 언급하지만 current repository(현재 저장소) file list(파일 목록)에는 없습니다.", C["coral"])
    s.text(0.75, 5.55, 11.6, 0.56, "Presentation(발표 자료)는 README(리드미)보다 actual implementation(실제 구현)을 우선해 구성했습니다.", size=16, color=C["sub"], bold=True, fill=C["white"], align="c")
    slides.append(s)

    s = Slide()
    title(s, "System Architecture(시스템 아키텍처)", "Runtime View(실행 관점)")
    s.text(0.75, 1.72, 2.25, 0.78, "Mobile client(모바일 클라이언트)", size=16, color=C["white"], bold=True, fill=C["blue"], align="c", anchor="mid")
    s.shape(3.18, 2.03, 0.75, 0.18, C["coral"], preset="rightArrow")
    s.text(4.18, 1.55, 2.9, 1.12, "General server(일반 서버)\nFastAPI(패스트API)\nREST API(REST API) + WebSocket(웹소켓)", size=15, color=C["white"], bold=True, fill=C["teal"], align="c", anchor="mid")
    s.shape(7.28, 2.03, 0.75, 0.18, C["gold"], preset="rightArrow")
    s.text(8.28, 1.55, 2.75, 1.12, "AI server(인공지능 서버)\nDance/Food analysis(분석)", size=15, color=C["white"], bold=True, fill=C["coral"], align="c", anchor="mid")
    s.text(4.18, 3.65, 2.9, 0.9, "Supabase(슈파베이스)\ndatabase(데이터베이스) + storage(스토리지)", size=15, color=C["white"], bold=True, fill=C["green"], align="c", anchor="mid")
    s.shape(5.25, 2.78, 0.32, 0.62, C["green"], preset="downArrow")
    s.bullets(0.78, 4.95, 11.5, 1.25, [
        "REST request(REST 요청)는 profile(프로필), home(홈), class(클래스), record(기록), food intake(식단 섭취)를 처리합니다.",
        "WebSocket(웹소켓)은 live session frame(실시간 세션 프레임)을 AI server(인공지능 서버)에 relay(중계)합니다.",
        "Supabase(슈파베이스)는 user data(사용자 데이터)와 image file(이미지 파일)의 persistence(영속성)를 담당합니다.",
    ], size=14)
    slides.append(s)

    s = Slide()
    title(s, "Data Definition Map(데이터 정의 지도)", "Pydantic Schema(파이단틱 스키마) 중심")
    card(s, 0.72, 1.55, 2.75, 1.1, "UserSignUp(사용자 가입)", "name, email, password, age, created_at\n-> SignUp table(가입 테이블) row(행)", C["blue"])
    card(s, 3.78, 1.55, 2.75, 1.1, "UserProfileUpdate(프로필 수정)", "height, weight, target_weight, target_day, image path(이미지 경로)\n-> Profile table(프로필 테이블)", C["teal"])
    card(s, 6.84, 1.55, 2.75, 1.1, "LiveSessionStartRequest(세션 시작 요청)", "uuid, dance_type, content_id\n-> session_id + ws_url response(응답)", C["coral"])
    card(s, 9.9, 1.55, 2.75, 1.1, "LiveSessionEndResponse(세션 종료 응답)", "total_frames, elapsed_seconds, total_calories, ended_at", C["gold"])
    s.shape(3.48, 2.0, 0.18, 0.15, C["line"], preset="rightArrow")
    s.shape(6.54, 2.0, 0.18, 0.15, C["line"], preset="rightArrow")
    s.shape(9.6, 2.0, 0.18, 0.15, C["line"], preset="rightArrow")
    card(s, 0.72, 3.28, 2.75, 1.1, "LiveFrameMessage(실시간 프레임 메시지)", "UUID, session_id, frame_index, total_frame, image bytes(이미지 바이트), user_weight", C["blue"])
    card(s, 3.78, 3.28, 2.75, 1.1, "LiveFrameMessage_go_ai_server(AI 전달 메시지)", "type=frame_base64, image string(이미지 문자열), metadata(메타데이터)", C["coral"])
    card(s, 6.84, 3.28, 2.75, 1.1, "AiLiveAnalysisMessage(AI 분석 메시지)", "processed_at, calories_burned, movement_score", C["green"])
    card(s, 9.9, 3.28, 2.75, 1.1, "LiveFrameResultMessage(프레임 결과 메시지)", "accepted, total_frames, elapsed_seconds, total_calories, movement_score", C["teal"])
    s.shape(3.48, 3.73, 0.18, 0.15, C["line"], preset="rightArrow")
    s.shape(6.54, 3.73, 0.18, 0.15, C["line"], preset="rightArrow")
    s.shape(9.6, 3.73, 0.18, 0.15, C["line"], preset="rightArrow")
    card(s, 0.72, 5.02, 3.8, 0.82, "FoodItem(음식 항목)", "label, calories, confidence", C["gold"])
    card(s, 4.78, 5.02, 3.8, 0.82, "FoodIntakeAnalysisResponse(식단 섭취 분석 응답)", "foods list(음식 목록), total_calories, source, analyzed_at", C["green"])
    card(s, 8.84, 5.02, 3.5, 0.82, "FoodRecordResponse(식단 기록 응답)", "UUID, Day, Foods, TotalCalories, RecordCount", C["coral"])
    slides.append(s)

    s = Slide()
    title(s, "Runtime Config(실행 설정)", "Host(호스트), Port(포트), Path(경로)")
    rows = [
        ("GENERAL_SERVER_HOST", "127.0.0.1 default(기본값)", "FastAPI app bind address(앱 바인드 주소)"),
        ("GENERAL_SERVER_PORT", "8000 default(기본값)", "mobile client(모바일 클라이언트)가 접근하는 API port(API 포트)"),
        ("AI_HOST / AI_PORT", "0.0.0.0 / 8001 default(기본값)", "AI server(인공지능 서버) WebSocket target(웹소켓 대상)"),
        ("AI_DANCE_WS_PATH", "/ws/dance/analyze default(기본값)", "dance frame analysis path(댄스 프레임 분석 경로)"),
        ("AI_FOOD_WS_PATH", "/ws/food/analyze default(기본값)", "food image analysis path(음식 이미지 분석 경로)"),
        ("SUPABASE_URL / SUPABASE_KEY", ".env file(.env 파일)", "database/storage credential(데이터베이스/스토리지 자격 증명)"),
    ]
    y0 = 1.55
    for name, default, role in rows:
        s.text(0.82, y0, 3.2, 0.46, name, size=12, color=C["white"], bold=True, fill=C["ink2"], anchor="mid")
        s.text(4.18, y0, 3.0, 0.46, default, size=12, fill=C["white"], line="DFE4E8", anchor="mid")
        s.text(7.35, y0, 4.65, 0.46, role, size=12, fill=C["white"], line="DFE4E8", anchor="mid")
        y0 += 0.68
    slides.append(s)

    s = Slide()
    title(s, "Live Session Flow(실시간 세션 흐름)", "WebSocket(웹소켓) Scenario(시나리오)")
    xs = [0.72, 3.15, 5.58, 8.01, 10.44]
    steps = [
        ("1", "POST(전송)\n/api/live/session/start", C["blue"]),
        ("2", "ws_url response(응답)\nclient connection(연결)", C["teal"]),
        ("3", "frame payload(프레임 페이로드)\nimage bytes/base64(이미지 바이트/베이스64)", C["coral"]),
        ("4", "AI analysis(인공지능 분석)\ncalorie + score(칼로리 + 점수)", C["gold"]),
        ("5", "frame_result response(응답)\nprogress(진행 상태)", C["green"]),
    ]
    for i, (num, body, color) in enumerate(steps):
        s.text(xs[i], 1.82, 0.55, 0.55, num, size=18, color=C["white"], bold=True, fill=color, align="c", anchor="mid")
        s.text(xs[i] + 0.65, 1.7, 1.6, 0.9, body, size=11, bold=True, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
        if i < 4:
            s.shape(xs[i] + 2.28, 2.05, 0.38, 0.15, C["line"], preset="rightArrow")
    s.bullets(0.78, 3.55, 11.6, 1.75, [
        "session_manager.py stores LIVE_SESSIONS dict(딕셔너리)에 status(상태), total_frames(총 프레임), elapsed_seconds(경과 초), total_calories(총 칼로리)를 보관합니다.",
        "ai_outbound.py uses per-session request_lock(세션별 요청 잠금)으로 AI server message(인공지능 서버 메시지) 순서를 보호합니다.",
        "session end(세션 종료)는 client socket(클라이언트 소켓)과 AI connection(인공지능 연결)을 닫고 summary response(요약 응답)를 반환합니다.",
    ])
    slides.append(s)

    s = Slide()
    title(s, "Live Payload Data Flow(실시간 페이로드 데이터 흐름)", "Frame(프레임) Transformation(변환)")
    s.text(0.72, 1.58, 1.95, 0.58, "1 Start request(시작 요청)", size=12, color=C["white"], bold=True, fill=C["blue"], align="c", anchor="mid")
    s.text(0.72, 2.25, 1.95, 0.95, "LiveSessionStartRequest\nuuid\ndance_type\ncontent_id", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.shape(2.82, 2.62, 0.38, 0.14, C["line"], preset="rightArrow")
    s.text(3.35, 1.58, 1.95, 0.58, "2 Session state(세션 상태)", size=12, color=C["white"], bold=True, fill=C["teal"], align="c", anchor="mid")
    s.text(3.35, 2.25, 1.95, 0.95, "LIVE_SESSIONS\nsession_id\nstatus=active\nstarted_at", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.shape(5.45, 2.62, 0.38, 0.14, C["line"], preset="rightArrow")
    s.text(5.98, 1.58, 1.95, 0.58, "3 Client frame(클라이언트 프레임)", size=12, color=C["white"], bold=True, fill=C["coral"], align="c", anchor="mid")
    s.text(5.98, 2.25, 1.95, 0.95, "LiveFrameMessage\nimage: bytes\nframe_index\nuser_weight", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.shape(8.08, 2.62, 0.38, 0.14, C["line"], preset="rightArrow")
    s.text(8.62, 1.58, 1.95, 0.58, "4 AI payload(AI 페이로드)", size=12, color=C["white"], bold=True, fill=C["gold"], align="c", anchor="mid")
    s.text(8.62, 2.25, 1.95, 0.95, "LiveFrameMessage_go_ai_server\nimage: base64 string(문자열)\ntype=frame_base64", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.shape(10.72, 2.62, 0.38, 0.14, C["line"], preset="rightArrow")
    s.text(11.25, 1.58, 1.55, 0.58, "5 Result(결과)", size=12, color=C["white"], bold=True, fill=C["green"], align="c", anchor="mid")
    s.text(11.25, 2.25, 1.55, 0.95, "LiveFrameResultMessage\ntotal_calories\nmovement_score", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.bullets(0.84, 4.0, 11.55, 1.45, [
        "image data(이미지 데이터)는 client side(클라이언트 측)에서 bytes(바이트)로 들어오고, AI server(인공지능 서버) 전달 전 base64 string(베이스64 문자열)로 변환됩니다.",
        "frame progress data(프레임 진행 데이터)는 client payload(클라이언트 페이로드)가 아니라 server-owned state(서버 소유 상태)에서 total_frames(총 프레임)와 elapsed_seconds(경과 초)를 누적합니다.",
        "AI result data(AI 결과 데이터)는 calories_burned(소모 칼로리)와 movement_score(움직임 점수)를 제공하고, server(서버)가 total_calories(총 칼로리)에 합산합니다.",
    ], size=13, fill=C["soft"])
    slides.append(s)

    s = Slide()
    title(s, "WebSocket Protocol(웹소켓 프로토콜)", "Message Contract(메시지 계약)")
    card(s, 0.82, 1.72, 3.35, 1.55, "Client -> General server(클라이언트 -> 일반 서버)", "`frame_binary` message(메시지)\nUUID, session_id, frame_index, total_frame, user_weight, image bytes(이미지 바이트).", C["blue"])
    card(s, 4.45, 1.72, 3.35, 1.55, "General -> AI server(일반 서버 -> 인공지능 서버)", "`frame_base64` message(메시지)\nimage base64(이미지 베이스64), user_weight(사용자 체중), frame metadata(프레임 메타데이터).", C["coral"])
    card(s, 8.08, 1.72, 3.35, 1.55, "AI -> Client(인공지능 -> 클라이언트)", "`frame_result` response(응답)\naccepted(수락), calories_burned(소모 칼로리), total_calories(총 칼로리), movement_score(움직임 점수).", C["green"])
    s.shape(4.18, 2.28, 0.18, 0.18, C["line"], preset="rightArrow")
    s.shape(7.82, 2.28, 0.18, 0.18, C["line"], preset="rightArrow")
    s.bullets(0.84, 4.0, 11.2, 1.42, [
        "Current mismatch(현재 불일치): demo client(데모 클라이언트)는 `type=frame` + `image_base64`를 보내지만 route(라우트)는 `frame_binary`와 binary payload(바이너리 페이로드)를 기다립니다.",
        "Fix direction(수정 방향): 하나의 protocol spec(프로토콜 명세)을 정하고 server/client/AI server(서버/클라이언트/인공지능 서버)를 같은 schema(스키마)로 맞춥니다.",
    ], size=14, fill=C["soft"])
    slides.append(s)

    s = Slide()
    title(s, "AI Bridge Flow(인공지능 브리지 흐름)", "Dance(댄스) vs Food(음식)")
    card(s, 0.82, 1.72, 5.25, 1.55, "Dance analysis(댄스 분석)", "initialize_ai_bridge(...) opens persistent WebSocket connection(지속 웹소켓 연결). Each frame request(프레임 요청)는 request_lock(요청 잠금) 안에서 send/recv(송수신)됩니다.", C["coral"])
    card(s, 6.45, 1.72, 5.25, 1.55, "Food analysis(음식 분석)", "analyze_food_with_ai(...) opens per-request WebSocket connection(요청별 웹소켓 연결). ready message(준비 메시지)를 건너뛰고 analysis payload(분석 페이로드)를 받습니다.", C["green"])
    s.text(1.1, 4.02, 2.2, 0.56, "Connection error(연결 오류)", size=13, color=C["white"], bold=True, fill=C["coral"], align="c", anchor="mid")
    s.shape(3.45, 4.18, 0.5, 0.16, C["line"], preset="rightArrow")
    s.text(4.15, 4.02, 2.35, 0.56, "close & retry(종료 후 재시도)", size=13, color=C["white"], bold=True, fill=C["teal"], align="c", anchor="mid")
    s.shape(6.65, 4.18, 0.5, 0.16, C["line"], preset="rightArrow")
    s.text(7.35, 4.02, 2.35, 0.56, "HTTP 502 response(HTTP 502 응답)", size=13, color=C["white"], bold=True, fill=C["blue"], align="c", anchor="mid")
    s.shape(9.85, 4.18, 0.5, 0.16, C["line"], preset="rightArrow")
    s.text(10.55, 4.02, 1.55, 0.56, "fallback(대체)", size=13, color=C["white"], bold=True, fill=C["green"], align="c", anchor="mid")
    s.bullets(0.84, 5.25, 11.1, 0.7, [
        "food flow(음식 흐름)는 mock fallback(모의 대체)이 있지만 dance flow(댄스 흐름)는 AI server(인공지능 서버) 연결 실패 시 user-facing error(사용자 노출 오류)가 될 가능성이 큽니다.",
    ], size=13)
    slides.append(s)

    s = Slide()
    title(s, "API Surface(엔드포인트 표면)", "Implemented Routes(구현 라우트)")
    rows = [
        ("User/Profile(사용자/프로필)", "POST /api/signup | DELETE /api/user/{uuid} | POST /api/user/{uuid} | PUT /api/Profile/{uuid}"),
        ("Home/Food(홈/식단)", "GET /api/home/{uuid} | POST /api/food/intake | GET /api/daily_food_intake/{uuid}/"),
        ("Live Session(실시간 세션)", "POST /api/live/session/start | POST /api/live/session/end | WS /ws/live/{session_id}"),
        ("Content/Record(콘텐츠/기록)", "GET /api/classes | GET /api/records | GET /api/profile/{uuid}"),
    ]
    cols = [C["blue"], C["green"], C["coral"], C["gold"]]
    y0 = 1.72
    for i, (group, routes) in enumerate(rows):
        s.text(0.78, y0, 2.55, 0.52, group, size=13, color=C["white"], bold=True, fill=cols[i], align="c", anchor="mid")
        s.text(3.52, y0, 8.55, 0.52, routes, size=11, fill=C["white"], line="DFE4E8", anchor="mid")
        y0 += 0.82
    s.bullets(0.8, 5.1, 11.4, 1.0, [
        "response_model(응답 모델)은 live session(실시간 세션)과 food intake(식단 섭취)에서 Pydantic schema(파이단틱 스키마)로 명시됩니다.",
        "class/record endpoint(클래스/기록 엔드포인트)는 현재 bool placeholder(불리언 자리표시자) response(응답)를 반환합니다.",
    ], size=14, fill=C["soft"])
    slides.append(s)

    s = Slide()
    title(s, "Food Intake Flow(식단 섭취 흐름)", "Image Upload(이미지 업로드)")
    s.text(0.82, 1.78, 2.6, 0.8, "Client(클라이언트)\nmeal image(식사 이미지)", size=15, color=C["white"], bold=True, fill=C["blue"], align="c", anchor="mid")
    s.shape(3.58, 2.08, 0.62, 0.2, C["line"], preset="rightArrow")
    s.text(4.38, 1.78, 2.65, 0.8, "General server(일반 서버)\nvalidation(검증)", size=15, color=C["white"], bold=True, fill=C["teal"], align="c", anchor="mid")
    s.shape(7.18, 2.08, 0.62, 0.2, C["line"], preset="rightArrow")
    s.text(7.98, 1.78, 2.2, 0.8, "AI server(인공지능 서버)\nfood analysis(음식 분석)", size=15, color=C["white"], bold=True, fill=C["coral"], align="c", anchor="mid")
    s.shape(10.36, 2.08, 0.62, 0.2, C["line"], preset="rightArrow")
    s.text(11.1, 1.78, 1.55, 0.8, "DailyFoodLog\ntable(테이블)", size=13, color=C["white"], bold=True, fill=C["green"], align="c", anchor="mid")
    card(s, 0.82, 3.45, 3.65, 1.4, "Validation(검증)", "SUPPORTED_IMAGE_EXTENSIONS set(집합)과 content_type(콘텐츠 타입)을 확인합니다.", C["teal"])
    card(s, 4.72, 3.45, 3.65, 1.4, "Storage(스토리지)", "DailyFoodLog bucket(버킷)에 image bytes(이미지 바이트)를 upload(업로드)합니다.", C["green"])
    card(s, 8.62, 3.45, 3.65, 1.4, "Fallback(대체)", "AI server error(인공지능 서버 오류) 시 mock analysis response(모의 분석 응답)를 사용합니다.", C["coral"])
    s.text(0.82, 5.58, 11.4, 0.55, "Output(출력): foods list(음식 목록), total_calories(총 칼로리), image_filename(이미지 파일명), source(출처), analyzed_at(분석 시각).", size=14, bold=True, fill=C["white"], line="DFE4E8", align="c")
    slides.append(s)

    s = Slide()
    title(s, "Food Payload Data Flow(식단 페이로드 데이터 흐름)", "Multipart(멀티파트) -> AI(인공지능) -> Table(테이블)")
    s.text(0.72, 1.55, 2.15, 0.54, "1 Request(요청)", size=12, color=C["white"], bold=True, fill=C["blue"], align="c", anchor="mid")
    s.text(0.72, 2.18, 2.15, 1.0, "FormData(폼 데이터)\nuuid\nday(optional)(선택)\nimage: UploadFile", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.shape(3.02, 2.57, 0.34, 0.14, C["line"], preset="rightArrow")
    s.text(3.52, 1.55, 2.15, 0.54, "2 Normalize(정규화)", size=12, color=C["white"], bold=True, fill=C["teal"], align="c", anchor="mid")
    s.text(3.52, 2.18, 2.15, 1.0, "validate image(이미지 검증)\nresolve extension(확장자 확인)\nbuild storage_path(저장 경로 생성)", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.shape(5.82, 2.57, 0.34, 0.14, C["line"], preset="rightArrow")
    s.text(6.32, 1.55, 2.15, 0.54, "3 AI request(AI 요청)", size=12, color=C["white"], bold=True, fill=C["coral"], align="c", anchor="mid")
    s.text(6.32, 2.18, 2.15, 1.0, "FoodAnalysisRequest\nuuid\nimage_base64", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.shape(8.62, 2.57, 0.34, 0.14, C["line"], preset="rightArrow")
    s.text(9.12, 1.55, 2.15, 0.54, "4 AI response(AI 응답)", size=12, color=C["white"], bold=True, fill=C["green"], align="c", anchor="mid")
    s.text(9.12, 2.18, 2.15, 1.0, "FoodIntakeAnalysisResponse\nfoods[]\ntotal_calories\nsource", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.shape(11.42, 2.57, 0.34, 0.14, C["line"], preset="rightArrow")
    s.text(11.95, 1.55, 0.72, 1.64, "DailyFoodLog\nrows(행)", size=9, color=C["white"], bold=True, fill=C["gold"], align="c", anchor="mid")
    card(s, 0.82, 4.15, 3.6, 1.05, "Storage row(스토리지 행)", "Bucket_Name=DailyFoodLog\nFile_Path=uuid/date_uuid.ext\nimage_url(public URL)(공개 URL)", C["gold"])
    card(s, 4.72, 4.15, 3.6, 1.05, "Food row(음식 행)", "UUID, Day, FoodName, Calories\none row per food item(음식 항목별 1행)", C["green"])
    card(s, 8.62, 4.15, 3.6, 1.05, "Read response(조회 응답)", "GET /api/daily_food_intake/{uuid}/\nFoods, TotalCalories, RecordCount", C["blue"])
    slides.append(s)

    s = Slide()
    title(s, "Schema & State(스키마와 상태)", "Shared Contracts(공유 계약)")
    card(s, 0.78, 1.72, 3.75, 1.55, "Pydantic schema(파이단틱 스키마)", "LiveSessionStartRequest, LiveFrameMessage, AiLiveAnalysisMessage, FoodIntakeAnalysisResponse 등이 request/response(요청/응답)를 고정합니다.", C["blue"])
    card(s, 4.8, 1.72, 3.75, 1.55, "In-memory state(메모리 상태)", "LIVE_SESSIONS dict(딕셔너리)와 ACTIVE_*_CONNECTIONS dict(딕셔너리)로 session(세션)과 socket(소켓)을 추적합니다.", C["teal"])
    card(s, 8.82, 1.72, 3.35, 1.55, "Supabase(슈파베이스)", "SignUp/Profile/DailyFoodLog table(테이블)과 Profile_Photo/DailyFoodLog bucket(버킷)을 사용합니다.", C["green"])
    s.bullets(0.82, 4.0, 11.35, 1.4, [
        "build_profile_payload(...) pulls joined profile data(프로필 데이터)와 public URL(공개 URL)을 조합합니다.",
        "calculate_daily_target_kcal(...) calculates target burn calorie(목표 소모 칼로리)를 days_remaining(남은 일수) 기준으로 제한합니다.",
        "insert_daily_food_log_rows(...) persists analyzed food item(분석된 음식 항목)을 row(행) 단위로 저장합니다.",
    ], size=14)
    slides.append(s)

    s = Slide()
    title(s, "Data Model(데이터 모델)", "Supabase(슈파베이스) Tables(테이블) & Buckets(버킷)")
    s.text(0.82, 1.72, 2.65, 0.7, "SignUp table(가입 테이블)\nUUID, Name, Email, Age", size=13, color=C["white"], bold=True, fill=C["blue"], align="c", anchor="mid")
    s.shape(3.6, 1.98, 0.48, 0.16, C["line"], preset="rightArrow")
    s.text(4.25, 1.72, 2.65, 0.7, "Profile table(프로필 테이블)\nHeight, Weight, Target", size=13, color=C["white"], bold=True, fill=C["teal"], align="c", anchor="mid")
    s.shape(6.98, 1.98, 0.48, 0.16, C["line"], preset="rightArrow")
    s.text(7.6, 1.72, 2.65, 0.7, "Profile_Photo bucket(프로필 사진 버킷)\nFilePath", size=13, color=C["white"], bold=True, fill=C["green"], align="c", anchor="mid")
    s.text(0.82, 3.22, 2.65, 0.7, "DailyFoodLog table(일일 식단 테이블)\nFoodName, Calories, Day", size=13, color=C["white"], bold=True, fill=C["coral"], align="c", anchor="mid")
    s.shape(3.6, 3.48, 0.48, 0.16, C["line"], preset="rightArrow")
    s.text(4.25, 3.22, 2.65, 0.7, "DailyFoodLog bucket(식단 이미지 버킷)\nimage file(이미지 파일)", size=13, color=C["white"], bold=True, fill=C["gold"], align="c", anchor="mid")
    s.text(7.6, 3.22, 3.0, 0.7, "Public URL(공개 URL)\nbuild_storage_public_url(...)", size=13, color=C["white"], bold=True, fill=C["ink2"], align="c", anchor="mid")
    s.bullets(0.84, 5.05, 11.0, 1.0, [
        "profile payload(프로필 페이로드)는 SignUp table(가입 테이블)과 Profile table(프로필 테이블)을 join(조인)한 뒤 bucket URL(버킷 주소)을 붙입니다.",
        "food payload(식단 페이로드)는 image storage path(이미지 저장 경로)와 food row(음식 행)를 함께 저장해 history view(기록 화면)에 재사용할 수 있습니다.",
    ], size=13, fill=C["soft"])
    slides.append(s)

    s = Slide()
    title(s, "Profile Data Flow(프로필 데이터 흐름)", "SignUp(가입) + Profile(프로필) + Bucket(버킷)")
    s.text(0.72, 1.55, 2.15, 0.55, "1 Signup request(가입 요청)", size=12, color=C["white"], bold=True, fill=C["blue"], align="c", anchor="mid")
    s.text(0.72, 2.18, 2.15, 0.9, "UserSignUp\nname/email/password/age\ncreated_at", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.shape(3.02, 2.52, 0.34, 0.14, C["line"], preset="rightArrow")
    s.text(3.52, 1.55, 2.15, 0.55, "2 SignUp table(가입 테이블)", size=12, color=C["white"], bold=True, fill=C["teal"], align="c", anchor="mid")
    s.text(3.52, 2.18, 2.15, 0.9, "UUID generated(UUID 생성)\nName, Email, Password, Age\nCreated_at", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.shape(5.82, 2.52, 0.34, 0.14, C["line"], preset="rightArrow")
    s.text(6.32, 1.55, 2.15, 0.55, "3 Profile update(프로필 수정)", size=12, color=C["white"], bold=True, fill=C["coral"], align="c", anchor="mid")
    s.text(6.32, 2.18, 2.15, 0.9, "UserProfileUpdate\nheight/weight/target\nimage UploadFile(이미지 파일)", size=10, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    s.shape(8.62, 2.52, 0.34, 0.14, C["line"], preset="rightArrow")
    s.text(9.12, 1.55, 2.15, 0.55, "4 Split update(분리 업데이트)", size=12, color=C["white"], bold=True, fill=C["green"], align="c", anchor="mid")
    s.text(9.12, 2.18, 2.15, 0.9, "SYNCED_SIGNUP_COLUMNS\nSYNCED_PROFILE_COLUMNS\nBucket_Profile_Photo/FilePath", size=9, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
    card(s, 0.82, 4.0, 3.4, 1.08, "Read profile(프로필 조회)", "get_profile_record(...) joins(조인) Profile table(프로필 테이블) + SignUp table(가입 테이블).", C["blue"])
    card(s, 4.52, 4.0, 3.4, 1.08, "Build URL(URL 생성)", "build_storage_public_url(...) turns bucket/path(버킷/경로) into profile_image_url(프로필 이미지 주소).", C["green"])
    card(s, 8.22, 4.0, 3.4, 1.08, "Response shape(응답 형태)", "build_profile_payload(...) returns uuid, name, email, age, height, weight, target fields(목표 필드).", C["teal"])
    slides.append(s)

    s = Slide()
    title(s, "Core Metrics(핵심 지표)", "Calorie(칼로리) & Session(세션)")
    card(s, 0.78, 1.72, 3.65, 1.45, "Daily target(일일 목표)", "current weight(현재 체중), target weight(목표 체중), target day(목표일), kcal_per_kg(kg당 칼로리)를 사용해 daily burn target(일일 소모 목표)을 계산합니다.", C["green"])
    card(s, 4.72, 1.72, 3.65, 1.45, "Food total(식단 합계)", "DailyFoodLog table(테이블)의 Calories(칼로리)를 합산해 TotalCalories(총 칼로리)와 RecordCount(기록 수)를 반환합니다.", C["coral"])
    card(s, 8.66, 1.72, 3.35, 1.45, "Live session(실시간 세션)", "frame gap(프레임 간격), elapsed seconds(경과 초), total frames(총 프레임), total calories(총 칼로리)를 누적합니다.", C["teal"])
    s.bullets(0.82, 4.05, 11.2, 1.35, [
        "movement_score(움직임 점수)와 calories_burned(소모 칼로리)는 AI server response(인공지능 서버 응답)에 의존합니다.",
        "현재 session store(세션 저장소)는 memory dict(메모리 딕셔너리)이므로 production(운영)에서는 Redis(레디스) 같은 shared store(공유 저장소)가 후보입니다.",
        "maximum_daily_kcal(일일 최대 칼로리) cap(상한)이 있어 비현실적인 목표값을 제한합니다.",
    ], size=14)
    slides.append(s)

    s = Slide()
    title(s, "AI Analysis Assets(인공지능 분석 자산)", "Prototype Evidence(프로토타입 근거)")
    s.pic(0.82, 1.68, 3.2, 3.2)
    card(s, 4.35, 1.68, 3.6, 1.28, "kcal_cal.py", "OpenCV camera frame(오픈CV 카메라 프레임)과 MediaPipe pose landmarks(미디어파이프 포즈 랜드마크)로 movement score(움직임 점수)를 계산합니다.", C["coral"])
    card(s, 8.25, 1.68, 3.6, 1.28, "rocognize_gif.py", "test.gif file(파일)을 frame(프레임)으로 읽고 pose detection visualization(포즈 감지 시각화)을 보여줍니다.", C["gold"])
    card(s, 4.35, 3.34, 3.6, 1.28, "live_session_client_test.py", "HTTP request(HTTP 요청)로 session(세션)을 열고 WebSocket(웹소켓)으로 frame stream(프레임 스트림)을 보내는 local test client(로컬 테스트 클라이언트)입니다.", C["blue"])
    card(s, 8.25, 3.34, 3.6, 1.28, "AI bridge(인공지능 브리지)", "dance analysis(댄스 분석)는 persistent connection(지속 연결), food analysis(음식 분석)는 per-request connection(요청별 연결) 구조입니다.", C["teal"])
    s.text(0.9, 5.55, 11.1, 0.62, "Prototype code(프로토타입 코드)는 model asset file(모델 자산 파일) pose_landmarker_lite.task를 기대합니다.", size=14, bold=True, align="c", fill=C["soft_gold"])
    slides.append(s)

    s = Slide()
    title(s, "Quality Controls(품질 제어)", "Validation(검증), Error(오류), Cleanup(정리)")
    card(s, 0.78, 1.72, 3.55, 1.35, "Input validation(입력 검증)", "Pydantic schema(파이단틱 스키마), image extension(이미지 확장자), content_type(콘텐츠 타입), session status(세션 상태).", C["blue"])
    card(s, 4.62, 1.72, 3.55, 1.35, "Upstream error(상위 오류)", "Supabase error(슈파베이스 오류)를 HTTP 503/500 response(응답)로 변환하고 AI error(AI 오류)는 HTTP 502 response(응답)로 변환합니다.", C["coral"])
    card(s, 8.46, 1.72, 3.55, 1.35, "Socket cleanup(소켓 정리)", "session end(세션 종료), WebSocketDisconnect(웹소켓 연결 해제), AI close(AI 종료) path(경로)를 둡니다.", C["green"])
    s.bullets(0.82, 3.85, 11.2, 1.7, [
        "request_lock(요청 잠금)은 per-session(세션별) AI message exchange(AI 메시지 교환)를 직렬화합니다.",
        "food analysis fallback(식단 분석 대체)은 AI server unavailable(인공지능 서버 사용 불가) 상황에서도 user flow(사용자 흐름)를 유지합니다.",
        "private network access header(사설 네트워크 접근 헤더)를 처리해 local device test(로컬 기기 테스트)에 대응합니다.",
    ], size=14)
    slides.append(s)

    s = Slide()
    title(s, "Test Plan(테스트 계획)", "What To Verify(검증할 것)")
    checks = [
        ("API smoke test(API 스모크 테스트)", "signup/profile/home/food endpoint(엔드포인트) response schema(응답 스키마) 확인", C["blue"]),
        ("WebSocket integration(웹소켓 통합)", "start session(세션 시작) -> connect(연결) -> frame(프레임) -> result(결과) -> end(종료)", C["coral"]),
        ("Supabase path(슈파베이스 경로)", "table insert(테이블 삽입), storage upload(스토리지 업로드), public URL(공개 URL)", C["green"]),
        ("AI fallback(AI 대체)", "food AI timeout(음식 AI 시간 제한), invalid payload(잘못된 페이로드), mock response(모의 응답)", C["gold"]),
        ("Presentation QA(발표 자료 QA)", "PPTX XML parse(PPTX XML 파싱), slide count(슬라이드 수), media embed(미디어 포함), text fit(텍스트 맞춤)", C["teal"]),
    ]
    y0 = 1.62
    for head, body, color in checks:
        s.text(0.82, y0, 3.3, 0.48, head, size=12, color=C["white"], bold=True, fill=color, anchor="mid")
        s.text(4.35, y0, 7.45, 0.48, body, size=12, fill=C["white"], line="DFE4E8", anchor="mid")
        y0 += 0.78
    s.text(0.86, 5.88, 10.9, 0.38, "Recommended(추천): protocol fixture(프로토콜 고정 데이터)를 먼저 만들면 client/server/AI server(클라이언트/서버/인공지능 서버) 계약이 흔들리지 않습니다.", size=12, color=C["sub"], fill=C["soft"], align="c")
    slides.append(s)

    s = Slide()
    title(s, "Risks & Gaps(리스크와 공백)", "Current Findings(현재 확인)")
    s.bullets(0.82, 1.74, 11.4, 4.35, [
        "README(리드미)가 `servers/ai_server/` path(경로)를 설명하지만 current repository(현재 저장소)에는 해당 folder(폴더)가 보이지 않습니다.",
        "build_ai_dance_ws_url(...) uses configured AI_DANCE_WS_PATH(인공지능 댄스 웹소켓 경로)를 붙이지 않아 AI WebSocket URL(AI 웹소켓 URL) 형식 점검이 필요합니다.",
        "live_session_client_test.py payload(페이로드)는 `type=frame` + `image_base64`이고 route(라우트)는 `type=frame_binary` + binary message(바이너리 메시지)를 기대해 protocol mismatch(프로토콜 불일치)가 있습니다.",
        "session state(세션 상태)가 memory(메모리)에 있어 multi-process(멀티 프로세스) 또는 restart(재시작) 상황에서 persistence(영속성)가 없습니다.",
        "security(보안), auth(인증), rate limit(요청 제한), CORS policy(CORS 정책)는 production(운영) 기준으로 재정의가 필요합니다.",
        "일부 Korean comment(한국어 주석)가 mojibake(문자 깨짐) 상태라 maintenance(유지보수) 가독성이 떨어집니다.",
    ])
    slides.append(s)

    s = Slide()
    title(s, "Improvement Plan(개선 계획)", "Fix Order(수정 순서)")
    phases = [
        ("Phase 1(1단계)", "Protocol alignment(프로토콜 정렬)", "`frame_binary` vs `frame` mismatch(불일치) 제거\nschema fixture(스키마 고정 데이터) 작성", C["coral"]),
        ("Phase 2(2단계)", "AI path cleanup(AI 경로 정리)", "AI_DANCE_WS_PATH(인공지능 댄스 경로) 사용\nAI_HOST value(AI 호스트 값) 점검", C["teal"]),
        ("Phase 3(3단계)", "Persistence(영속성)", "LIVE_SESSIONS dict(세션 딕셔너리) 대체\nRedis(레디스) 또는 database state(데이터베이스 상태)", C["green"]),
        ("Phase 4(4단계)", "Production guardrail(운영 안전장치)", "auth(인증), rate limit(요청 제한), structured log(구조화 로그), health check(헬스 체크)", C["blue"]),
    ]
    x0 = 0.7
    for phase, head, body, color in phases:
        s.text(x0, 1.78, 2.85, 0.42, phase, size=12, color=C["white"], bold=True, fill=color, align="c", anchor="mid")
        s.text(x0, 2.35, 2.85, 0.42, head, size=13, bold=True, fill=C["white"], line="DFE4E8", align="c", anchor="mid")
        s.text(x0, 2.95, 2.85, 1.18, body, size=11, color=C["sub"], fill=C["white"], line="DFE4E8", align="c", anchor="mid")
        if x0 < 9.0:
            s.shape(x0 + 2.94, 3.1, 0.34, 0.16, C["line"], preset="rightArrow")
        x0 += 3.05
    s.bullets(0.84, 5.2, 11.1, 0.8, [
        "이 순서는 demo reliability(데모 신뢰성)를 먼저 올리고, 이후 production readiness(운영 준비도)를 확장하는 흐름입니다.",
    ], size=13, fill=C["soft"])
    slides.append(s)

    s = Slide()
    title(s, "Roadmap(로드맵)", "Recommended Next Steps(추천 다음 단계)")
    roadmap = [
        ("1", "MVP hardening(MVP 안정화)", "protocol(프로토콜) 통일, AI URL(AI 주소) 수정, README(리드미) 최신화", C["coral"]),
        ("2", "Data contract(데이터 계약)", "schema test(스키마 테스트), API examples(API 예시), error format(오류 형식)", C["blue"]),
        ("3", "AI integration(인공지능 연동)", "dance/food server path(댄스/음식 서버 경로) 확정, timeout(시간 제한), retry(재시도)", C["teal"]),
        ("4", "Production(운영)", "auth(인증), deployment(배포), observability(관측성), persistent session store(영속 세션 저장소)", C["green"]),
    ]
    y0 = 1.7
    for n, head, body, color in roadmap:
        s.text(0.86, y0 + 0.07, 0.5, 0.5, n, size=17, color=C["white"], bold=True, fill=color, align="c", anchor="mid")
        s.text(1.58, y0, 3.15, 0.62, head, size=16, bold=True, anchor="mid")
        s.text(4.9, y0, 6.95, 0.62, body, size=14, color=C["sub"], fill=C["white"], line="DFE4E8", anchor="mid")
        y0 += 1.05
    s.text(0.86, 6.12, 11.0, 0.46, "Recommendation(추천): first sprint(첫 스프린트)는 protocol mismatch(프로토콜 불일치)와 AI bridge URL(AI 브리지 주소)을 먼저 닫는 것이 가장 효과적입니다.", size=14, color=C["white"], bold=True, fill=C["ink2"], align="c")
    slides.append(s)

    s = Slide()
    title(s, "Demo Script(시연 진행안)", "Run & Present(실행과 발표)")
    s.bullets(0.84, 1.74, 5.55, 4.45, [
        "1. `uv run python main.py` command(명령어)로 general server(일반 서버)를 실행합니다.",
        "2. Swagger UI(스웨거 UI)에서 signup/profile/home endpoint(엔드포인트)를 확인합니다.",
        "3. food intake upload(식단 섭취 업로드) flow(흐름)를 설명하고 Supabase storage(슈파베이스 스토리지)를 연결합니다.",
        "4. live session start request(실시간 세션 시작 요청)와 ws_url response(응답)를 보여줍니다.",
        "5. test.gif asset(자산)으로 realtime frame streaming(실시간 프레임 스트리밍) 방향성을 소개합니다.",
    ])
    s.text(7.0, 1.75, 4.9, 4.4, "Speaker note(발표자 메모)\n\n현재 AI server(인공지능 서버) repository(저장소) 위치가 불명확하므로, demo(시연)는 general server(일반 서버)의 app-facing API(앱 연동 인터페이스)와 bridge contract(브리지 계약)를 중심으로 진행하는 것이 안전합니다.", size=16, color=C["white"], fill=C["ink2"])
    slides.append(s)

    s = Slide(C["ink"])
    s.shape(0.78, 0.72, 11.8, 5.65, C["ink2"], C["line"])
    s.text(1.16, 1.18, 10.9, 0.48, "Closing Message(마무리 메시지)", size=16, color=C["gold"], bold=True, align="c")
    s.text(1.18, 2.05, 10.8, 1.08, "Dance Diet Server는 mobile client(모바일 클라이언트), AI analysis(인공지능 분석), Supabase data layer(슈파베이스 데이터 계층)를 잇는 backend hub(백엔드 허브)입니다.", size=28, color=C["white"], bold=True, align="c")
    s.text(1.58, 4.05, 10.05, 0.92, "가장 큰 next action(다음 조치)은 live WebSocket protocol(실시간 웹소켓 프로토콜)과 AI server path(인공지능 서버 경로)를 하나로 맞추는 것입니다.", size=18, color="D6E0E6", align="c")
    pill(s, 4.2, 5.55, 1.52, "MVP(최소 기능 제품)", C["coral"])
    pill(s, 5.95, 5.55, 1.65, "AI(인공지능)", C["teal"])
    pill(s, 7.84, 5.55, 1.72, "Production(운영)", C["green"])
    slides.append(s)

    total = len(slides)
    for i, slide in enumerate(slides, 1):
        if i != 1:
            footer(slide, i, total)
    return slides


def types_xml(n: int) -> str:
    slide_parts = "\n".join(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1, n + 1))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="gif" ContentType="image/gif"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
{slide_parts}
</Types>"""


def root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""


def app_xml(n: int) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<Application>Codex</Application><PresentationFormat>On-screen Show (16:9)</PresentationFormat><Slides>{n}</Slides><Notes>0</Notes><HiddenSlides>0</HiddenSlides><MMClips>0</MMClips><ScaleCrop>false</ScaleCrop>
<HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Theme</vt:lpstr></vt:variant><vt:variant><vt:i4>1</vt:i4></vt:variant></vt:vector></HeadingPairs>
<TitlesOfParts><vt:vector size="1" baseType="lpstr"><vt:lpstr>Dance Diet Server</vt:lpstr></vt:vector></TitlesOfParts><Company/><LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged><AppVersion>16.0000</AppVersion>
</Properties>"""


def core_xml() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>Dance Diet Server Project Overview</dc:title><dc:subject>FastAPI backend project presentation</dc:subject><dc:creator>Codex</dc:creator><cp:keywords>FastAPI WebSocket Supabase AI</cp:keywords><dc:description>Project overview deck generated from repository inspection.</dc:description><cp:lastModifiedBy>Codex</cp:lastModifiedBy>
<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>"""


def pres_xml(n: int) -> str:
    ids = "\n".join(f'<p:sldId id="{256 + i}" r:id="rId{i + 1}"/>' for i in range(1, n + 1))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>{ids}</p:sldIdLst>
<p:sldSz cx="{SW}" cy="{SH}" type="wide"/><p:notesSz cx="6858000" cy="9144000"/>
<p:defaultTextStyle><a:defPPr><a:defRPr lang="ko-KR"><a:latin typeface="Aptos"/><a:ea typeface="Malgun Gothic"/><a:cs typeface="Malgun Gothic"/></a:defRPr></a:defPPr></p:defaultTextStyle>
</p:presentation>"""


def pres_rels(n: int) -> str:
    rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
    rels += [f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1, n + 1)]
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{"".join(rels)}</Relationships>'


def master_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
<p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz="3200"><a:latin typeface="Aptos Display"/><a:ea typeface="Malgun Gothic"/></a:defRPr></a:lvl1pPr></p:titleStyle><p:bodyStyle><a:lvl1pPr><a:defRPr sz="1800"><a:latin typeface="Aptos"/><a:ea typeface="Malgun Gothic"/></a:defRPr></a:lvl1pPr></p:bodyStyle><p:otherStyle><a:lvl1pPr><a:defRPr sz="1800"><a:latin typeface="Aptos"/><a:ea typeface="Malgun Gothic"/></a:defRPr></a:lvl1pPr></p:otherStyle></p:txStyles>
</p:sldMaster>"""


def theme_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="{NS_A}" name="Dance Diet Theme"><a:themeElements><a:clrScheme name="DanceDiet">
<a:dk1><a:srgbClr val="{C['ink']}"/></a:dk1><a:lt1><a:srgbClr val="{C['paper']}"/></a:lt1><a:dk2><a:srgbClr val="{C['ink2']}"/></a:dk2><a:lt2><a:srgbClr val="FFFFFF"/></a:lt2>
<a:accent1><a:srgbClr val="{C['teal']}"/></a:accent1><a:accent2><a:srgbClr val="{C['coral']}"/></a:accent2><a:accent3><a:srgbClr val="{C['green']}"/></a:accent3><a:accent4><a:srgbClr val="{C['gold']}"/></a:accent4><a:accent5><a:srgbClr val="{C['blue']}"/></a:accent5><a:accent6><a:srgbClr val="7A5AF8"/></a:accent6><a:hlink><a:srgbClr val="{C['blue']}"/></a:hlink><a:folHlink><a:srgbClr val="7A5AF8"/></a:folHlink>
</a:clrScheme><a:fontScheme name="DanceDietFonts"><a:majorFont><a:latin typeface="Aptos Display"/><a:ea typeface="Malgun Gothic"/><a:cs typeface="Malgun Gothic"/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/><a:ea typeface="Malgun Gothic"/><a:cs typeface="Malgun Gothic"/></a:minorFont></a:fontScheme>
<a:fmtScheme name="DanceDietFormat"><a:fillStyleLst><a:solidFill><a:schemeClr val="accent1"/></a:solidFill><a:solidFill><a:schemeClr val="accent2"/></a:solidFill><a:solidFill><a:schemeClr val="accent3"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="12700"><a:solidFill><a:schemeClr val="accent1"/></a:solidFill></a:ln><a:ln w="19050"><a:solidFill><a:schemeClr val="accent2"/></a:solidFill></a:ln><a:ln w="25400"><a:solidFill><a:schemeClr val="accent3"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="lt1"/></a:solidFill><a:solidFill><a:schemeClr val="lt2"/></a:solidFill><a:solidFill><a:schemeClr val="dk1"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
</a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>"""


LAYOUT = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'
MASTER_RELS = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>'
LAYOUT_RELS = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>'


def write_pptx() -> Path:
    slides = build_slides()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    with ZipFile(OUT, "w", ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types_xml(len(slides)))
        z.writestr("_rels/.rels", root_rels())
        z.writestr("docProps/app.xml", app_xml(len(slides)))
        z.writestr("docProps/core.xml", core_xml())
        z.writestr("ppt/presentation.xml", pres_xml(len(slides)))
        z.writestr("ppt/_rels/presentation.xml.rels", pres_rels(len(slides)))
        z.writestr("ppt/theme/theme1.xml", theme_xml())
        z.writestr("ppt/slideMasters/slideMaster1.xml", master_xml())
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", MASTER_RELS)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", LAYOUT)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", LAYOUT_RELS)
        if GIF.exists():
            z.write(GIF, "ppt/media/test.gif")
        for i, slide in enumerate(slides, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", slide.xml())
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", slide.rels_xml())
    return OUT.resolve()


if __name__ == "__main__":
    print(write_pptx())
