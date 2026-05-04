from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
VENDOR = ROOT / "docs" / "_vendor_pdf_runtime"
PROJECT_SITE_PACKAGES = ROOT / ".venv" / "Lib" / "site-packages"
if VENDOR.exists():
    for package_dir in ("PIL", "fitz", "pypdf", "pymupdf"):
        package_path = VENDOR / package_dir
        if package_path.exists():
            sys.path.insert(0, str(package_path))
    sys.path.insert(0, str(VENDOR))
if PROJECT_SITE_PACKAGES.exists():
    sys.path.append(str(PROJECT_SITE_PACKAGES))

from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


PDF_PATH = OUT_DIR / "dance_diet_auto_presentation.pdf"
HTML_PATH = OUT_DIR / "index.html"
PAGES_DIR = OUT_DIR / "rendered_pages"
FONT = "Malgun"
FONT_BOLD = "MalgunBold"
W, H = 960, 540

PALETTE = {
    "ink": "#111820",
    "ink2": "#17212B",
    "paper": "#F6F3EC",
    "white": "#FFFFFF",
    "muted": "#AEB8BF",
    "line": "#32404B",
    "text": "#18222D",
    "sub": "#44525D",
    "teal": "#2AA7A5",
    "green": "#73B66B",
    "coral": "#F26957",
    "gold": "#E5B94B",
    "blue": "#3B7DDD",
    "soft": "#EEF3F4",
    "soft_gold": "#F7EBC3",
}


def c(hex_color: str) -> colors.Color:
    return colors.HexColor(hex_color)


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont(FONT, r"C:\Windows\Fonts\malgun.ttf"))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, r"C:\Windows\Fonts\malgunbd.ttf"))


def text_width(text: str, size: int, bold: bool = False) -> float:
    return pdfmetrics.stringWidth(text, FONT_BOLD if bold else FONT, size)


def wrap(text: str, size: int, width: float, bold: bool = False) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if text_width(trial, size, bold) <= width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def draw_text_box(
    p: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    size: int = 16,
    color: str = PALETTE["text"],
    bold: bool = False,
    align: str = "left",
    valign: str = "top",
    fill: str | None = None,
    stroke: str | None = None,
    radius: float = 8,
) -> None:
    if fill:
        p.setFillColor(c(fill))
        p.setStrokeColor(c(stroke or fill))
        p.roundRect(x, y, w, h, radius, fill=1, stroke=1 if stroke else 0)
    elif stroke:
        p.setStrokeColor(c(stroke))
        p.roundRect(x, y, w, h, radius, fill=0, stroke=1)

    font = FONT_BOLD if bold else FONT
    p.setFont(font, size)
    p.setFillColor(c(color))
    inner = 12
    max_w = w - inner * 2
    lines = wrap(text, size, max_w, bold)
    leading = size * 1.25
    total_h = len(lines) * leading
    if valign == "mid":
        start_y = y + h / 2 + total_h / 2 - size
    else:
        start_y = y + h - inner - size
    for idx, line in enumerate(lines):
        line_y = start_y - idx * leading
        if line_y < y + inner - size:
            break
        if align == "center":
            p.drawCentredString(x + w / 2, line_y, line)
        elif align == "right":
            p.drawRightString(x + w - inner, line_y, line)
        else:
            p.drawString(x + inner, line_y, line)


def title(p: canvas.Canvas, heading: str, eyebrow: str = "", *, dark: bool = False) -> None:
    draw_text_box(p, 42, 472, 400, 20, eyebrow, size=10, color=PALETTE["gold"] if dark else PALETTE["line"], bold=True)
    draw_text_box(p, 42, 424, 710, 42, heading, size=25, color=PALETTE["white"] if dark else PALETTE["text"], bold=True)
    p.setFillColor(c(PALETTE["coral"]))
    p.rect(46, 404, 72, 4, fill=1, stroke=0)
    p.setFillColor(c(PALETTE["teal"]))
    p.rect(128, 404, 54, 4, fill=1, stroke=0)
    p.setFillColor(c(PALETTE["gold"]))
    p.rect(194, 404, 34, 4, fill=1, stroke=0)


def card(p: canvas.Canvas, x: float, y: float, w: float, h: float, head: str, body: str, accent: str) -> None:
    p.setFillColor(c(PALETTE["white"]))
    p.setStrokeColor(c("#DFE4E8"))
    p.roundRect(x, y, w, h, 8, fill=1, stroke=1)
    p.setFillColor(c(accent))
    p.roundRect(x, y, 8, h, 4, fill=1, stroke=0)
    draw_text_box(p, x + 12, y + h - 42, w - 24, 32, head, size=10, bold=True)
    draw_text_box(p, x + 12, y + 8, w - 24, h - 46, body, size=9, color=PALETTE["sub"])


def arrow(p: canvas.Canvas, x: float, y: float, w: float = 34, color: str = PALETTE["line"]) -> None:
    p.setFillColor(c(color))
    p.rect(x, y + 6, w - 12, 4, fill=1, stroke=0)
    path = p.beginPath()
    path.moveTo(x + w - 12, y)
    path.lineTo(x + w, y + 8)
    path.lineTo(x + w - 12, y + 16)
    path.close()
    p.drawPath(path, fill=1, stroke=0)


def bullets(p: canvas.Canvas, x: float, y: float, w: float, h: float, items: list[str], *, size: int = 12) -> None:
    p.setFillColor(c(PALETTE["white"]))
    p.setStrokeColor(c("#DFE4E8"))
    p.roundRect(x, y, w, h, 8, fill=1, stroke=1)
    current_y = y + h - 24
    p.setFont(FONT, size)
    p.setFillColor(c(PALETTE["text"]))
    for item in items:
        lines = wrap(item, size, w - 52)
        p.drawString(x + 18, current_y, "•")
        for i, line in enumerate(lines):
            p.drawString(x + 36, current_y - i * size * 1.25, line)
        current_y -= max(1, len(lines)) * size * 1.25 + 8
        if current_y < y + 16:
            break


def slide_bg(p: canvas.Canvas, bg: str = PALETTE["paper"]) -> None:
    p.setFillColor(c(bg))
    p.rect(0, 0, W, H, fill=1, stroke=0)


