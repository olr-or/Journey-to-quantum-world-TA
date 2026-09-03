from __future__ import annotations

import hmac
import io
import queue
import random
import re
import threading
import time as time_module
from datetime import datetime, time
from zoneinfo import ZoneInfo

import gspread
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload


st.set_page_config(
    page_title="Class Attendance",
    page_icon="🐣",
    layout="centered",
)

st.markdown(
    """
    <style>
      :root {
        --yellow-50: #fffdf4;
        --yellow-100: #fff6cf;
        --yellow-200: #ffe89a;
        --yellow-400: #f2c94c;
        --yellow-500: #e7b832;
        --yellow-600: #c99716;
        --ink: #3f392d;
        --muted: #847c69;
        --line: #efe3b9;
      }

      .stApp {
        background: linear-gradient(180deg, #fffdf7 0%, #ffffff 40%);
        color: var(--ink);
      }

      .block-container {
        max-width: 760px;
        padding-top: 4.2rem;
        padding-bottom: 4rem;
      }

      .student-hero { margin: 0 0 1.25rem 0; }

      .student-kicker {
        color: var(--yellow-600);
        font-weight: 700;
        font-size: .78rem;
        letter-spacing: .12em;
        text-transform: uppercase;
        margin-bottom: .35rem;
      }

      .student-title {
        font-size: clamp(2rem, 6vw, 3rem);
        line-height: 1.05;
        font-weight: 800;
        letter-spacing: -.04em;
        color: #3d372b;
        margin: 0 0 .55rem 0;
      }

      .student-subtitle {
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.65;
        margin: 0;
      }

      .schedule-card {
        background: linear-gradient(135deg, #fff8dc, #fffdf3);
        border: 1px solid var(--yellow-200);
        border-radius: 18px;
        padding: 1rem 1.15rem;
        margin: 1rem 0 1.35rem 0;
        color: #6f6240;
        box-shadow: 0 8px 24px rgba(201, 151, 22, .08);
        line-height: 1.7;
      }

      .schedule-card strong { color: #a87700; }

      div[data-testid="stForm"] {
        background: rgba(255,255,255,.92);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 1.35rem 1.35rem .75rem;
        box-shadow: 0 12px 36px rgba(128, 102, 26, .06);
      }

      div[data-baseweb="input"] > div,
      div[data-baseweb="textarea"] > div {
        border-radius: 14px !important;
        border-color: var(--line) !important;
        background: #fffdf7 !important;
      }

      div[data-baseweb="input"] > div:focus-within,
      div[data-baseweb="textarea"] > div:focus-within {
        border-color: var(--yellow-400) !important;
        box-shadow: 0 0 0 1px var(--yellow-400) !important;
      }

      button[kind="primary"],
      button[kind="primaryFormSubmit"],
      div[data-testid="stFormSubmitButton"] button,
      button[data-testid="stBaseButton-primary"],
      button[data-testid="stBaseButton-primaryFormSubmit"] {
        background: linear-gradient(135deg, #e7b832, #c99716) !important;
        background-color: #e7b832 !important;
        border: none !important;
        color: white !important;
        border-radius: 14px !important;
        min-height: 3rem !important;
        font-weight: 700 !important;
        box-shadow: 0 8px 20px rgba(201, 151, 22, .22) !important;
      }

      button[kind="primary"]:hover,
      button[kind="primaryFormSubmit"]:hover,
      div[data-testid="stFormSubmitButton"] button:hover,
      button[data-testid="stBaseButton-primary"]:hover,
      button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
        background: linear-gradient(135deg, #f2c94c, #e7b832) !important;
        background-color: #e7b832 !important;
        border: none !important;
        color: white !important;
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(201, 151, 22, .28) !important;
      }

      div[data-testid="stMetric"] {
        background: #fffdf7;
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 12px;
      }

      .instruction-card {
        background: #fff9e8;
        border-left: 4px solid var(--yellow-400);
        border-radius: 14px;
        padding: .9rem 1rem;
        margin: 1rem 0 1.25rem;
        color: #6d6247;
        line-height: 1.6;
      }

      .success-card {
        text-align: center;
        background: linear-gradient(145deg, #fff8dc, #ffffff);
        border: 1px solid var(--yellow-200);
        border-radius: 24px;
        padding: 2rem 1.4rem;
        margin: 1.25rem 0;
        box-shadow: 0 16px 36px rgba(201, 151, 22, .10);
      }

      .success-icon {
        width: 54px;
        height: 54px;
        margin: 0 auto .85rem;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #ffe7a3;
        color: #9c7200;
        font-size: 1.55rem;
        font-weight: 900;
      }

      .success-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #4b4330;
        margin-bottom: .35rem;
      }

      .success-copy {
        color: var(--muted);
        font-size: .96rem;
      }

      div[data-testid="stAlert"] { border-radius: 16px; }

      @media (max-width: 640px) {
        .block-container { padding-top: 3.4rem; }
        .student-title { font-size: 2.15rem; }
        div[data-testid="stForm"] { padding: 1rem 1rem .55rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

KST = ZoneInfo("Asia/Seoul")

SPREADSHEET_ID = "1QqzM0Me8-YgAER0HLjNwhQ9x2CdIK5Huibdjb0oaDnw"

ROSTER_HEADERS = ["Student ID", "Name", "Department"]

ATTENDANCE_HEADERS = [
    "Student ID",
    "Name",
    "Department",
    "Session",
    "Submitted At",
    "Status",
    "Class Response",
    "Photo URL",
]

REFLECTION_SHEET = "reflections"
REFLECTION_HEADERS = [
    "Student ID",
    "Name",
    "Department",
    "Class Date",
    "Day",
    "Session",
    "Submitted At",
    "Reflection",
]

RESPONSE_MIN_CHARS = 20
REFLECTION_MIN_CHARS = 20
DATE_SHEET_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

CLASS_SCHEDULE = {
    1: [
        {
            "session": "16:00 Check",
            "day_name": "Tuesday",
            "open": time(16, 0, 0),
            "present_until": time(16, 10, 0),
            "late_until": time(16, 20, 0),
            "close": time(17, 0, 0),
        },
        {
            "session": "17:00 Check",
            "day_name": "Tuesday",
            "open": time(17, 0, 0),
            "present_until": time(17, 5, 0),
            "late_until": time(17, 20, 0),
            "close": time(18, 0, 0),
        },
    ],
    3: [
        {
            "session": "15:00 Check",
            "day_name": "Thursday",
            "open": time(15, 0, 0),
            "present_until": time(15, 10, 0),
            "late_until": time(15, 20, 0),
            "close": time(16, 0, 0),
        },
    ],
}

REFLECTION_SCHEDULE = {
    1: {
        "day_name": "Tuesday",
        "session": "17:40 Reflection",
        "open": time(17, 40, 0),
        "close": time(19, 0, 0),
    },
    3: {
        "day_name": "Thursday",
        "session": "15:50 Reflection",
        "open": time(15, 50, 0),
        "close": time(17, 0, 0),
    },
}

def now_kst() -> datetime:
    return datetime.now(KST)


RETRYABLE_HTTP_STATUS = {429, 500, 502, 503, 504}


def _http_status_from_exception(exc: Exception):
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status is None:
        resp = getattr(exc, "resp", None)
        status = getattr(resp, "status", None)
    try:
        return int(status) if status is not None else None
    except Exception:
        return None


def api_call_with_backoff(func, *, attempts: int = 7):
    """Retry transient Google API failures with exponential backoff."""
    for attempt in range(attempts):
        try:
            return func()
        except (gspread.exceptions.APIError, HttpError) as exc:
            status = _http_status_from_exception(exc)
            if status not in RETRYABLE_HTTP_STATUS or attempt == attempts - 1:
                raise
            delay = min((2 ** attempt) + random.uniform(0.0, 0.8), 20.0)
            time_module.sleep(delay)


@st.cache_resource(show_spinner=False)
def submission_state():
    return {
        "lock": threading.RLock(),
        "attendance": set(),
        "reflections": set(),
    }


def clear_read_caches():
    read_roster.clear()
    read_attendance_sheet.clear()
    read_reflections.clear()
    list_attendance_sheets.clear()


def class_context(now: datetime | None = None) -> dict:
    if now is None:
        now = now_kst()
    elif now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    else:
        now = now.astimezone(KST)

    schedules = CLASS_SCHEDULE.get(now.weekday())

    if schedules is None:
        return {
            "is_class_day": False,
            "can_submit": False,
            "message": "No class is scheduled today.",
            "date_sheet": now.date().isoformat(),
            "now": now,
            "schedule": None,
        }

    current_t = now.time().replace(tzinfo=None)

    for schedule in schedules:
        if schedule["open"] <= current_t <= schedule["close"]:
            return {
                "is_class_day": True,
                "can_submit": True,
                "message": "Attendance submission is currently open.",
                "date_sheet": now.date().isoformat(),
                "now": now,
                "schedule": schedule,
            }

    first_open = schedules[0]["open"]
    last_close = schedules[-1]["close"]

    if current_t < first_open:
        message = (
            f"Attendance submission opens at "
            f"{first_open.strftime('%H:%M')}."
        )
    else:
        message = (
            f"Today's attendance submission closed at "
            f"{last_close.strftime('%H:%M')}."
        )

    return {
        "is_class_day": True,
        "can_submit": False,
        "message": message,
        "date_sheet": now.date().isoformat(),
        "now": now,
        "schedule": None,
    }


def reflection_context(now: datetime | None = None) -> dict:
    if now is None:
        now = now_kst()
    elif now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    else:
        now = now.astimezone(KST)

    schedule = REFLECTION_SCHEDULE.get(now.weekday())
    date_sheet = now.date().isoformat()

    if schedule is None:
        return {
            "is_reflection_day": False,
            "can_submit": False,
            "message": "No class reflection is scheduled today.",
            "date_sheet": date_sheet,
            "now": now,
            "schedule": None,
        }

    current_t = now.time().replace(tzinfo=None)

    if schedule["open"] <= current_t <= schedule["close"]:
        return {
            "is_reflection_day": True,
            "can_submit": True,
            "message": "Class Reflection is currently open.",
            "date_sheet": date_sheet,
            "now": now,
            "schedule": schedule,
        }

    if current_t < schedule["open"]:
        message = (
            f"Class Reflection opens at "
            f"{schedule['open'].strftime('%H:%M')}."
        )
    else:
        message = (
            f"Today's Class Reflection closed at "
            f"{schedule['close'].strftime('%H:%M')}."
        )

    return {
        "is_reflection_day": True,
        "can_submit": False,
        "message": message,
        "date_sheet": date_sheet,
        "now": now,
        "schedule": schedule,
    }



def determine_status(submitted_at: datetime) -> str:
    submitted_at = submitted_at.astimezone(KST)

    schedules = CLASS_SCHEDULE.get(submitted_at.weekday())
    if schedules is None:
        return "Absent"

    t = submitted_at.time().replace(tzinfo=None)

    for schedule in schedules:
        if schedule["open"] <= t <= schedule["close"]:
            if t <= schedule["present_until"]:
                return "Present"
            if t <= schedule["late_until"]:
                return "Late"
            return "Absent"

    return "Absent"

def secret_ready() -> bool:
    try:
        _ = st.secrets["ADMIN_PASSWORD"]
        _ = st.secrets["gcp_service_account"]
        _ = st.secrets["drive_oauth"]
        _ = st.secrets["DRIVE_FOLDER_ID"]
        return True
    except Exception:
        return False


def service_account_info() -> dict:
    return dict(st.secrets["gcp_service_account"])


@st.cache_resource(show_spinner=False)
def open_spreadsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_service_account_info(
        service_account_info(),
        scopes=scopes,
    )
    client = gspread.authorize(credentials)
    return client.open_by_key(SPREADSHEET_ID)


@st.cache_resource(show_spinner=False)
def drive_service():
    oauth = dict(st.secrets["drive_oauth"])

    credentials = UserCredentials(
        token=None,
        refresh_token=oauth["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=oauth["client_id"],
        client_secret=oauth["client_secret"],
        scopes=["https://www.googleapis.com/auth/drive"],
    )

    return build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


@st.cache_data(ttl=60, show_spinner=False)
def worksheet_exists(title: str) -> bool:
    try:
        api_call_with_backoff(lambda: open_spreadsheet().worksheet(title))
        return True
    except gspread.WorksheetNotFound:
        return False


@st.cache_resource(show_spinner=False)
def get_or_create_worksheet(title: str, rows: int, cols: int):
    spreadsheet = open_spreadsheet()
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


@st.cache_data(ttl=600, show_spinner=False)
def read_roster() -> pd.DataFrame:
    ws = get_or_create_worksheet("students", rows=200, cols=6)
    values = api_call_with_backoff(ws.get_all_values)

    if not values:
        return pd.DataFrame(columns=ROSTER_HEADERS)

    header = [str(x).strip() for x in values[0]]
    missing = [col for col in ROSTER_HEADERS if col not in header]

    if missing:
        raise RuntimeError(
            "The 'students' sheet is missing required columns: "
            + ", ".join(missing)
        )

    raw = pd.DataFrame(values[1:], columns=header)
    df = raw[ROSTER_HEADERS].copy()

    for col in ROSTER_HEADERS:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df = df[
        (df["Student ID"] != "")
        & (df["Name"] != "")
    ].copy()

    df["Student ID"] = df["Student ID"].str.replace(r"\.0$", "", regex=True)

    return df.reset_index(drop=True)


@st.cache_resource(show_spinner=False)
def ensure_attendance_sheet(date_sheet: str):
    ws = get_or_create_worksheet(
        date_sheet,
        rows=500,
        cols=len(ATTENDANCE_HEADERS) + 2,
    )

    first_row = api_call_with_backoff(lambda: ws.row_values(1))

    if not first_row:
        api_call_with_backoff(
            lambda: ws.append_row(ATTENDANCE_HEADERS, value_input_option="RAW")
        )

        sheet_id = ws.id
        requests = []
        for value, color in [
            ("출석", {"red": 0.094, "green": 0.502, "blue": 0.220}),
            ("지각", {"red": 0.890, "green": 0.455, "blue": 0.000}),
            ("결석", {"red": 0.851, "green": 0.188, "blue": 0.145}),
        ]:
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": 5,
                            "endColumnIndex": 6,
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": value}],
                            },
                            "format": {
                                "textFormat": {
                                    "foregroundColor": color,
                                    "bold": True,
                                }
                            },
                        },
                    },
                    "index": 0,
                }
            })
        api_call_with_backoff(
            lambda: open_spreadsheet().batch_update({"requests": requests})
        )
        return ws

    if first_row[: len(ATTENDANCE_HEADERS)] != ATTENDANCE_HEADERS:
        raise RuntimeError(
            f"The header of the '{date_sheet}' sheet does not match the expected format. "
            f"Please set the first row to {ATTENDANCE_HEADERS}."
        )

    return ws


@st.cache_data(ttl=20, show_spinner=False)
def read_attendance_sheet(date_sheet: str) -> pd.DataFrame:
    try:
        ws = api_call_with_backoff(lambda: open_spreadsheet().worksheet(date_sheet))
    except gspread.WorksheetNotFound:
        return pd.DataFrame(columns=ATTENDANCE_HEADERS)

    values = api_call_with_backoff(ws.get_all_values)
    if not values:
        return pd.DataFrame(columns=ATTENDANCE_HEADERS)

    header = values[0]
    if header[: len(ATTENDANCE_HEADERS)] != ATTENDANCE_HEADERS:
        raise RuntimeError(
            f"The header of the '{date_sheet}' sheet does not match the expected format. "
            f"Please set the first row to {ATTENDANCE_HEADERS}."
        )

    normalized = []
    for row in values[1:]:
        row = list(row) + [""] * (len(ATTENDANCE_HEADERS) - len(row))
        normalized.append(row[: len(ATTENDANCE_HEADERS)])

    if not normalized:
        return pd.DataFrame(columns=ATTENDANCE_HEADERS)
    return pd.DataFrame(normalized, columns=ATTENDANCE_HEADERS)


@st.cache_resource(show_spinner=False)
def ensure_reflection_sheet():
    ws = get_or_create_worksheet(
        REFLECTION_SHEET,
        rows=1000,
        cols=len(REFLECTION_HEADERS) + 2,
    )

    first_row = api_call_with_backoff(lambda: ws.row_values(1))

    if not first_row:
        api_call_with_backoff(
            lambda: ws.append_row(REFLECTION_HEADERS, value_input_option="RAW")
        )
        return ws

    if first_row[: len(REFLECTION_HEADERS)] != REFLECTION_HEADERS:
        raise RuntimeError(
            f"The header of the '{REFLECTION_SHEET}' sheet does not match the expected format. "
            f"Please set the first row to {REFLECTION_HEADERS}."
        )

    return ws


@st.cache_data(ttl=20, show_spinner=False)
def read_reflections() -> pd.DataFrame:
    try:
        ws = api_call_with_backoff(lambda: open_spreadsheet().worksheet(REFLECTION_SHEET))
    except gspread.WorksheetNotFound:
        return pd.DataFrame(columns=REFLECTION_HEADERS)

    values = api_call_with_backoff(ws.get_all_values)
    if not values:
        return pd.DataFrame(columns=REFLECTION_HEADERS)

    header = values[0]
    if header[: len(REFLECTION_HEADERS)] != REFLECTION_HEADERS:
        raise RuntimeError(
            f"The header of the '{REFLECTION_SHEET}' sheet does not match the expected format. "
            f"Please set the first row to {REFLECTION_HEADERS}."
        )

    normalized = []
    for row in values[1:]:
        row = list(row) + [""] * (len(REFLECTION_HEADERS) - len(row))
        normalized.append(row[: len(REFLECTION_HEADERS)])

    if not normalized:
        return pd.DataFrame(columns=REFLECTION_HEADERS)
    return pd.DataFrame(normalized, columns=REFLECTION_HEADERS)


def reflection_has_submitted(student_id: str, class_date: str) -> bool:
    key = (str(student_id).strip(), str(class_date).strip())
    state = submission_state()

    with state["lock"]:
        if key in state["reflections"]:
            return True

    df = read_reflections()
    if df.empty:
        return False

    matched = df[
        (df["Student ID"].astype(str).str.strip() == key[0])
        & (df["Class Date"].astype(str).str.strip() == key[1])
    ]
    exists = not matched.empty
    if exists:
        with state["lock"]:
            state["reflections"].add(key)
    return exists


class SheetWriteBatcher:
    """Batch near-simultaneous submissions into a small number of Sheets writes."""

    def __init__(self):
        self._queue = queue.Queue()
        self._thread = threading.Thread(
            target=self._worker,
            name="google-sheet-batch-writer",
            daemon=True,
        )
        self._thread.start()

    def submit(self, kind: str, sheet_name: str, row: list, state_key: tuple):
        item = {
            "kind": kind,
            "sheet_name": sheet_name,
            "row": row,
            "state_key": state_key,
            "done": threading.Event(),
            "error": None,
        }
        state = submission_state()
        bucket = "attendance" if kind == "attendance" else "reflections"

        with state["lock"]:
            if state_key in state[bucket]:
                raise ValueError(
                    "Attendance has already been submitted for today's class."
                    if kind == "attendance"
                    else "You have already submitted today's class reflection."
                )
            state[bucket].add(state_key)

        self._queue.put(item)

        if not item["done"].wait(timeout=45):
            with state["lock"]:
                state[bucket].discard(state_key)
            raise TimeoutError("Saving took too long. Please try again in a moment.")

        if item["error"] is not None:
            raise item["error"]

    def _worker(self):
        while True:
            first = self._queue.get()
            batch = [first]
            deadline = time_module.monotonic() + 1.0

            while len(batch) < 100:
                remaining = deadline - time_module.monotonic()
                if remaining <= 0:
                    break
                try:
                    batch.append(self._queue.get(timeout=remaining))
                except queue.Empty:
                    break

            groups = {}
            for item in batch:
                groups.setdefault((item["kind"], item["sheet_name"]), []).append(item)

            for (kind, sheet_name), items in groups.items():
                state = submission_state()
                bucket = "attendance" if kind == "attendance" else "reflections"
                try:
                    ws = ensure_attendance_sheet(sheet_name) if kind == "attendance" else ensure_reflection_sheet()
                    rows = [item["row"] for item in items]
                    api_call_with_backoff(
                        lambda ws=ws, rows=rows: ws.append_rows(rows, value_input_option="RAW")
                    )
                except Exception as exc:
                    with state["lock"]:
                        for item in items:
                            state[bucket].discard(item["state_key"])
                            item["error"] = exc
                            item["done"].set()
                else:
                    for item in items:
                        item["done"].set()


@st.cache_resource(show_spinner=False)
def sheet_write_batcher():
    return SheetWriteBatcher()


def append_reflection(
    student: pd.Series,
    submitted_at: datetime,
    session: str,
    reflection: str,
) -> None:
    submitted_at = submitted_at.astimezone(KST)
    class_date = submitted_at.date().isoformat()

    if reflection_has_submitted(str(student["Student ID"]), class_date):
        raise ValueError("You have already submitted today's class reflection.")

    row = [
        str(student["Student ID"]),
        str(student["Name"]),
        str(student["Department"]),
        class_date,
        submitted_at.strftime("%A"),
        session,
        submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
        reflection.strip(),
    ]
    state_key = (str(student["Student ID"]).strip(), class_date)
    sheet_write_batcher().submit(
        kind="reflection",
        sheet_name=REFLECTION_SHEET,
        row=row,
        state_key=state_key,
    )


def student_has_submitted(
    student_id: str,
    date_sheet: str,
    session: str,
) -> bool:
    key = (str(student_id).strip(), str(date_sheet).strip(), str(session).strip())
    state = submission_state()

    with state["lock"]:
        if key in state["attendance"]:
            return True

    df = read_attendance_sheet(date_sheet)
    if df.empty:
        return False

    matched = df[
        (df["Student ID"].astype(str).str.strip() == key[0])
        & (df["Session"].astype(str).str.strip() == key[2])
    ]
    exists = not matched.empty
    if exists:
        with state["lock"]:
            state["attendance"].add(key)
    return exists


def append_attendance_record(
    student: pd.Series,
    submitted_at: datetime,
    status: str,
    session: str,
    class_response: str,
    photo_url: str,
) -> None:
    date_sheet = submitted_at.astimezone(KST).date().isoformat()

    if student_has_submitted(str(student["Student ID"]), date_sheet, session):
        raise ValueError("Attendance has already been submitted for today's class.")

    status_korean = {
        "Present": "출석",
        "Late": "지각",
        "Absent": "결석",
    }.get(status, status)

    row = [
        str(student["Student ID"]),
        str(student["Name"]),
        str(student["Department"]),
        session,
        submitted_at.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S"),
        status_korean,
        class_response.strip(),
        photo_url,
    ]
    state_key = (str(student["Student ID"]).strip(), date_sheet, str(session).strip())
    sheet_write_batcher().submit(
        kind="attendance",
        sheet_name=date_sheet,
        row=row,
        state_key=state_key,
    )


@st.cache_data(ttl=60, show_spinner=False)
def list_attendance_sheets() -> list[str]:
    return sorted(
        [
            ws.title
            for ws in api_call_with_backoff(open_spreadsheet().worksheets)
            if DATE_SHEET_RE.match(ws.title)
        ],
        reverse=True,
    )


def escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


@st.cache_data(ttl=3600, show_spinner=False)
def get_or_create_date_folder(date_sheet: str) -> str:
    service = drive_service()
    parent_folder_id = str(st.secrets["DRIVE_FOLDER_ID"]).strip()
    escaped_name = escape_drive_query(date_sheet)

    query = (
        f"name = '{escaped_name}' "
        f"and '{parent_folder_id}' in parents "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )

    result = api_call_with_backoff(
        lambda: service.files().list(
            q=query,
            spaces="drive",
            fields="files(id,name)",
            pageSize=10,
        ).execute()
    )

    files = result.get("files", [])
    if files:
        return files[0]["id"]

    created = api_call_with_backoff(
        lambda: service.files().create(
            body={
                "name": date_sheet,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_folder_id],
            },
            fields="id",
        ).execute()
    )

    return created["id"]


def safe_filename_part(value: str) -> str:
    value = str(value).strip()
    value = re.sub(r'[\\/:*?"<>|]+', "_", value)
    return value or "student"


def compress_camera_image(
    camera_file,
    *,
    target_bytes: int = 900_000,
    max_dimension: int = 1920,
) -> bytes:
    """
    Keep the camera capture at 1080p in the browser, but recompress it before
    uploading to Google Drive. The goal is roughly <= 0.9 MB while preserving
    enough detail for attendance verification.
    """
    original = camera_file.getvalue()

    try:
        with Image.open(io.BytesIO(original)) as img:
            img = ImageOps.exif_transpose(img)

            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            elif img.mode == "L":
                img = img.convert("RGB")

            # Keep 1080p-scale detail, but avoid unexpectedly huge camera frames.
            if max(img.size) > max_dimension:
                scale = max_dimension / max(img.size)
                new_size = (
                    max(1, int(img.width * scale)),
                    max(1, int(img.height * scale)),
                )
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Start high and step down only if needed.
            for quality in (82, 76, 70, 64, 58):
                output = io.BytesIO()
                img.save(
                    output,
                    format="JPEG",
                    quality=quality,
                    progressive=True,
                    subsampling="4:2:0",
                )
                compressed = output.getvalue()

                if len(compressed) <= target_bytes:
                    return compressed

            # If still over target, use the smallest result from the loop.
            return compressed

    except Exception:
        # A photo upload should not fail solely because recompression failed.
        # Fall back to the original camera bytes.
        return original


def upload_attendance_photo(
    camera_file,
    student_id: str,
    student_name: str,
    submitted_at: datetime,
) -> str:
    date_sheet = submitted_at.astimezone(KST).date().isoformat()
    folder_id = get_or_create_date_folder(date_sheet)

    filename = (
        f"{safe_filename_part(student_id)}_"
        f"{safe_filename_part(student_name)}_"
        f"{submitted_at.astimezone(KST).strftime('%H%M%S')}.jpg"
    )

    compressed_photo = compress_camera_image(camera_file)

    media = MediaIoBaseUpload(
        io.BytesIO(compressed_photo),
        mimetype="image/jpeg",
        resumable=False,
    )

    created = api_call_with_backoff(
        lambda: drive_service().files().create(
            body={
                "name": filename,
                "parents": [folder_id],
            },
            media_body=media,
            fields="id,webViewLink",
        ).execute()
    )

    file_id = created["id"]

    return created.get(
        "webViewLink",
        f"https://drive.google.com/file/d/{file_id}/view",
    )


def make_date_excel(
    roster: pd.DataFrame,
    attendance_df: pd.DataFrame,
) -> bytes:
    output = io.BytesIO()

    submitted_ids = (
        set(attendance_df["Student ID"].astype(str))
        if not attendance_df.empty
        else set()
    )

    missing = roster[
        ~roster["Student ID"].astype(str).isin(submitted_ids)
    ].copy()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        attendance_df.to_excel(writer, sheet_name="Attendance", index=False)
        missing.to_excel(writer, sheet_name="Not Submitted", index=False)
        roster.to_excel(writer, sheet_name="Student Roster", index=False)

        for sheet_name in ["Attendance", "Not Submitted", "Student Roster"]:
            ws = writer.sheets[sheet_name]
            ws.freeze_panes(1, 0)
            ws.set_column(0, max(0, ws.dim_colmax), 18)

    return output.getvalue()


def make_all_dates_excel(
    roster: pd.DataFrame,
    date_sheets: list[str],
) -> bytes:
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        roster.to_excel(writer, sheet_name="Student Roster", index=False)
        roster_ws = writer.sheets["Student Roster"]
        roster_ws.freeze_panes(1, 0)
        roster_ws.set_column(0, max(0, roster_ws.dim_colmax), 18)

        for date_sheet in sorted(date_sheets):
            df = read_attendance_sheet(date_sheet)
            df.to_excel(writer, sheet_name=date_sheet, index=False)
            ws = writer.sheets[date_sheet]
            ws.freeze_panes(1, 0)
            ws.set_column(0, max(0, ws.dim_colmax), 18)

    return output.getvalue()


def student_page():
    context = class_context()

    st.markdown(
        """
        <div class="student-hero">
          <div class="student-kicker">CLASS ATTENDANCE</div>
          <div class="student-title">Attendance Check</div>
          <p class="student-subtitle">
            Take a photo of the ongoing lecture and briefly respond to the class question below.<br>
            Attendance is determined automatically based on the actual submission time.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """
        <div class="schedule-card">
          🐣 <strong>Regular class schedule</strong><br><br>

          <strong>Tuesday: 16:00–18:00</strong>
          <span style="font-size:0.93rem;">(attendance checks at 16:00 and 17:00)</span><br>
          &nbsp;&nbsp;16:00 check — Present: through 16:05 &nbsp;·&nbsp; Late: through 16:20 &nbsp;·&nbsp; Absent: after 16:20<br>
          &nbsp;&nbsp;17:00 check — Present: through 17:05 &nbsp;·&nbsp; Late: through 17:20 &nbsp;·&nbsp; Absent: after 17:20<br><br>

          <strong>Thursday: 15:00–16:00</strong><br>
          &nbsp;&nbsp;15:00 check — Present: through 15:05 &nbsp;·&nbsp; Late: through 15:20 &nbsp;·&nbsp; Absent: after 15:20
        </div>
        """,
        unsafe_allow_html=True,
    )

    if context["can_submit"] and context["schedule"] is not None:
        s = context["schedule"]
        st.caption(
            f"Current attendance window: {s['day_name']} — {s['session']} "
            f"({s['open'].strftime('%H:%M')}–{s['close'].strftime('%H:%M')})"
        )

    roster = read_roster()

    if roster.empty:
        st.error("The student roster has not been registered yet.")
        return

    if "attendance_student" not in st.session_state:
        st.session_state.attendance_student = None

    if "attendance_submitted" not in st.session_state:
        st.session_state.attendance_submitted = False

    if st.session_state.attendance_submitted:
        st.markdown(
            """
            <div class="success-card">
              <div class="success-icon">✓</div>
              <div class="success-title">Attendance Submitted</div>
              <div class="success-copy">
                Your submission has been recorded successfully.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Return to Start"):
            st.session_state.attendance_submitted = False
            st.session_state.attendance_student = None
            st.rerun()
        return

    if not context["can_submit"]:
        if context["is_class_day"]:
            st.info(context["message"])
        else:
            st.info(
                "No class is scheduled today. Attendance submission is available only "
                "during Tuesday 16:00–18:00 and Thursday 15:00–16:00."
            )
        return

    if st.session_state.attendance_student is None:
        with st.form("attendance_login"):
            student_id = st.text_input(
                "Student ID",
                placeholder="e.g. 2025163002",
            ).strip()

            student_name = st.text_input(
                "Name",
                placeholder="Enter your registered name",
            ).strip()

            start = st.form_submit_button(
                "Start Attendance Check",
                type="primary",
                use_container_width=True,
            )

        if start:
            matched = roster[
                (roster["Student ID"].astype(str) == student_id)
                & (roster["Name"].astype(str) == student_name)
            ]

            if matched.empty:
                st.error(
                    "The Student ID and Name do not match the registered roster."
                )
                return

            if student_has_submitted(
                student_id,
                context["date_sheet"],
                context["schedule"]["session"],
            ):
                st.warning(
                    "Attendance has already been submitted for today's class."
                )
                return

            st.session_state.attendance_student = matched.iloc[0].to_dict()
            st.rerun()

        return

    student = pd.Series(st.session_state.attendance_student)

    context = class_context()
    if not context["can_submit"]:
        st.warning(context["message"])
        return

    if student_has_submitted(
        str(student["Student ID"]),
        context["date_sheet"],
        context["schedule"]["session"],
    ):
        st.warning(
            "Attendance has already been submitted for today's class."
        )
        return

    c1, c2 = st.columns(2)
    c1.metric("Student", str(student["Name"]))
    c2.metric("Student ID", str(student["Student ID"]))

    if context["schedule"]["session"] == "17:00 Check":
        response_title = "What do you remember from today's class?"
        response_instruction = (
            "Write about something that stood out to you or that you remember "
            "from the past hour of today's class."
        )
        response_placeholder = (
            "Describe something that stood out to you or that you remember "
            "from the past hour of today's class."
        )
    else:
        response_title = "What do you expect to learn?"
        response_instruction = (
            "Briefly describe what you expect to learn or understand better "
            "during this class."
        )
        response_placeholder = (
            "Briefly describe what you expect to learn or understand better "
            "during this class."
        )

    st.markdown(
        f"""
        <div class="instruction-card">
        <strong>1. Take a class photo</strong><br>
        Use the camera below to photograph the ongoing lecture. File upload is not available.<br><br>
        <strong>2. Write a short response</strong><br>
        {response_instruction}
        </div>
        """,
        unsafe_allow_html=True,
    )

    session_key = (
        context["schedule"]["session"]
        .replace(" ", "_")
        .replace(":", "")
    )

    photo = st.camera_input(
        "Take a photo of the ongoing lecture",
        resolution="1080p",
        key=f"camera_{student['Student ID']}_{context['date_sheet']}_{session_key}",
    )

    class_response = st.text_area(
        response_title,
        placeholder=response_placeholder,
        height=140,
        max_chars=1000,
        key=f"response_{student['Student ID']}_{context['date_sheet']}_{session_key}",
    )

    st.caption(
        f"Please write at least {RESPONSE_MIN_CHARS} characters."
    )

    if st.button(
        "Submit Attendance",
        type="primary",
        use_container_width=True,
    ):
        submitted_at = now_kst()
        fresh_context = class_context(submitted_at)

        if not fresh_context["can_submit"]:
            st.error(
                "The attendance submission window has closed. "
                "Your submission was not recorded."
            )
            return

        if photo is None:
            st.error("Please take a class photo before submitting.")
            return

        if len(class_response.strip()) < RESPONSE_MIN_CHARS:
            st.error(
                f"Please write at least {RESPONSE_MIN_CHARS} characters "
                "in the Class Response field."
            )
            return

        if student_has_submitted(
            str(student["Student ID"]),
            fresh_context["date_sheet"],
            fresh_context["schedule"]["session"],
        ):
            st.warning(
                "Attendance has already been submitted for today's class."
            )
            return

        status = determine_status(submitted_at)

        try:
            with st.spinner("Saving your attendance record..."):
                photo_url = upload_attendance_photo(
                    photo,
                    str(student["Student ID"]),
                    str(student["Name"]),
                    submitted_at,
                )

                append_attendance_record(
                    student=student,
                    submitted_at=submitted_at,
                    status=status,
                    session=fresh_context["schedule"]["session"],
                    class_response=class_response,
                    photo_url=photo_url,
                )

        except Exception as exc:
            st.error(
                "An error occurred while saving your attendance. "
                "Please contact the course TAs."
            )
            st.exception(exc)
            return

        st.session_state.attendance_student = None
        st.session_state.attendance_submitted = True
        st.toast(f"Attendance submitted: {status} 🐣")
        st.rerun()

    if st.button("Change Student Information"):
        st.session_state.attendance_student = None
        st.rerun()


def reflection_page():
    context = reflection_context()

    st.markdown(
        """
        <div class="student-hero">
          <div class="student-kicker">CLASS REFLECTION</div>
          <div class="student-title">Class Reflection</div>
          <p class="student-subtitle">
            Share a short reflection on today's class.<br>
            No photo is required for this submission.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="schedule-card">
          🐣 <strong>Reflection submission schedule</strong><br><br>
          <strong>Tuesday:</strong> 17:40–18:00<br>
          <strong>Thursday:</strong> 15:50–16:00
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not context["can_submit"]:
        st.info(context["message"])
        return

    roster = read_roster()

    if roster.empty:
        st.error("The student roster has not been registered yet.")
        return

    if "reflection_student" not in st.session_state:
        st.session_state.reflection_student = None

    if "reflection_submitted" not in st.session_state:
        st.session_state.reflection_submitted = False

    if st.session_state.reflection_submitted:
        st.markdown(
            """
            <div class="success-card">
              <div class="success-icon">✓</div>
              <div class="success-title">Reflection Submitted</div>
              <div class="success-copy">
                Your class reflection has been recorded successfully.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Return to Reflection Start"):
            st.session_state.reflection_submitted = False
            st.session_state.reflection_student = None
            st.rerun()
        return

    if st.session_state.reflection_student is None:
        with st.form("reflection_login"):
            student_id = st.text_input(
                "Student ID",
                placeholder="e.g. 2025163002",
                key="reflection_student_id",
            ).strip()

            student_name = st.text_input(
                "Name",
                placeholder="Enter your registered name",
                key="reflection_student_name",
            ).strip()

            start = st.form_submit_button(
                "Start Class Reflection",
                type="primary",
                use_container_width=True,
            )

        if start:
            matched = roster[
                (roster["Student ID"].astype(str) == student_id)
                & (roster["Name"].astype(str) == student_name)
            ]

            if matched.empty:
                st.error(
                    "The Student ID and Name do not match the registered roster."
                )
                return

            if reflection_has_submitted(student_id, context["date_sheet"]):
                st.warning("You have already submitted today's class reflection.")
                return

            st.session_state.reflection_student = matched.iloc[0].to_dict()
            st.rerun()

        return

    student = pd.Series(st.session_state.reflection_student)

    context = reflection_context()
    if not context["can_submit"]:
        st.warning(context["message"])
        return

    if reflection_has_submitted(
        str(student["Student ID"]),
        context["date_sheet"],
    ):
        st.warning("You have already submitted today's class reflection.")
        return

    c1, c2 = st.columns(2)
    c1.metric("Student", str(student["Name"]))
    c2.metric("Student ID", str(student["Student ID"]))

    st.markdown(
        """
        <div class="instruction-card">
          <strong>Class Reflection</strong><br>
          Please share your thoughts or reflections on today's class.
          You can write about what stood out to you, what you found interesting,
          or how you felt about today's lesson.
        </div>
        """,
        unsafe_allow_html=True,
    )

    reflection_text = st.text_area(
        "What are your thoughts on today's class?",
        placeholder=(
            "Share anything that stood out to you, what you found interesting, "
            "or how you felt about today's class."
        ),
        height=170,
        max_chars=1500,
        key=f"reflection_{student['Student ID']}_{context['date_sheet']}",
    )

    st.caption(
        f"Please write at least {REFLECTION_MIN_CHARS} characters. No photo is required."
    )

    if st.button(
        "Submit Class Reflection",
        type="primary",
        use_container_width=True,
    ):
        submitted_at = now_kst()
        fresh_context = reflection_context(submitted_at)

        if not fresh_context["can_submit"]:
            st.error(
                "The Class Reflection submission window has closed. "
                "Your response was not recorded."
            )
            return

        if len(reflection_text.strip()) < REFLECTION_MIN_CHARS:
            st.error(
                f"Please write at least {REFLECTION_MIN_CHARS} characters."
            )
            return

        if reflection_has_submitted(
            str(student["Student ID"]),
            fresh_context["date_sheet"],
        ):
            st.warning("You have already submitted today's class reflection.")
            return

        try:
            with st.spinner("Saving your class reflection..."):
                append_reflection(
                    student=student,
                    submitted_at=submitted_at,
                    session=fresh_context["schedule"]["session"],
                    reflection=reflection_text,
                )
        except Exception as exc:
            st.error(
                "An error occurred while saving your class reflection. "
                "Please contact the course TAs."
            )
            st.exception(exc)
            return

        st.session_state.reflection_student = None
        st.session_state.reflection_submitted = True
        st.toast("Class reflection submitted 🐣")
        st.rerun()

    if st.button("Change Reflection Student Information"):
        st.session_state.reflection_student = None
        st.rerun()



def admin_login() -> bool:
    if st.session_state.get("admin_authenticated", False):
        return True

    password = st.text_input(
        "Admin Password",
        type="password",
    )

    if st.button("Admin Login", type="primary"):
        expected = str(st.secrets["ADMIN_PASSWORD"])

        if hmac.compare_digest(password, expected):
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False


def admin_page():
    st.title("Admin")

    if not admin_login():
        return

    if st.button("Log Out"):
        st.session_state.admin_authenticated = False
        st.rerun()

    roster = read_roster()

    st.subheader("Student Roster")

    if roster.empty:
        st.warning("No students are registered.")
        return

    st.success(f"{len(roster)} students are currently registered.")
    st.dataframe(
        roster,
        hide_index=True,
        use_container_width=True,
    )

    st.divider()
    st.subheader("Attendance Records")

    date_sheets = list_attendance_sheets()
    today = now_kst().date().isoformat()

    options = date_sheets.copy()
    if today not in options:
        options.insert(0, today)

    selected_date = st.selectbox(
        "Class Date",
        options,
        index=0,
    )

    attendance_df = read_attendance_sheet(selected_date)

    submitted_ids = (
        set(attendance_df["Student ID"].astype(str))
        if not attendance_df.empty
        else set()
    )

    missing = roster[
        ~roster["Student ID"].astype(str).isin(submitted_ids)
    ].copy()

    present_count = (
        int(attendance_df["Status"].isin(["출석", "Present"]).sum())
        if not attendance_df.empty else 0
    )
    late_count = (
        int(attendance_df["Status"].isin(["지각", "Late"]).sum())
        if not attendance_df.empty else 0
    )
    absent_count = (
        int(attendance_df["Status"].isin(["결석", "Absent"]).sum())
        if not attendance_df.empty else 0
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Present", present_count)
    m2.metric("Late", late_count)
    m3.metric("Absent", absent_count)
    m4.metric("Not Submitted", len(missing))

    total = len(roster)
    submitted_count = len(submitted_ids)
    st.progress(submitted_count / total if total else 0)

    st.markdown("**Submitted Records**")
    if attendance_df.empty:
        st.info("No attendance submissions for this date.")
    else:
        st.dataframe(
            attendance_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Photo URL": st.column_config.LinkColumn(
                    "Photo",
                    display_text="View Photo",
                )
            },
        )

    st.markdown("**Not Submitted**")
    if missing.empty:
        st.success("All students have submitted.")
    else:
        st.dataframe(
            missing,
            hide_index=True,
            use_container_width=True,
        )

    excel_bytes = make_date_excel(
        roster,
        attendance_df,
    )

    st.download_button(
        "Download Selected Date as Excel",
        data=excel_bytes,
        file_name=f"attendance_{selected_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    real_dates = list_attendance_sheets()
    if real_dates:
        all_bytes = make_all_dates_excel(
            roster,
            real_dates,
        )

        st.download_button(
            "Download All Attendance Records as Excel",
            data=all_bytes,
            file_name="attendance_all_dates.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.divider()
    st.subheader("Class Reflections")

    reflection_df = read_reflections()

    if reflection_df.empty:
        st.info("No class reflections have been submitted yet.")
    else:
        st.dataframe(
            reflection_df,
            hide_index=True,
            use_container_width=True,
        )

    if st.button("Reload Latest Data"):
        clear_read_caches()
        worksheet_exists.clear()
        st.rerun()


if not secret_ready():
    st.title("Class Attendance")
    st.error("Deployment setup has not been completed yet.")
    st.markdown(
        "Configure `ADMIN_PASSWORD`, `DRIVE_FOLDER_ID`, `[gcp_service_account]`, and "
        "`[drive_oauth]` in Streamlit Cloud **Secrets**."
    )
    st.stop()


page = st.sidebar.radio(
    "Menu",
    ["Attendance Check", "Class Reflection", "Admin"],
)

try:
    if page == "Attendance Check":
        student_page()
    elif page == "Class Reflection":
        reflection_page()
    else:
        admin_page()

except gspread.exceptions.APIError as exc:
    st.error(
        "A Google API error occurred. Check the Google Sheets/Drive APIs "
        "and sharing permissions for the service account."
    )
    st.exception(exc)

except Exception as exc:
    st.error(
        "There is a problem with the app configuration or data connection."
    )
    st.exception(exc)