SLIDES = [
    {
        "title": "Dance Diet Server 발표",
        "script": "안녕하세요. 지금부터 Dance Diet Server project(프로젝트) 발표를 시작하겠습니다. 이 발표는 project overview(프로젝트 개요), tech stack(기술 스택), system architecture(시스템 아키텍처), feature description(핵심 기능 설명), demo video(시연 영상), database diagram(DB 구성도), future plan(향후 개발 계획) 순서로 진행됩니다.",
        "kind": "cover",
    },
    {
        "title": "목차",
        "script": "먼저 목차입니다. 프로젝트 개요는 팀에서 최종 내용을 채울 수 있도록 mockup(목업) 형태로 두었습니다. 이어서 기술 스택, 시스템 아키텍처, 시스템 구성도, 핵심 기능, 시연 영상 placeholder(자리표시자), DB 구성도, 전체 개발 내용 및 향후 개발 계획 순서로 설명합니다.",
        "kind": "agenda_requested",
    },
    {
        "title": "프로젝트 개요",
        "script": "프로젝트 개요 부분은 사용자가 직접 채울 수 있도록 mockup(목업)으로 구성했습니다. 현재는 Dance Diet Server가 dance workout(댄스 운동), food intake(식단 섭취), calorie tracking(칼로리 추적)을 연결하는 backend service(백엔드 서비스)라는 방향만 표시합니다.",
        "kind": "project_overview_mock",
    },
    {
        "title": "기술 스택",
        "script": "기술 스택은 FastAPI(패스트API), WebSocket(웹소켓), Pydantic(파이단틱), Supabase(슈파베이스), OpenCV(오픈CV), MediaPipe(미디어파이프), uv(유브이), Python(파이썬)으로 구성됩니다. 각 기술은 API(응용 프로그램 인터페이스), realtime communication(실시간 통신), data validation(데이터 검증), storage(스토리지), AI prototype(인공지능 프로토타입) 역할을 맡습니다.",
        "kind": "tech_stack_requested",
    },
    {
        "title": "시스템 아키텍처",
        "script": "시스템 아키텍처는 mobile client(모바일 클라이언트), general server(일반 서버), AI server(인공지능 서버), Supabase(슈파베이스)로 나뉩니다. client(클라이언트)는 REST request(REST 요청)와 WebSocket message(웹소켓 메시지)를 보내고, general server(일반 서버)는 data processing(데이터 처리)과 AI bridge(인공지능 브리지)를 담당합니다.",
        "kind": "system_architecture_requested",
    },
    {
        "title": "시스템 구성도",
        "script": "시스템 구성도는 data flow(데이터 흐름) 기준입니다. profile data(프로필 데이터)는 SignUp table(가입 테이블)과 Profile table(프로필 테이블)로 흐르고, live frame data(실시간 프레임 데이터)는 WebSocket(웹소켓)을 거쳐 AI server(인공지능 서버)로 전달됩니다. food image data(식단 이미지 데이터)는 storage bucket(스토리지 버킷)과 DailyFoodLog table(테이블)에 저장됩니다.",
        "kind": "system_diagram_requested",
    },
    {
        "title": "핵심 기능 설명",
        "script": "핵심 기능은 회원 및 프로필 관리, 실시간 댄스 세션, 식단 이미지 분석, 홈 화면 calorie summary(칼로리 요약), 기록 조회입니다. 현재 발표 자료에서는 각 기능이 어떤 endpoint(엔드포인트), schema(스키마), table(테이블)을 사용하는지 한눈에 보이도록 정리했습니다.",
        "kind": "core_features_requested",
    },
    {
        "title": "시연 영상",
        "script": "시연 영상 slide(슬라이드)는 팀에서 촬영한 video(영상)를 삽입할 수 있도록 placeholder(자리표시자)만 만들었습니다. 영상은 live session(실시간 세션) 시작, frame streaming(프레임 스트리밍), food intake upload(식단 업로드), profile view(프로필 화면) 순서로 구성하면 자연스럽습니다.",
        "kind": "demo_video_placeholder",
    },
    {
        "title": "DB 구성도",
        "script": "DB 구성도입니다. Supabase(슈파베이스) dashboard(대시보드)는 현재 401 Unauthorized(권한 없음)라서 직접 schema introspection(스키마 조회)은 되지 않았습니다. 대신 codebase(코드베이스)에서 실제로 사용하는 table(테이블), PK(기본키), FK(외래키), cardinality(관계 수)를 기준으로 ERD(Entity Relationship Diagram, 개체 관계도)를 구성했습니다. Storage bucket(스토리지 버킷)은 relational table(관계형 테이블)이 아니므로 dashed line(점선)으로 분리해 표시합니다.",
        "kind": "db_diagram_placeholder",
    },
    {
        "title": "전체 개발 내용 및 향후 개발 계획",
        "script": "전체 개발 내용 및 향후 개발 계획 부분은 팀에서 최종 내용을 채울 수 있도록 placeholder(자리표시자)로 구성했습니다. 현재는 completed work(완료 내용), current issue(현재 이슈), next sprint(다음 스프린트), future expansion(향후 확장) 영역만 보여줍니다.",
        "kind": "dev_plan_placeholder",
    },
    {
        "title": "마무리",
        "script": "마무리입니다. 이 발표 자료는 팀이 실제 내용, 시연 영상, Supabase database diagram(DB 구성도), 향후 개발 계획을 추가하기 쉽도록 구조를 먼저 잡아둔 version(버전)입니다. 다음 단계는 Supabase(슈파베이스) schema(스키마) 확인 후 DB 구성도(DB diagram)를 실제 구조로 교체하는 것입니다.",
        "kind": "close",
    },
]


def draw_cover(p: canvas.Canvas, slide: dict[str, str]) -> None:
    slide_bg(p, PALETTE["ink"])
    p.setFillColor(c(PALETTE["ink2"]))
    p.rect(615, 0, 345, 540, fill=1, stroke=0)
    draw_text_box(p, 54, 432, 430, 24, "PDF(PDF) AUTOMATIC PRESENTATION(자동 발표)", size=11, color=PALETTE["gold"], bold=True)
    draw_text_box(p, 54, 305, 560, 90, "Dance Diet Server", size=42, color=PALETTE["white"], bold=True)
    draw_text_box(p, 58, 220, 510, 72, "FastAPI(패스트API), WebSocket(웹소켓), AI bridge(인공지능 브리지), Supabase(슈파베이스)를 연결하는 backend(백엔드) overview(개요).", size=16, color="#D8E1E6")
    for x, label, col in [(58, "FastAPI(패스트API)", "teal"), (210, "WebSocket(웹소켓)", "coral"), (375, "Supabase(슈파베이스)", "green")]:
        draw_text_box(p, x, 160, 140, 30, label, size=10, color=PALETTE["white"], bold=True, align="center", valign="mid", fill=PALETTE[col])
    draw_text_box(p, 650, 180, 250, 115, "PDF(PDF) page image(페이지 이미지)를 넘기고 browser TTS(브라우저 음성 합성)가 speaker note(발표자 노트)를 읽습니다.", size=17, color=PALETTE["white"], align="center", valign="mid")


def draw_agenda(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "Agenda(목차)", "Automatic PT(자동 발표) 구성")
    rows = [
        ("01", "Product Context(제품 맥락)", "goal(목표), user value(사용자 가치), repository evidence(저장소 근거)"),
        ("02", "Data Definition(데이터 정의)", "Pydantic schema(파이단틱 스키마), table(테이블), bucket(버킷)"),
        ("03", "Data Flow(데이터 흐름)", "live frame(실시간 프레임), food image(식단 이미지), profile update(프로필 수정)"),
        ("04", "Roadmap(로드맵)", "risk(리스크), fix order(수정 순서), demo plan(시연 계획)"),
    ]
    y = 330
    for num, head, body in rows:
        draw_text_box(p, 70, y, 64, 38, num, size=15, color=PALETTE["white"], bold=True, fill=PALETTE["teal"], align="center", valign="mid")
        draw_text_box(p, 155, y, 245, 38, head, size=15, bold=True, valign="mid")
        draw_text_box(p, 420, y, 420, 38, body, size=12, fill=PALETTE["white"], stroke="#DFE4E8", valign="mid")
        y -= 68


def draw_goal(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "Product Goal(제품 목표)", "Why this server(서버) exists")
    draw_text_box(p, 62, 315, 410, 72, "dance workout(댄스 운동), food intake(식단 섭취), calorie target(칼로리 목표)을 하나의 daily loop(일일 루프)로 연결합니다.", size=22, bold=True)
    card(p, 60, 160, 250, 105, "Dance tracking(댄스 추적)", "camera frame(카메라 프레임)을 WebSocket(웹소켓)으로 보내 movement score(움직임 점수)와 burned calorie(소모 칼로리)를 받습니다.", PALETTE["coral"])
    card(p, 355, 160, 250, 105, "Food logging(식단 기록)", "meal image(식사 이미지)를 upload(업로드)하고 AI analysis(인공지능 분석) 결과를 DailyFoodLog table(테이블)에 저장합니다.", PALETTE["green"])
    card(p, 650, 160, 250, 105, "Mobile home(모바일 홈)", "home/profile/record/class tab(탭)에 필요한 payload(페이로드)를 REST endpoint(엔드포인트)로 제공합니다.", PALETTE["teal"])


def draw_schema(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "Data Definition Map(데이터 정의 지도)", "Schema(스키마)와 저장 대상")
    boxes = [
        (55, 315, "UserSignUp(사용자 가입)", "name, email, password, age\n-> SignUp table(가입 테이블)", PALETTE["blue"]),
        (282, 315, "UserProfileUpdate\n(프로필 수정)", "height, weight, target_weight\n-> Profile table(프로필 테이블)", PALETTE["teal"]),
        (509, 315, "LiveFrameMessage\n(실시간 프레임)", "image bytes(이미지 바이트), user_weight\n-> AI payload(AI 페이로드)", PALETTE["coral"]),
        (736, 315, "LiveFrameResult\nMessage(프레임 결과)", "total_calories, movement_score\n-> client response\n(클라이언트 응답)", PALETTE["green"]),
        (55, 170, "FoodAnalysis\nRequest(음식 분석 요청)", "uuid, image_base64\n-> AI food server\n(AI 음식 서버)", PALETTE["coral"]),
        (282, 170, "FoodIntakeAnalysis\nResponse(식단 분석 응답)", "foods[], total_calories, source\n-> DailyFoodLog table(테이블)", PALETTE["green"]),
        (509, 170, "FoodRecord\nResponse(식단 기록 응답)", "Foods, TotalCalories, RecordCount\n-> record view(기록 화면)", PALETTE["gold"]),
        (736, 170, "LIVE_SESSIONS\nstate(세션 상태)", "session_id, total_frames,\nelapsed_seconds", PALETTE["teal"]),
    ]
    for x, y, head, body, accent in boxes:
        card(p, x, y, 185, 92, head, body, accent)


def draw_live_flow(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "Live Payload Data Flow(실시간 페이로드 데이터 흐름)", "Frame(프레임) 변환")
    steps = [
        ("1 Start request(시작 요청)", "LiveSessionStartRequest\nuuid, dance_type, content_id", PALETTE["blue"]),
        ("2 Session state(세션 상태)", "LIVE_SESSIONS\nsession_id, status, started_at", PALETTE["teal"]),
        ("3 Client frame(클라이언트 프레임)", "LiveFrameMessage\nimage: bytes\nframe_index", PALETTE["coral"]),
        ("4 AI payload(AI 페이로드)", "LiveFrameMessage_go_ai_server\nimage: base64 string(문자열)", PALETTE["gold"]),
        ("5 Result(결과)", "LiveFrameResultMessage\ntotal_calories\nmovement_score", PALETTE["green"]),
    ]
    x0 = 35
    for i, (head, body, col) in enumerate(steps):
        draw_text_box(p, x0, 322, 164, 42, head, size=10, color=PALETTE["white"], bold=True, fill=col, align="center", valign="mid")
        draw_text_box(p, x0, 212, 164, 96, body, size=9, fill=PALETTE["white"], stroke="#DFE4E8", align="center", valign="mid")
        if i < len(steps) - 1:
            arrow(p, x0 + 170, 252)
        x0 += 186
    bullets(p, 65, 80, 830, 80, [
        "server(서버)가 total_frames(총 프레임), elapsed_seconds(경과 초), total_calories(총 칼로리)를 소유하고 누적합니다.",
        "AI response(AI 응답)의 calories_burned(소모 칼로리)와 movement_score(움직임 점수)가 client response(클라이언트 응답)에 합쳐집니다.",
    ], size=11)


def draw_food_flow(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "Food Payload Data Flow(식단 페이로드 데이터 흐름)", "Image(이미지) -> AI(인공지능) -> Table(테이블)")
    steps = [
        ("Request(요청)", "FormData(폼 데이터)\nuuid, day, image UploadFile", PALETTE["blue"]),
        ("Normalize(정규화)", "validate image(이미지 검증)\nbuild storage_path(저장 경로)", PALETTE["teal"]),
        ("AI request(AI 요청)", "FoodAnalysisRequest\nimage_base64", PALETTE["coral"]),
        ("AI response(AI 응답)", "FoodIntakeAnalysisResponse\nfoods[], total_calories", PALETTE["green"]),
        ("Persist(저장)", "DailyFoodLog rows(행)\nBucket_Name, File_Path", PALETTE["gold"]),
    ]
    x0 = 40
    for i, (head, body, col) in enumerate(steps):
        draw_text_box(p, x0, 318, 160, 42, head, size=11, color=PALETTE["white"], bold=True, fill=col, align="center", valign="mid")
        draw_text_box(p, x0, 215, 160, 90, body, size=9, fill=PALETTE["white"], stroke="#DFE4E8", align="center", valign="mid")
        if i < len(steps) - 1:
            arrow(p, x0 + 166, 252)
        x0 += 184
    card(p, 70, 85, 250, 78, "Storage row(스토리지 행)", "path=uuid/date_uuid.ext\nimage_url(public URL)(공개 URL)", PALETTE["gold"])
    card(p, 355, 85, 250, 78, "Food row(음식 행)", "UUID, Day, FoodName, Calories\none row per item(항목별 1행)", PALETTE["green"])
    card(p, 640, 85, 250, 78, "Read response(조회 응답)", "Foods, TotalCalories, RecordCount\nrecord screen(기록 화면)", PALETTE["blue"])


def draw_profile_flow(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "Profile Data Flow(프로필 데이터 흐름)", "SignUp(가입) + Profile(프로필) + Bucket(버킷)")
    steps = [
        ("Signup request(가입 요청)", "UserSignUp\nname, email, age", PALETTE["blue"]),
        ("SignUp table(가입 테이블)", "UUID generated(UUID 생성)\nName, Email, Age", PALETTE["teal"]),
        ("Profile update(프로필 수정)", "UserProfileUpdate\nheight, weight, target", PALETTE["coral"]),
        ("Profile bucket(프로필 버킷)", "Profile_Photo bucket(버킷)\nFilePath", PALETTE["gold"]),
        ("Profile response(프로필 응답)", "profile_image_url\njoined data(조인 데이터)", PALETTE["green"]),
    ]
    x0 = 38
    for i, (head, body, col) in enumerate(steps):
        draw_text_box(p, x0, 315, 160, 42, head, size=10, color=PALETTE["white"], bold=True, fill=col, align="center", valign="mid")
        draw_text_box(p, x0, 212, 160, 90, body, size=9, fill=PALETTE["white"], stroke="#DFE4E8", align="center", valign="mid")
        if i < len(steps) - 1:
            arrow(p, x0 + 166, 250)
        x0 += 184
    bullets(p, 75, 82, 810, 90, [
        "SYNCED_SIGNUP_COLUMNS(가입 동기화 컬럼)와 SYNCED_PROFILE_COLUMNS(프로필 동기화 컬럼)로 update target(수정 대상)을 나눕니다.",
        "profile read(프로필 조회)는 SignUp table(가입 테이블)과 Profile table(프로필 테이블)을 join(조인)하고 storage public URL(스토리지 공개 주소)을 붙입니다.",
    ], size=11)


def draw_config(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "Runtime Config(실행 설정)", "Environment variable(환경 변수)")
    rows = [
        ("GENERAL_SERVER_HOST", "127.0.0.1", "FastAPI bind address(바인드 주소)"),
        ("GENERAL_SERVER_PORT", "8000", "general API port(API 포트)"),
        ("AI_HOST / AI_PORT", "0.0.0.0 / 8001", "AI WebSocket target(AI 웹소켓 대상)"),
        ("AI_DANCE_WS_PATH", "/ws/dance/analyze", "dance frame path(댄스 프레임 경로)"),
        ("AI_FOOD_WS_PATH", "/ws/food/analyze", "food image path(음식 이미지 경로)"),
        ("SUPABASE_URL / KEY", ".env file(.env 파일)", "database/storage credential(자격 증명)"),
    ]
    y = 345
    for name, default, role in rows:
        draw_text_box(p, 85, y, 250, 34, name, size=11, color=PALETTE["white"], bold=True, fill=PALETTE["ink2"], valign="mid")
        draw_text_box(p, 360, y, 220, 34, default, size=11, fill=PALETTE["white"], stroke="#DFE4E8", valign="mid")
        draw_text_box(p, 605, y, 270, 34, role, size=11, fill=PALETTE["white"], stroke="#DFE4E8", valign="mid")
        y -= 50


def draw_api(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "API Surface(API 표면)", "Data owner(데이터 주체) 기준")
    rows = [
        ("User/Profile(사용자/프로필)", "POST /api/signup | PUT /api/Profile/{uuid} | GET /api/profile/{uuid}", PALETTE["blue"]),
        ("Home/Food(홈/식단)", "GET /api/home/{uuid} | POST /api/food/intake | GET /api/daily_food_intake/{uuid}/", PALETTE["green"]),
        ("Live Session(실시간 세션)", "POST /api/live/session/start | WS /ws/live/{session_id} | POST /api/live/session/end", PALETTE["coral"]),
        ("Content/Record(콘텐츠/기록)", "GET /api/classes | GET /api/records", PALETTE["gold"]),
    ]
    y = 330
    for head, body, col in rows:
        draw_text_box(p, 65, y, 240, 46, head, size=12, color=PALETTE["white"], bold=True, fill=col, align="center", valign="mid")
        draw_text_box(p, 330, y, 560, 46, body, size=10, fill=PALETTE["white"], stroke="#DFE4E8", valign="mid")
        y -= 68


def draw_risk(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "Risk(리스크) & Gap(공백)", "Current finding(현재 확인)")
    bullets(p, 70, 125, 820, 245, [
        "README(리드미)는 servers/ai_server path(경로)를 언급하지만 current repository(현재 저장소)에는 해당 folder(폴더)가 보이지 않습니다.",
        "demo client(데모 클라이언트)는 type=frame + image_base64를 보내고, route(라우트)는 frame_binary + binary payload(바이너리 페이로드)를 기대합니다.",
        "build_ai_dance_ws_url(...) function(함수)이 AI_DANCE_WS_PATH(인공지능 댄스 경로)를 사용하지 않아 AI WebSocket URL(AI 웹소켓 주소) 점검이 필요합니다.",
        "LIVE_SESSIONS state(세션 상태)가 memory(메모리)에 있어 restart(재시작)와 multi-process(멀티 프로세스)에 취약합니다.",
    ], size=12)


def draw_roadmap(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "Improvement Plan(개선 계획)", "Fix order(수정 순서)")
    phases = [
        ("1", "Protocol alignment(프로토콜 정렬)", "client/server/AI schema(클라이언트/서버/AI 스키마)를 하나로 맞춥니다.", PALETTE["coral"]),
        ("2", "AI path cleanup(AI 경로 정리)", "AI_DANCE_WS_PATH(인공지능 댄스 경로)와 host(호스트)를 정확히 사용합니다.", PALETTE["teal"]),
        ("3", "Persistent session(영속 세션)", "memory dict(메모리 딕셔너리)를 shared store(공유 저장소)로 대체합니다.", PALETTE["green"]),
        ("4", "Production guardrail(운영 안전장치)", "auth(인증), rate limit(요청 제한), structured log(구조화 로그)를 추가합니다.", PALETTE["blue"]),
    ]
    x0 = 60
    for num, head, body, col in phases:
        draw_text_box(p, x0, 315, 190, 36, f"Phase {num}({num}단계)", size=12, color=PALETTE["white"], bold=True, fill=col, align="center", valign="mid")
        draw_text_box(p, x0, 250, 190, 46, head, size=12, bold=True, fill=PALETTE["white"], stroke="#DFE4E8", align="center", valign="mid")
        draw_text_box(p, x0, 150, 190, 82, body, size=10, color=PALETTE["sub"], fill=PALETTE["white"], stroke="#DFE4E8", align="center", valign="mid")
        if num != "4":
            arrow(p, x0 + 198, 215)
        x0 += 220


def draw_close(p: canvas.Canvas) -> None:
    slide_bg(p, PALETTE["ink"])
    p.setFillColor(c(PALETTE["ink2"]))
    p.setStrokeColor(c(PALETTE["line"]))
    p.roundRect(70, 90, 820, 360, 10, fill=1, stroke=1)
    draw_text_box(p, 100, 390, 760, 30, "Closing Message(마무리 메시지)", size=15, color=PALETTE["gold"], bold=True, align="center")
    draw_text_box(p, 115, 255, 730, 90, "Dance Diet Server는 mobile client(모바일 클라이언트), AI analysis(인공지능 분석), Supabase data layer(슈파베이스 데이터 계층)를 잇는 backend hub(백엔드 허브)입니다.", size=24, color=PALETTE["white"], bold=True, align="center", valign="mid")
    draw_text_box(p, 155, 175, 650, 55, "next action(다음 조치): live WebSocket protocol(실시간 웹소켓 프로토콜)과 AI server path(인공지능 서버 경로)를 하나로 맞추기.", size=15, color="#D6E0E6", align="center")


def draw_agenda_requested(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "목차", "Presentation Agenda(발표 목차)")
    rows = [
        ("01", "프로젝트 개요", "팀에서 최종 작성할 mockup(목업) 영역"),
        ("02", "기술 스택", "FastAPI(패스트API), Supabase(슈파베이스), WebSocket(웹소켓), AI prototype(인공지능 프로토타입)"),
        ("03", "시스템 아키텍처", "client(클라이언트), server(서버), AI server(인공지능 서버), database(데이터베이스)"),
        ("04", "시스템 구성도", "data flow(데이터 흐름), request/response(요청/응답), storage(스토리지)"),
        ("05", "핵심 기능 설명", "profile(프로필), live session(실시간 세션), food intake(식단 섭취), record(기록)"),
        ("06", "시연 영상", "팀에서 video(영상)를 직접 삽입할 placeholder(자리표시자)"),
        ("07", "DB 구성도", "Supabase(슈파베이스) 권한 확인 후 실제 schema(스키마) 반영"),
        ("08", "전체 개발 내용 및 향후 개발 계획", "팀에서 최종 작성할 placeholder(자리표시자)"),
    ]
    y = 372
    for num, head, body in rows:
        draw_text_box(p, 62, y, 54, 30, num, size=11, color=PALETTE["white"], bold=True, fill=PALETTE["teal"], align="center", valign="mid")
        draw_text_box(p, 134, y, 260, 30, head, size=12, bold=True, valign="mid")
        draw_text_box(p, 415, y, 460, 30, body, size=10, fill=PALETTE["white"], stroke="#DFE4E8", valign="mid")
        y -= 42


def draw_project_overview_mock(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "프로젝트 개요", "Mockup(목업) 영역")
    draw_text_box(p, 68, 320, 390, 72, "이 영역은 팀 발표자가 직접 채울 project summary(프로젝트 요약) 공간입니다.", size=22, bold=True)
    card(p, 62, 170, 250, 92, "Problem(문제)", "사용자가 dance workout(댄스 운동), calorie tracking(칼로리 추적), food record(식단 기록)를 따로 관리하는 불편함을 해결합니다.", PALETTE["coral"])
    card(p, 355, 170, 250, 92, "Solution(해결)", "mobile client(모바일 클라이언트)와 backend server(백엔드 서버)를 통해 workout data(운동 데이터)와 food data(식단 데이터)를 연결합니다.", PALETTE["teal"])
    card(p, 648, 170, 250, 92, "Expected value(기대 효과)", "daily goal(일일 목표), consumed calorie(섭취 칼로리), burned calorie(소모 칼로리)를 한 흐름으로 보여줍니다.", PALETTE["green"])
    draw_text_box(p, 105, 92, 750, 40, "PLACEHOLDER(자리표시자): 팀 소개, 대상 사용자, 서비스 한 줄 설명을 여기에 넣으면 됩니다.", size=13, color=PALETTE["sub"], fill=PALETTE["soft"], align="center", valign="mid")


def draw_tech_stack_requested(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "기술 스택", "Tech Stack(기술 스택)")
    rows = [
        ("Backend(백엔드)", "FastAPI(패스트API), Uvicorn(유비콘), Python(파이썬)", "REST API(REST API), file upload(파일 업로드), middleware(미들웨어)"),
        ("Realtime(실시간)", "WebSocket(웹소켓), websockets library(웹소켓 라이브러리)", "live frame streaming(실시간 프레임 스트리밍), AI bridge(인공지능 브리지)"),
        ("Data(데이터)", "Supabase(슈파베이스)", "table(테이블), storage bucket(스토리지 버킷), public URL(공개 URL)"),
        ("Schema(스키마)", "Pydantic(파이단틱)", "request validation(요청 검증), response model(응답 모델)"),
        ("AI prototype(AI 프로토타입)", "OpenCV(오픈CV), MediaPipe(미디어파이프), NumPy(넘파이)", "pose landmark(포즈 랜드마크), movement score(움직임 점수)"),
        ("Tooling(도구)", "uv(유브이), pyproject.toml(파이프로젝트 설정)", "dependency management(의존성 관리), local run(로컬 실행)"),
    ]
    y = 345
    for area, tech, role in rows:
        draw_text_box(p, 62, y, 160, 34, area, size=11, color=PALETTE["white"], bold=True, fill=PALETTE["ink2"], valign="mid")
        draw_text_box(p, 244, y, 300, 34, tech, size=10, fill=PALETTE["white"], stroke="#DFE4E8", valign="mid")
        draw_text_box(p, 566, y, 330, 34, role, size=10, fill=PALETTE["white"], stroke="#DFE4E8", valign="mid")
        y -= 48


def draw_system_architecture_requested(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "시스템 아키텍처", "System Architecture(시스템 아키텍처)")
    draw_text_box(p, 56, 302, 170, 58, "Mobile client\n(모바일 클라이언트)", size=12, color=PALETTE["white"], bold=True, fill=PALETTE["blue"], align="center", valign="mid")
    arrow(p, 242, 322, 42, PALETTE["line"])
    draw_text_box(p, 300, 286, 210, 90, "General server\n(일반 서버)\nFastAPI(패스트API)\nREST API + WebSocket", size=12, color=PALETTE["white"], bold=True, fill=PALETTE["teal"], align="center", valign="mid")
    arrow(p, 526, 322, 42, PALETTE["line"])
    draw_text_box(p, 584, 302, 160, 58, "AI server\n(인공지능 서버)", size=12, color=PALETTE["white"], bold=True, fill=PALETTE["coral"], align="center", valign="mid")
    draw_text_box(p, 300, 148, 210, 62, "Supabase\n(슈파베이스)\nDB + Storage", size=12, color=PALETTE["white"], bold=True, fill=PALETTE["green"], align="center", valign="mid")
    p.setFillColor(c(PALETTE["green"]))
    p.rect(398, 224, 6, 48, fill=1, stroke=0)
    bullets(p, 68, 74, 820, 62, [
        "general server(일반 서버)는 API gateway(API 게이트웨이), session manager(세션 관리자), AI bridge(인공지능 브리지) 역할을 맡습니다.",
        "Supabase(슈파베이스)는 user profile(사용자 프로필), daily food log(일일 식단 기록), image storage(이미지 저장소)를 담당합니다.",
    ], size=10)


def draw_system_diagram_requested(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "시스템 구성도", "Data Flow(데이터 흐름) 기준")
    steps = [
        ("User data\n(사용자 데이터)", "SignUp/Profile table\n(가입/프로필 테이블)", PALETTE["blue"]),
        ("Live frame\n(실시간 프레임)", "WebSocket(웹소켓)\n-> AI server(인공지능 서버)", PALETTE["coral"]),
        ("Food image\n(식단 이미지)", "Storage bucket(스토리지 버킷)\n+ DailyFoodLog table(테이블)", PALETTE["green"]),
        ("Home summary\n(홈 요약)", "target calorie(목표 칼로리)\n+ intake calorie(섭취 칼로리)", PALETTE["gold"]),
    ]
    x0 = 60
    for idx, (head, body, color) in enumerate(steps):
        draw_text_box(p, x0, 295, 185, 56, head, size=12, color=PALETTE["white"], bold=True, fill=color, align="center", valign="mid")
        draw_text_box(p, x0, 182, 185, 88, body, size=10, fill=PALETTE["white"], stroke="#DFE4E8", align="center", valign="mid")
        if idx < len(steps) - 1:
            arrow(p, x0 + 194, 220, 36, PALETTE["line"])
        x0 += 220
    draw_text_box(p, 105, 92, 750, 40, "핵심은 request data(요청 데이터)가 schema(스키마) 검증을 거쳐 table(테이블), bucket(버킷), AI response(AI 응답)로 나뉘어 흐르는 구조입니다.", size=12, color=PALETTE["sub"], fill=PALETTE["soft"], align="center", valign="mid")


def draw_core_features_requested(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "핵심 기능 설명", "Core Features(핵심 기능)")
    features = [
        ("회원/프로필 관리", "signup(가입), login(로그인), profile update(프로필 수정), profile image(프로필 이미지)"),
        ("실시간 댄스 세션", "session start(세션 시작), WebSocket frame(웹소켓 프레임), AI movement score(AI 움직임 점수)"),
        ("식단 이미지 분석", "food image upload(식단 이미지 업로드), AI food analysis(AI 음식 분석), DailyFoodLog 저장"),
        ("홈/기록 조회", "daily target calorie(일일 목표 칼로리), intake calorie(섭취 칼로리), record period(기록 기간)"),
    ]
    y = 322
    for idx, (head, body) in enumerate(features, start=1):
        color = [PALETTE["blue"], PALETTE["coral"], PALETTE["green"], PALETTE["gold"]][idx - 1]
        draw_text_box(p, 72, y, 54, 44, f"{idx}", size=18, color=PALETTE["white"], bold=True, fill=color, align="center", valign="mid")
        draw_text_box(p, 150, y, 210, 44, head, size=13, bold=True, valign="mid")
        draw_text_box(p, 380, y, 500, 44, body, size=10, fill=PALETTE["white"], stroke="#DFE4E8", valign="mid")
        y -= 70


def draw_demo_video_placeholder(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "시연 영상", "Demo Video(시연 영상) Placeholder(자리표시자)")
    p.setFillColor(c("#101820"))
    p.setStrokeColor(c(PALETTE["line"]))
    p.roundRect(115, 118, 730, 300, 10, fill=1, stroke=1)
    p.setFillColor(c(PALETTE["coral"]))
    path = p.beginPath()
    path.moveTo(440, 215)
    path.lineTo(440, 320)
    path.lineTo(535, 267)
    path.close()
    p.drawPath(path, fill=1, stroke=0)
    draw_text_box(p, 170, 80, 620, 34, "PLACEHOLDER(자리표시자): 팀에서 촬영한 video(영상)를 이 영역에 삽입하세요.", size=13, color=PALETTE["sub"], fill=PALETTE["soft"], align="center", valign="mid")


def draw_db_diagram_placeholder(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "DB ERD", "Entity Relationship Diagram(개체 관계도) - Code-derived(코드 기준)")

    def entity(
        x: float,
        y: float,
        w: float,
        h: float,
        name: str,
        label: str,
        rows: list[tuple[str, str]],
        accent: str,
    ) -> None:
        p.setFillColor(c(PALETTE["white"]))
        p.setStrokeColor(c("#D7DEE2"))
        p.roundRect(x, y, w, h, 7, fill=1, stroke=1)
        p.setFillColor(c(accent))
        p.roundRect(x, y + h - 38, w, 38, 7, fill=1, stroke=0)
        p.setFillColor(c(accent))
        p.rect(x, y + h - 20, w, 20, fill=1, stroke=0)
        p.setFillColor(c(PALETTE["white"]))
        p.setFont(FONT_BOLD, 12)
        p.drawCentredString(x + w / 2, y + h - 23, name)
        p.setFillColor(c("#EAF2F4"))
        p.setFont(FONT, 7)
        p.drawCentredString(x + w / 2, y + h - 34, label)

        row_h = (h - 50) / len(rows)
        current_y = y + h - 50 - row_h
        for tag, field in rows:
            p.setStrokeColor(c("#EDF1F3"))
            p.line(x + 10, current_y + row_h, x + w - 10, current_y + row_h)
            if tag:
                tag_fill = PALETTE["coral"] if "FK" in tag else PALETTE["blue"]
                p.setFillColor(c(tag_fill))
                p.roundRect(x + 16, current_y + 3.5, 44, row_h - 7, 4, fill=1, stroke=0)
                p.setFillColor(c(PALETTE["white"]))
                p.setFont(FONT_BOLD, 6)
                p.drawCentredString(x + 38, current_y + row_h / 2 - 2, tag)
                p.setFillColor(c(PALETTE["text"]))
                p.setFont(FONT, 8)
                p.drawString(x + 70, current_y + row_h / 2 - 3, field)
            else:
                p.setFillColor(c(PALETTE["text"]))
                p.setFont(FONT, 8)
                p.drawString(x + 24, current_y + row_h / 2 - 3, field)
            current_y -= row_h

    def bucket(x: float, y: float, w: float, h: float, name: str, path: str, accent: str) -> None:
        p.setFillColor(c(PALETTE["soft_gold"]))
        p.setStrokeColor(c(accent))
        p.roundRect(x, y, w, h, 7, fill=1, stroke=1)
        draw_text_box(p, x + 12, y + h - 34, w - 24, 24, name, size=10, color=PALETTE["text"], bold=True, align="center", valign="mid")
        draw_text_box(p, x + 12, y + 10, w - 24, h - 44, path, size=8, color=PALETTE["sub"], align="center", valign="mid")

    def relation(x1: float, y1: float, x2: float, y2: float, start: str, end: str, label: str) -> None:
        p.setStrokeColor(c(PALETTE["line"]))
        p.setLineWidth(1.8)
        p.line(x1, y1, x2, y2)
        p.setFillColor(c(PALETTE["line"]))
        p.circle(x1, y1, 3, fill=1, stroke=0)
        p.circle(x2, y2, 3, fill=1, stroke=0)
        draw_text_box(p, x1 + 6, y1 + 6, 34, 16, start, size=8, color=PALETTE["line"], bold=True, align="center", valign="mid")
        draw_text_box(p, x2 - 38, y2 + 6, 34, 16, end, size=8, color=PALETTE["line"], bold=True, align="center", valign="mid")
        draw_text_box(p, (x1 + x2) / 2 - 52, (y1 + y2) / 2 + 6, 104, 18, label, size=7, color=PALETTE["sub"], fill=PALETTE["soft"], align="center", valign="mid")

    entity(
        60,
        206,
        240,
        176,
        "SignUp",
        "user account(사용자 계정)",
        [
            ("PK", "UUID"),
            ("", "Name"),
            ("", "Email"),
            ("", "Password"),
            ("", "Age"),
            ("", "Created_at"),
        ],
        PALETTE["blue"],
    )
    entity(
        390,
        262,
        250,
        150,
        "Profile",
        "profile detail(프로필 상세)",
        [
            ("PK/FK", "UUID"),
            ("", "Height, Weight"),
            ("", "Target_weight, Target_day"),
            ("", "Today_Target_kcal"),
            ("", "Current_streak"),
            ("", "Bucket_Profile_Photo"),
            ("", "FilePath"),
        ],
        PALETTE["teal"],
    )
    entity(
        390,
        78,
        250,
        150,
        "DailyFoodLog",
        "daily meal record(일일 식단 기록)",
        [
            ("FK", "UUID"),
            ("", "Day"),
            ("", "FoodName"),
            ("", "Calories"),
            ("", "Bucket_Name"),
            ("", "File_Path"),
        ],
        PALETTE["green"],
    )

    bucket(700, 300, 198, 72, "Profile_Photo bucket\n(프로필 사진 버킷)", "path: uuid/timestamp.ext", PALETTE["gold"])
    bucket(700, 112, 198, 72, "DailyFoodLog bucket\n(식단 이미지 버킷)", "path: uuid/date_uuid.ext", PALETTE["coral"])

    relation(300, 310, 390, 337, "1", "0..1", "Profile.UUID FK")
    relation(300, 250, 390, 153, "1", "N", "DailyFoodLog.UUID FK")

    p.setStrokeColor(c(PALETTE["gold"]))
    p.setDash(5, 4)
    p.line(640, 337, 700, 336)
    p.setStrokeColor(c(PALETTE["coral"]))
    p.line(640, 153, 700, 148)
    p.setDash()
    draw_text_box(p, 648, 344, 52, 18, "FilePath", size=7, color=PALETTE["sub"], align="center", valign="mid")
    draw_text_box(p, 645, 160, 56, 18, "File_Path", size=7, color=PALETTE["sub"], align="center", valign="mid")

    draw_text_box(p, 70, 38, 820, 30, "Source(출처): internal_services.py, schemas.py, Bucket.py. Supabase API(슈파베이스 API)는 현재 401 Unauthorized(권한 없음)라서 실제 constraint(제약조건)는 dashboard(대시보드) 권한 확인 후 검증 필요.", size=9, color=PALETTE["sub"], fill=PALETTE["soft"], align="center", valign="mid")


def draw_dev_plan_placeholder(p: canvas.Canvas) -> None:
    slide_bg(p)
    title(p, "전체 개발 내용 및 향후 개발 계획", "Development Summary(개발 요약) Placeholder(자리표시자)")
    columns = [
        ("Completed(완료)", "회원/프로필 API(API)\n실시간 session(세션)\n식단 upload(업로드)"),
        ("In progress(진행 중)", "AI server(인공지능 서버) 연동\nprotocol(프로토콜) 정리\nDB schema(DB 스키마) 검증"),
        ("Next(다음)", "시연 video(영상) 촬영\nDB diagram(DB 구성도) 확정\ntest(테스트) 보강"),
        ("Future(향후)", "auth(인증)\ndeployment(배포)\nanalytics(분석)"),
    ]
    x0 = 58
    for idx, (head, body) in enumerate(columns):
        color = [PALETTE["blue"], PALETTE["coral"], PALETTE["green"], PALETTE["gold"]][idx]
        draw_text_box(p, x0, 310, 190, 44, head, size=12, color=PALETTE["white"], bold=True, fill=color, align="center", valign="mid")
        draw_text_box(p, x0, 160, 190, 126, body, size=11, fill=PALETTE["white"], stroke="#DFE4E8", align="center", valign="mid")
        x0 += 220
    draw_text_box(p, 105, 85, 750, 40, "PLACEHOLDER(자리표시자): 팀이 실제 개발 내용과 sprint plan(스프린트 계획)을 최종 입력하면 됩니다.", size=13, color=PALETTE["sub"], fill=PALETTE["soft"], align="center", valign="mid")


DRAWERS = {
    "cover": draw_cover,
    "agenda": lambda p, s: draw_agenda(p),
    "agenda_requested": lambda p, s: draw_agenda_requested(p),
    "project_overview_mock": lambda p, s: draw_project_overview_mock(p),
    "tech_stack_requested": lambda p, s: draw_tech_stack_requested(p),
    "system_architecture_requested": lambda p, s: draw_system_architecture_requested(p),
    "system_diagram_requested": lambda p, s: draw_system_diagram_requested(p),
    "core_features_requested": lambda p, s: draw_core_features_requested(p),
    "demo_video_placeholder": lambda p, s: draw_demo_video_placeholder(p),
    "db_diagram_placeholder": lambda p, s: draw_db_diagram_placeholder(p),
    "dev_plan_placeholder": lambda p, s: draw_dev_plan_placeholder(p),
    "goal": lambda p, s: draw_goal(p),
    "schema": lambda p, s: draw_schema(p),
    "live_flow": lambda p, s: draw_live_flow(p),
    "food_flow": lambda p, s: draw_food_flow(p),
    "profile_flow": lambda p, s: draw_profile_flow(p),
    "config": lambda p, s: draw_config(p),
    "api": lambda p, s: draw_api(p),
    "risk": lambda p, s: draw_risk(p),
    "roadmap": lambda p, s: draw_roadmap(p),
    "close": lambda p, s: draw_close(p),
}


def build_pdf() -> None:
    register_fonts()
    p = canvas.Canvas(str(PDF_PATH), pagesize=(W, H))
    for slide in SLIDES:
        DRAWERS[slide["kind"]](p, slide)
        p.setFont(FONT, 8)
        p.setFillColor(c(PALETTE["muted"] if slide["kind"] in {"cover", "close"} else PALETTE["line"]))
        p.drawString(44, 24, "Server_Dance-diet | PDF(PDF) automatic presentation(자동 발표)")
        p.drawRightString(916, 24, f"{SLIDES.index(slide) + 1:02d}/{len(SLIDES):02d}")
        p.showPage()
    p.save()


def render_pages() -> None:
    import fitz

    if PAGES_DIR.exists():
        shutil.rmtree(PAGES_DIR)
    PAGES_DIR.mkdir(parents=True)
    doc = fitz.open(PDF_PATH)
    for idx, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pix.save(PAGES_DIR / f"page_{idx:02d}.png")


def build_html() -> None:
    data = [
        {
            "title": slide["title"],
            "script": slide["script"],
            "image": f"rendered_pages/page_{idx:02d}.png",
        }
        for idx, slide in enumerate(SLIDES, start=1)
    ]
    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dance Diet Server Automatic Presentation</title>
  <style>
    :root {{
      color-scheme: dark;
      --ink: #111820;
      --panel: #17212B;
      --line: #32404B;
      --text: #EEF3F4;
      --muted: #AEB8BF;
      --teal: #2AA7A5;
      --coral: #F26957;
      --gold: #E5B94B;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      background: var(--ink);
      color: var(--text);
      font-family: "Malgun Gothic", "Segoe UI", sans-serif;
    }}
    main {{
      width: 100vw;
      height: 100vh;
      padding: 0;
      margin: 0;
      background: #05080c;
    }}
    .stage {{
      width: 100vw;
      height: 100vh;
      background: #0b1117;
      position: relative;
      overflow: hidden;
      cursor: none;
    }}
    .stage img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
      background: #0b1117;
    }}
  </style>
</head>
<body>
  <main>
    <section class="stage" aria-label="PDF(PDF) rendered slide(렌더링 슬라이드)">
      <img id="slideImage" alt="presentation slide">
    </section>
  </main>
  <script>
    const slides = {json.dumps(data, ensure_ascii=False, indent=2)};
    let index = 0;
    let playing = false;
    let timer = null;
    const img = document.getElementById('slideImage');
    const stage = document.querySelector('.stage');

    function chooseVoice() {{
      const voices = speechSynthesis.getVoices();
      return voices.find(v => v.lang && v.lang.toLowerCase().startsWith('ko')) || voices.find(v => v.lang && v.lang.toLowerCase().startsWith('en')) || voices[0] || null;
    }}

    function estimateMs(text) {{
      return Math.max(6500, Math.min(24000, text.length * 78));
    }}

    function render() {{
      const slide = slides[index];
      img.src = slide.image;
      document.title = `${{index + 1}} / ${{slides.length}} - ${{slide.title}}`;
    }}

    function speakCurrent() {{
      speechSynthesis.cancel();
      const slide = slides[index];
      const utter = new SpeechSynthesisUtterance(slide.script);
      utter.lang = 'ko-KR';
      utter.rate = 0.95;
      utter.pitch = 1.0;
      utter.volume = 1.0;
      const voice = chooseVoice();
      if (voice) utter.voice = voice;
      utter.onend = () => {{
        if (!playing) return;
        timer = setTimeout(nextAuto, 800);
      }};
      utter.onerror = () => {{
        if (!playing) return;
        timer = setTimeout(nextAuto, estimateMs(slide.script));
      }};
      speechSynthesis.speak(utter);
    }}

    function nextAuto() {{
      if (index >= slides.length - 1) {{
        playing = false;
        return;
      }}
      index += 1;
      render();
      speakCurrent();
    }}

    function start() {{
      if (document.documentElement.requestFullscreen && !document.fullscreenElement) {{
        document.documentElement.requestFullscreen().catch(() => {{}});
      }}
      playing = true;
      render();
      speakCurrent();
    }}

    function stop() {{
      playing = false;
      clearTimeout(timer);
      speechSynthesis.cancel();
    }}

    stage.addEventListener('click', () => {{
      if (!playing) start();
    }});
    document.addEventListener('keydown', (event) => {{
      if (event.key === ' ' || event.key === 'Enter') {{
        event.preventDefault();
        if (!playing) start();
        else if (speechSynthesis.paused) speechSynthesis.resume();
        else speechSynthesis.pause();
      }}
      if (event.key === 'ArrowLeft') {{
      index = Math.max(0, index - 1);
      render();
      if (playing) speakCurrent();
      }}
      if (event.key === 'ArrowRight') {{
      index = Math.min(slides.length - 1, index + 1);
      render();
      if (playing) speakCurrent();
      }}
      if (event.key.toLowerCase() === 's') stop();
    }});
    speechSynthesis.onvoiceschanged = chooseVoice;
    render();
  </script>
</body>
</html>
"""
    HTML_PATH.write_text(html, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build_pdf()
    render_pages()
    build_html()
    print(PDF_PATH)
    print(HTML_PATH)
    print(PAGES_DIR)


if __name__ == "__main__":
    main()
