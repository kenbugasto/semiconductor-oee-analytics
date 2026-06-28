#!/usr/bin/env python
# coding: utf-8

# In[1]:


# =====================================================
# OEE Analytics Tool
# Handler CSV + Production TXT Integration
# Main-style Python / Anaconda Script Version
# =====================================================

import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html

import configparser
from ftplib import FTP
import subprocess
from datetime import datetime, timedelta

# =====================================================
# CONFIG - UPDATE THESE ONLY
# =====================================================

USER_ID = os.environ.get("USERNAME", "K02943")

CONFIG_PATH = Path(__file__).with_name("oee_config.ini")

config = configparser.ConfigParser()
config.read(CONFIG_PATH, encoding="utf-8")

def cfg_path(section, key):
    value = config.get(section, key)
    value = value.replace("{USER_ID}", USER_ID)
    return Path(value)

PLOT_BG = "#F2F2F2"

HANDLER_CSV_FOLDER = cfg_path("PATHS", "handler_csv_folder")
TXT_FOLDER = cfg_path("PATHS", "txt_folder")
OUT_DIR = cfg_path("PATHS", "out_dir")

TARGET_OEE = config.getfloat("OEE", "target_oee")
MAX_TEST_SITE_QTY = config.getint("OEE", "max_test_site_qty")

IDEAL_YIELD = config.getfloat("OEE", "ideal_yield")
IDEAL_TEST_TIME = config.getfloat("OEE", "ideal_test_time")
IDEAL_INDEX_TIME = config.getfloat("OEE", "ideal_index_time")

USE_FTP_DOWNLOAD = config.getboolean("RUN", "use_ftp_download", fallback=False)

if USE_FTP_DOWNLOAD:
    HANDLER_FTP_HOST = config.get("HANDLER_FTP", "host")
    HANDLER_FTP_USER = config.get("HANDLER_FTP", "user")
    HANDLER_FTP_PASSWORD = config.get("HANDLER_FTP", "password")
    HANDLER_FTP_ROOT = config.get("HANDLER_FTP", "root")

    HANDLER_FOLDERS = [
        x.strip()
        for x in config.get("HANDLER_FTP", "folders").split(",")
        if x.strip()
    ]

    TXT_FTP_HOST = config.get("TXT_FTP", "host")
    TXT_FTP_USER = config.get("TXT_FTP", "user")
    TXT_FTP_PASSWORD = config.get("TXT_FTP", "password")
    TXT_FTP_CUST_CODE = config.get("TXT_FTP", "cust_code")
    TXT_FTP_YR_CODE = config.getint("TXT_FTP", "yr_code")
else:
    HANDLER_FOLDERS = []

FTP_SCRIPT_PATH = Path(f"D:/ASEKH/{USER_ID}/oee_ftp_script.txt")
FTP_BATCH_PATH = Path(f"D:/ASEKH/{USER_ID}/oee_run_ftp.bat")

REPORT_DATE = pd.Timestamp(config.get("RUN", "report_date")).normalize()
ROLLING_START_DATE = pd.Timestamp(config.get("RUN", "rolling_start_date")).normalize()
ROLLING_END_DATE = pd.Timestamp(config.get("RUN", "rolling_end_date")).normalize()

# =====================================================
# COMMON HELPERS
# =====================================================

def parse_mixed_datetime(series):
    """
    Handles multiple formats:
    - 2026/2/5 上午 05:04:09
    - 2026/2/5 下午 01:04:09
    - 2026-05-23 20:25:48:825
    - 2026-05-23 20:25:48
    """
    s = series.fillna("").astype(str).str.strip()

    # Taiwan AM/PM format
    s_tw = (
        s.str.replace("上午", " AM ", regex=False)
         .str.replace("下午", " PM ", regex=False)
         .str.replace(r"\s+", " ", regex=True)
    )

    parsed_tw = pd.to_datetime(
        s_tw,
        format="%Y/%m/%d %p %I:%M:%S",
        errors="coerce"
    )

    # Handler datetime with millisecond after colon
    # 2026-05-23 20:25:48:825 -> 2026-05-23 20:25:48.825
    s_ms = s.str.replace(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}):(\d+)$",
        r"\1.\2",
        regex=True
    )

    parsed_ms = pd.to_datetime(
        s_ms,
        format="%Y-%m-%d %H:%M:%S.%f",
        errors="coerce"
    )

    parsed_normal = pd.to_datetime(s_ms, errors="coerce")

    return parsed_tw.fillna(parsed_ms).fillna(parsed_normal)


def clean_numeric(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce"
    ).fillna(0)


def safe_filename(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(value)).strip("_")


def get_clean_handler(handler_name):

    value = str(handler_name).strip().upper()

    if "-" in value:
        value = value.split("-")[-1].strip()

    value = value.replace("KDH", "HDLR")

    return value

def extract_date_from_filename(filename):
    m = re.search(r"(20\d{6})", str(filename))
    if not m:
        return pd.NaT
    return pd.to_datetime(m.group(1), format="%Y%m%d", errors="coerce")


def download_handler_csv_from_ftp(target_date, local_csv_root):
    target_date = pd.Timestamp(target_date)

    date_str_file = target_date.strftime("%Y%m%d")
    date_str_folder = target_date.strftime("%Y_%m_%d")

    expected_file = f"MessageLog_{date_str_file}.csv"

    local_csv_root.mkdir(parents=True, exist_ok=True)

    print("\nConnecting to handler CSV FTP...")
    print("Target FTP date folder:", date_str_folder)
    print("Target CSV file:", expected_file)

    with FTP(HANDLER_FTP_HOST, timeout=60) as ftp:
        ftp.login(HANDLER_FTP_USER, HANDLER_FTP_PASSWORD)

        for handler_folder in HANDLER_FOLDERS:
            remote_dir = f"/{HANDLER_FTP_ROOT}/{handler_folder}/{date_str_folder}"

            local_handler_name = handler_folder.replace("1100-", "")
            local_handler_dir = local_csv_root / local_handler_name
            local_handler_dir.mkdir(parents=True, exist_ok=True)

            local_file = local_handler_dir / expected_file

            try:
                ftp.cwd(remote_dir)
                remote_files = ftp.nlst()
            except Exception as e:
                print(f"WARNING: Cannot access FTP folder: {remote_dir} | {e}")
                continue

            if expected_file not in remote_files:
                print(f"WARNING: Missing file: {expected_file} in {remote_dir}")
                print("Available files:", remote_files[:20])
                continue

            print(f"Downloading {expected_file} -> {local_file}")

            with open(local_file, "wb") as f:
                ftp.retrbinary(f"RETR {expected_file}", f.write)

    print("Handler CSV FTP download completed.")

def ensure_folder(folder_path):
    Path(folder_path).mkdir(parents=True, exist_ok=True)


def daterange(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def create_txt_ftp_script(
    start_date,
    end_date,
    ftp_script_path,
    download_dir
):
    ensure_folder(download_dir)
    ensure_folder(ftp_script_path.parent)

    yr_code = TXT_FTP_YR_CODE
    yr_code_bef = yr_code - 1
    if yr_code_bef < 0:
        yr_code_bef = 9

    target_stations = ["1100", "1101", "1102"]

    lines = [
        f"open {TXT_FTP_HOST}",
        TXT_FTP_USER,
        TXT_FTP_PASSWORD,
        f"cd /SUM/{TXT_FTP_CUST_CODE}/{yr_code}",
        "binary",
        "prompt",
        f"lcd {download_dir}",
    ]

    for d in daterange(start_date, end_date):
        ymd = d.strftime("%Y%m%d")
        for station in target_stations:
            lines.append(f"mget ??????????_{station}_*{ymd}??????.txt")

    lines.append(f"cd /SUM/{TXT_FTP_CUST_CODE}/{yr_code_bef}")

    for d in daterange(start_date, end_date):
        ymd = d.strftime("%Y%m%d")
        for station in target_stations:
            lines.append(f"mget ??????????_{station}_*{ymd}??????.txt")

    lines.extend([
        "disconnect",
        "bye",
    ])

    ftp_script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ftp_script_path


def create_txt_ftp_batch(batch_path, ftp_script_path, working_dir):
    ensure_folder(batch_path.parent)

    lines = [
        "@echo off",
        "echo ========================================",
        "echo OEE TXT FTP DOWNLOAD STARTED",
        "echo ========================================",
        f"cd /d {working_dir}",
        f"ftp -s:{ftp_script_path}",
        "echo TXT FTP download finished.",
    ]

    batch_path.write_text("\r\n".join(lines) + "\r\n", encoding="mbcs")
    return batch_path


def run_batch_file(batch_path):
    process = subprocess.Popen(
        [str(batch_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=True,
    )

    print("\n=== TXT FTP DOWNLOAD LOG ===")

    for line in process.stdout:
        line = line.rstrip()
        if line:
            print(line, flush=True)

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(f"TXT FTP batch failed: {process.returncode}")


def download_txt_files_from_ftp(start_date, end_date, local_txt_folder):
    start_date = pd.Timestamp(start_date).date()
    end_date = pd.Timestamp(end_date).date()

    ensure_folder(local_txt_folder)

    before_files = {
        p.name for p in local_txt_folder.glob("*.txt")
    }

    ftp_script = create_txt_ftp_script(
        start_date=start_date,
        end_date=end_date,
        ftp_script_path=FTP_SCRIPT_PATH,
        download_dir=local_txt_folder,
    )

    batch_path = create_txt_ftp_batch(
        batch_path=FTP_BATCH_PATH,
        ftp_script_path=ftp_script,
        working_dir=local_txt_folder,
    )

    run_batch_file(batch_path)

    after_files = {
        p.name for p in local_txt_folder.glob("*.txt")
    }

    new_files = sorted(after_files - before_files)

    print(f"\nNew TXT files downloaded: {len(new_files)}")
    for name in new_files[:30]:
        print(" -", name)

    return new_files

# =====================================================
# HANDLER CSV LOADER
# =====================================================

def categorize_handler_event(row):
    msg = f"{row.get('Message','')} {row.get('MessageEn','')}".upper()
    code = str(row.get("AlarmCode", "")).strip()
    area = str(row.get("Area", "")).upper()

    if "AUTO MOVE IN OK" in msg:
        return "LOT_MOVE_IN"
    if "AUTO MOVE OUT OK" in msg:
        return "LOT_MOVE_OUT"
    if "START AUTO MOVE OUT" in msg:
        return "LOT_MOVE_OUT_START"
    if "INPUT COUNT" in msg:
        return "SUMMARY_OUTPUT"
    if "TOTAL RT TIME" in msg:
        return "SUMMARY_RETEST"
    if "TOTAL RUN SEC" in msg:
        return "SUMMARY_RUN_TIME"
    if "UPH" in msg:
        return "SUMMARY_UPH"
    if "SITESTATUS" in msg:
        return "SITE_STATUS"
    if "SITEUSERATE" in msg:
        return "SITE_USE_RATE"
    if "PAUSING" in msg or "暫停" in msg:
        return "PAUSE"
    if "ACCESS_GUARD_INTERRUPTION" in msg or "光柵" in msg:
        return "ACCESS_GUARD_INTERRUPTION"
    if "ROBOT" in msg or "機械手" in msg:
        return "ROBOT_ARM_NOT_READY"
    if "VACUUM" in msg or "吸料" in msg:
        return "VACUUM_ERROR"
    if "VISION" in msg or "視覺" in msg:
        return "VISION_ERROR"
    if "BINNING TIMEOUT" in msg:
        return "BINNING_TIMEOUT"
    if "DUT SENSOR FAIL" in msg:
        return "DUT_SENSOR_FAIL"
    if "NEST IN FAIL" in msg:
        return "NEST_FAIL"
    if "SAFETY DOOR" in msg or "安全門" in msg or "門鎖" in msg:
        return "SAFETY_DOOR"
    if "NG" in msg or code == "3001":
        if area == "LOADER_MACHINE":
            return "HANDLER_LOAD_UNLOAD"
        elif area == "TESTA":
            return "TEST_SITE_A_REPEAT_FAIL"
        elif area == "TESTB":
            return "TEST_SITE_B_REPEAT_FAIL"
        return "TESTER_NG"
    if "TESTERRESULT" in msg:
        return "TESTER_RESULT_FAIL"
    if area == "LOADER_MACHINE":
        return "LOADER_EVENT"
    if "CLOSESITE" in msg or "LOAD_CLOSE_FAIL" in msg:
        return "CLOSE_SITE_ASSIST"
    if "OPENSITE" in msg or "LOAD_OPEN_FAIL" in msg:
        return "OPEN_SITE_ASSIST"

    return "OTHER"


def load_handler_csv(path):
    df = pd.read_csv(path, engine="python")
    df.columns = [str(c).strip() for c in df.columns]

    required = [
        "ID_EventLog",
        "OccurDateTime",
        "Message",
        "MessageEn",
        "Area",
        "LotInfo",
        "AlarmCode",
        "MSGStartTime",
        "ResponseTime",
        "RepairTime",
        "Device",
        "HandlerID",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Handler CSV missing columns: {missing} | File: {path}")

    df["event_time"] = parse_mixed_datetime(df["OccurDateTime"])

    for col in ["MSGStartTime", "ResponseTime", "RepairTime"]:
        df[col] = clean_numeric(df[col])

    text_cols = [
        "Message",
        "MessageEn",
        "Area",
        "LotInfo",
        "AlarmCode",
        "Device",
        "HandlerID",
    ]

    for col in text_cols:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df["handler_clean"] = df["HandlerID"].apply(get_clean_handler)
    df["event_category"] = df.apply(categorize_handler_event, axis=1)

    # First-pass duration assumption.
    # Later validate whether MSGStartTime or RepairTime is the preferred downtime duration.
    df["duration_sec"] = df["MSGStartTime"].clip(lower=0)
    df["duration_min"] = df["duration_sec"] / 60
    df["event_hour"] = df["event_time"].dt.floor("h")

    df["source_csv_file"] = path.name
    df["source_csv_path"] = str(path)

    df["source_file_date"] = extract_date_from_filename(path.name)

    df = df.sort_values(
        ["HandlerID", "LotInfo", "event_time", "ID_EventLog"]
    ).reset_index(drop=True)

    return df


def load_handler_csv_folder(folder, target_date=None, start_date=None, end_date=None):
    if start_date is not None and end_date is not None:
        start_date = pd.Timestamp(start_date).normalize()
        end_date = pd.Timestamp(end_date).normalize()

        csv_files = []

        for d in pd.date_range(start_date, end_date, freq="D"):
            date_str = d.strftime("%Y%m%d")
            csv_files.extend(folder.rglob(f"MessageLog_{date_str}.csv"))

        csv_files = sorted(set(csv_files))

    elif target_date is not None:
        date_str = pd.Timestamp(target_date).strftime("%Y%m%d")
        csv_files = sorted(folder.rglob(f"MessageLog_{date_str}.csv"))

    else:
        csv_files = sorted(folder.rglob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {folder}")

    parts = []

    for p in csv_files:
        temp = load_handler_csv(p)
        parts.append(temp)

    df = pd.concat(parts, ignore_index=True)

    dedupe_cols = [
        "ID_EventLog",
        "OccurDateTime",
        "Message",
        "LotInfo",
        "HandlerID",
        "AlarmCode",
    ]

    existing_dedupe_cols = [c for c in dedupe_cols if c in df.columns]
    df = df.drop_duplicates(subset=existing_dedupe_cols).reset_index(drop=True)

    return df


# =====================================================
# PRODUCTION TXT PARSER
# =====================================================

def read_text_file_safely(path):
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        try:
            return path.read_text(encoding=enc, errors="ignore")
        except Exception:
            pass
    return path.read_text(errors="ignore")


def parse_txt_2d_list(path):
    """
    Parser for USI/SIP TXT files with structure:

    Schedule No. : 18UG73T246
    Handler Name : 1100-KDH02
    Start Time   : 2026-05-23 20:25:46
    End Time     : 2026-05-23 21:56:46

    ***** 2D List *****
    Flow  2D NO  TEST_ID SITE T.T HB SB Bin DESCRIPTION P/F DateTime MAC Address
     FT   serial+handler S5B0 236 1 11111111 Pass PASS 2026:05:23:20:32:24
    """

    text = read_text_file_safely(path)
    lines = text.splitlines()

    meta = {
        "source_file": path.name,
        "source_path": str(path),
        "customer": "",
        "schedule_no": "",
        "device_type": "",
        "lot_id": "",
        "station": "",
        "recipe": "",
        "series": "",
        "test_program": "",
        "handler_name": "",
        "handler_clean": "",
        "lot_start_time": "",
        "lot_end_time": "",
    }

    for line in lines[:100]:
        if ":" not in line:
            continue

        key, val = line.split(":", 1)
        key = key.strip().lower()
        val = val.strip()

        if key == "customer":
            meta["customer"] = val
        elif key == "schedule no.":
            meta["schedule_no"] = val
        elif key == "device type":
            meta["device_type"] = val
        elif key == "lot id":
            meta["lot_id"] = val
        elif key == "station":
            meta["station"] = val
        elif key == "recipe":
            meta["recipe"] = val
        elif key == "series":
            meta["series"] = val
        elif key == "test program":
            meta["test_program"] = val
        elif key == "handler name":
            meta["handler_name"] = val
            meta["handler_clean"] = get_clean_handler(val)
        elif key == "start time":
            meta["lot_start_time"] = val
        elif key == "end time":
            meta["lot_end_time"] = val

    start_idx = None
    for i, line in enumerate(lines):
        if "***** 2D List" in line:
            start_idx = i
            break

    if start_idx is None:
        return pd.DataFrame()

    rows = []

    # Start after section title and header line
    for line in lines[start_idx + 2:]:
        raw = line.rstrip()

        if not raw.strip():
            continue

        if raw.startswith("*****"):
            break

        # Example row:
        # FT 4Q9...1100-KDH02 S5B0 236 1 11111111 Pass PASS 2026:05:23:20:32:24
        m = re.match(
            r"^\s*"
            r"(?P<flow>\S+)\s+"
            r"(?P<serial_testid>\S+)\s+"
            r"(?P<site>\S+)\s+"
            r"(?P<tt>\d+(?:\.\d+)?)\s+"
            r"(?P<hb>\S+)\s+"
            r"(?P<sb>\S*)\s+"
            r"(?P<desc>.*?)\s+"
            r"(?P<pf>PASS|FAIL)\s+"
            r"(?P<dt>\d{4}:\d{2}:\d{2}:\d{2}:\d{2}:\d{2})"
            r"(?:\s+(?P<mac>.*))?"
            r"\s*$",
            raw
        )

        if not m:
            continue

        d = m.groupdict()
        serial_testid = d["serial_testid"]
        handler_name = meta["handler_name"]

        serial_no = serial_testid
        test_id = ""

        if handler_name and serial_testid.endswith(handler_name):
            serial_no = serial_testid[: -len(handler_name)]
            test_id = handler_name

        site_raw = d["site"]
        site_no = re.sub(r"\D", "", site_raw.split("B")[0])

        rows.append({
            **meta,
            "flow": d["flow"].strip().upper(),
            "serial_testid": serial_testid,
            "serial_no": serial_no,
            "test_id": test_id,
            "site": site_raw,
            "site_no": site_no,
            "test_time_sec": float(d["tt"]),
            "hb": d["hb"].strip(),
            "sb": d["sb"].strip(),
            "bin_description": d["desc"].strip(),
            "pf_status": d["pf"].strip().upper(),
            "test_datetime_raw": d["dt"],
            "mac_address": d.get("mac") or "",
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    df["test_datetime"] = pd.to_datetime(
        df["test_datetime_raw"],
        format="%Y:%m:%d:%H:%M:%S",
        errors="coerce"
    )

    df["lot_start_time"] = pd.to_datetime(df["lot_start_time"], errors="coerce")
    df["lot_end_time"] = pd.to_datetime(df["lot_end_time"], errors="coerce")

    return df


def load_all_txt_files(txt_folder):

    if not txt_folder.exists():
        raise FileNotFoundError(f"TXT_FOLDER does not exist: {txt_folder}")

    txt_files = sorted({
        p.resolve()
        for ext in ["*.txt", "*.log"]
        for p in txt_folder.rglob(ext)
        if any(stn in p.name for stn in ["STN1", "STN2", "STN3"])
    })

    if not txt_files:
        raise FileNotFoundError(f"No TXT/LOG files found in: {txt_folder}")

    prod_parts = []
    empty_files = []

    for p in txt_files:
        temp = parse_txt_2d_list(p)
        if not temp.empty:
            prod_parts.append(temp)
        else:
            empty_files.append(p.name)

    if not prod_parts:
        raise ValueError(
            "No production TXT rows parsed. Check TXT layout or parser. "
            f"Files scanned: {len(txt_files)}"
        )

    prod_raw = pd.concat(prod_parts, ignore_index=True)

    return prod_raw


# =====================================================
# PRODUCTION STANDARDIZATION
# =====================================================

def get_device_page_group(row):
    series = str(row.get("series", "")).strip().upper()
    recipe = str(row.get("recipe", "")).upper()
    station = str(row.get("station", "")).strip()

    if series in ["XU1", "XU2"]:
        if station == "1100":
            station_group = "STN2"
        elif station == "1101":
            station_group = "STN1"
        elif station == "1102":
            station_group = "STN3"
        else:
            station_group = "UNKNOWN"
    else:
        if "STN1" in recipe:
            station_group = "STN1"
        elif "STN2" in recipe:
            station_group = "STN2"
        elif "STN3" in recipe:
            station_group = "STN3"
        else:
            station_group = "UNKNOWN"

    if not series:
        series = "UNKNOWN_DEVICE"

    return f"{series}-{station_group}"


def standardize_prod_data(prod_raw):
    prod_df = prod_raw.copy()

    required_prod_cols = [
        "serial_no",
        "schedule_no",
        "flow",
        "pf_status",
        "site_no",
        "test_datetime",
        "test_time_sec",
        "sb",
    ]

    missing_prod_cols = [c for c in required_prod_cols if c not in prod_df.columns]
    if missing_prod_cols:
        raise ValueError(f"Production parsed data missing columns: {missing_prod_cols}")

    prod_df["schedule_no"] = prod_df["schedule_no"].fillna("").astype(str).str.strip()
    prod_df["lot_key"] = prod_df["schedule_no"]
    prod_df["serial_no"] = prod_df["serial_no"].fillna("").astype(str).str.strip()
    prod_df["flow_group"] = prod_df["flow"].fillna("").astype(str).str.upper().str.strip()

    prod_df["flow_group_raw"] = prod_df["flow_group"]
    prod_df["flow_group"] = np.where(
        prod_df["flow_group"].str.startswith("RT"),
        "RT",
        prod_df["flow_group"]
    )

    prod_df["pf_status"] = prod_df["pf_status"].fillna("").astype(str).str.upper().str.strip()
    prod_df["site_no"] = prod_df["site_no"].fillna("").astype(str).str.strip()
    prod_df["test_datetime"] = pd.to_datetime(prod_df["test_datetime"], errors="coerce")
    prod_df["test_time_sec"] = clean_numeric(prod_df["test_time_sec"])
    prod_df["errCode"] = prod_df["sb"].fillna("").astype(str).str.strip()
    prod_df["soft_bin"] = prod_df["sb"].fillna("").astype(str).str.strip()
    prod_df["test_hour"] = prod_df["test_datetime"].dt.floor("h")
    prod_df["device_page_group"] = prod_df.apply(get_device_page_group, axis=1)

    prod_df = prod_df.sort_values(
        ["schedule_no", "site_no", "test_datetime"]
    ).reset_index(drop=True)

    return prod_df


# =====================================================
# ANALYTICS
# =====================================================

def match_lots(handler_df, prod_df):
    handler_lots = set(handler_df["LotInfo"].dropna().astype(str).str.strip())
    prod_lots = set(prod_df["schedule_no"].dropna().astype(str).str.strip())

    matched_lots = sorted(handler_lots.intersection(prod_lots))

    print("\nHandler lots :", len(handler_lots))
    print("Prod lots    :", len(prod_lots))
    print("Matched lots :", len(matched_lots))
    print("Matched lot list:", matched_lots[:50])

    handler_matched = handler_df[handler_df["LotInfo"].isin(matched_lots)].copy()
    prod_matched = prod_df[prod_df["schedule_no"].isin(matched_lots)].copy()

    print("Matched handler rows:", len(handler_matched))
    print("Matched prod rows   :", len(prod_matched))

    if not matched_lots:
        print("\nWARNING: No matched lots found between Handler LotInfo and TXT Schedule No.")
        print("Handler sample lots:", sorted(list(handler_lots))[:20])
        print("Production sample lots:", sorted(list(prod_lots))[:20])

    return matched_lots, handler_matched, prod_matched


def build_lot_summary(handler_matched, prod_matched):
    handler_lot_summary = (
        handler_matched
        .groupby("LotInfo")
        .agg(
            handler_first_event=("event_time", "min"),
            handler_last_event=("event_time", "max"),
            handler_events=("ID_EventLog", "count"),
            handler_duration_min=("duration_min", "sum"),
        )
        .reset_index()
        .rename(columns={"LotInfo": "schedule_no"})
    )

    prod_lot_summary = (
        prod_matched
        .groupby("schedule_no")
        .agg(
            first_unit_time=("test_datetime", "min"),
            last_unit_time=("test_datetime", "max"),
            prod_rows=("serial_no", "count"),
            unique_serials=("serial_no", "nunique"),
            pass_units=("pf_status", lambda x: (x == "PASS").sum()),
            fail_units=("pf_status", lambda x: (x == "FAIL").sum()),
            total_test_sec=("test_time_sec", "sum"),
        )
        .reset_index()
    )

    lot_summary = handler_lot_summary.merge(
        prod_lot_summary,
        on="schedule_no",
        how="outer"
    )

    lot_summary["ramp_up_min"] = (
        lot_summary["first_unit_time"] - lot_summary["handler_first_event"]
    ).dt.total_seconds() / 60

    lot_summary["lot_span_min"] = (
        lot_summary["handler_last_event"] - lot_summary["handler_first_event"]
    ).dt.total_seconds() / 60

    lot_summary["tester_span_min"] = (
        lot_summary["last_unit_time"] - lot_summary["first_unit_time"]
    ).dt.total_seconds() / 60

    lot_summary["yield_pct"] = np.where(
        lot_summary["prod_rows"].fillna(0) > 0,
        lot_summary["pass_units"] / lot_summary["prod_rows"] * 100,
        np.nan
    )

    lot_summary = lot_summary.sort_values("handler_first_event")

    return lot_summary


def build_handler_category_summary(handler_matched):
    handler_category_summary = (
        handler_matched
        .groupby(["event_category"], dropna=False)
        .agg(
            events=("ID_EventLog", "count"),
            total_duration_min=("duration_min", "sum"),
            avg_duration_sec=("duration_sec", "mean"),
            max_duration_sec=("duration_sec", "max"),
        )
        .reset_index()
        .sort_values(["total_duration_min", "events"], ascending=False)
    )

    return handler_category_summary


def build_site_summary(prod_matched):
    prod_matched = prod_matched.sort_values(
        ["schedule_no", "site_no", "test_datetime"]
    ).copy()

    grp = ["schedule_no", "site_no"]

    prod_matched["prev_test_datetime"] = prod_matched.groupby(grp)["test_datetime"].shift(1)
    prod_matched["prev_test_time_sec"] = prod_matched.groupby(grp)["test_time_sec"].shift(1)

    prod_matched["time_diff_sec"] = (
        prod_matched["test_datetime"] - prod_matched["prev_test_datetime"]
    ).dt.total_seconds()

    prod_matched["index_gap_sec"] = prod_matched["time_diff_sec"] - prod_matched["prev_test_time_sec"]
    prod_matched["index_gap_sec"] = prod_matched["index_gap_sec"].clip(lower=0)

    site_summary = (
        prod_matched
        .groupby(["schedule_no", "site_no"])
        .agg(
            rows=("serial_no", "count"),
            unique_serials=("serial_no", "nunique"),
            pass_units=("pf_status", lambda x: (x == "PASS").sum()),
            fail_units=("pf_status", lambda x: (x == "FAIL").sum()),
            avg_test_time_sec=("test_time_sec", "mean"),
            p95_test_time_sec=("test_time_sec", lambda x: x.quantile(0.95)),
            max_test_time_sec=("test_time_sec", "max"),
            avg_index_gap_sec=("index_gap_sec", "mean"),
            p95_index_gap_sec=("index_gap_sec", lambda x: x.quantile(0.95)),
            max_index_gap_sec=("index_gap_sec", "max"),
        )
        .reset_index()
        .sort_values(["schedule_no", "p95_index_gap_sec"], ascending=[True, False])
    )

    return prod_matched, site_summary


def build_hourly_summaries(prod_matched, handler_matched):
    prod_hourly_summary = (
        prod_matched
        .dropna(subset=["test_hour"])
        .groupby(["test_hour", "schedule_no", "handler_clean", "device_page_group", "flow_group"], dropna=False)
        .agg(
            units=("serial_no", "count"),
            pass_units=("pf_status", lambda x: (x == "PASS").sum()),
            fail_units=("pf_status", lambda x: (x == "FAIL").sum()),
            total_test_sec=("test_time_sec", "sum"),
        )
        .reset_index()
        .sort_values(["test_hour", "schedule_no", "handler_clean", "flow_group"])
    )

    handler_hourly_summary = (
        handler_matched
        .dropna(subset=["event_hour"])
        .groupby(["event_hour", "HandlerID", "handler_clean", "event_category"], dropna=False)
        .agg(
            events=("ID_EventLog", "count"),
            total_duration_min=("duration_min", "sum"),
        )
        .reset_index()
        .sort_values(["event_hour", "handler_clean", "event_category"])
    )

    return prod_hourly_summary, handler_hourly_summary

def get_rolling_7day_window(report_date):
    report_date = pd.Timestamp(report_date).normalize()
    start_date = report_date - pd.Timedelta(days=6)
    end_date = report_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    return start_date, end_date

# =====================================================
# PLOTTING - OVERALL + PER HANDLER HTML REPORTS
# =====================================================

def build_oee_visual_reports(prod_matched, handler_matched, out_dir, report_day_start):
    prod_matched = prod_matched.copy()
    handler_matched = handler_matched.copy()

    handler_count = (
        prod_matched["handler_clean"]
        .dropna()
        .nunique()
    )

    OVERALL_TARGET_UPH = None

    print(f"Handler count: {handler_count}")
    print("Target UPH: disabled / pending ideal test + index time")

    PASS_COLOR = "#A8DDB5" 
    FAIL_COLOR = "#F4A6A6"

    # Row 3 uptime split

    UPTIME_COLOR = "#A8DDB5"
    RETEST_TIME_COLOR = "#4CAF50"

    RYG_RED = "#D73027"
    RYG_YELLOW = "#FEE08B"
    RYG_GREEN = "#1A9850"

    EVENT_COLOR_MAP = {
        "PAUSE": "#F4A582",
        "ACCESS_GUARD_INTERRUPTION": "#D6604D",
        "SAFETY_DOOR": "#B2182B",
        "ROBOT_ARM_NOT_READY": "#B2ABD2",
        "VACUUM_ERROR": "#8073AC",
        "VISION_ERROR": "#542788",
        "TESTER_NG": "#92C5DE",
        "BINNING_TIMEOUT": "#4393C3",
        "DUT_SENSOR_FAIL": "#2166AC",
        "NEST_FAIL": "#FDDDBF",
        "LOADER_EVENT": "#FDAE61",
        "LOT_MOVE_IN": "#F46D43",
        "LOT_MOVE_OUT": "#D53E4F",
        "LOT_MOVE_OUT_START": "#9E0142",
        "SUMMARY_OUTPUT": "#E6F598",
        "SUMMARY_RETEST": "#FEE08B",
        "SUMMARY_RUN_TIME": "#D9EF8B",
        "SUMMARY_UPH": "#ABDDA4",
        "SITE_STATUS": "#CCCCCC",
        "SITE_USE_RATE": "#999999",
        "TESTER_RESULT_FAIL": "#C51B7D",
        "CLOSE_SITE_ASSIST": "#8C6BB1",
        "OPEN_SITE_ASSIST": "#9E9AC8",
        "OTHER": "#BDBDBD",
        "HANDLER_LOAD_UNLOAD": "#FDAE61",
        "TEST_SITE_A_REPEAT_FAIL": "#1F78B4",
        "TEST_SITE_B_REPEAT_FAIL": "#4D4D4D",
    }

    def get_event_color(category):
        return EVENT_COLOR_MAP.get(str(category), "#BDBDBD")

    def get_ryg_color(value):
        if value < 80:
            return RYG_RED
        elif value < 90:
            return RYG_YELLOW
        else:
            return RYG_GREEN


    def calc_oee_metrics(
        output_pivot,
        efficiency_pct,
        target_uph
    ):
        availability_pct = (
            float(efficiency_pct["UP_TIME"].mean())
            if "UP_TIME" in efficiency_pct.columns
            else 0.0
        )

        total_units = float(output_pivot["TOTAL"].sum())
        pass_units = float(output_pivot["PASS"].sum())

        quality_pct = (
            pass_units / total_units * 100
            if total_units > 0
            else 0.0
        )

        if "TARGET_UPH_ACTIVE_SITES" in output_pivot.columns:
            actual_units = output_pivot["TOTAL"].sum()
            target_units = output_pivot["TARGET_UPH_ACTIVE_SITES"].sum()

            performance_pct = (
                actual_units / target_units * 100
                if target_units > 0
                else 0.0
            )
        else:
            performance_pct = 0.0

        performance_pct = min(performance_pct, 100.0)

        oee_pct = (
            availability_pct / 100
            * performance_pct / 100
            * quality_pct / 100
            * 100
        )

        return {
            "OEE": oee_pct,
            "Availability": availability_pct,
            "performance": performance_pct,
            "Quality": quality_pct,
        }

    def build_hourly_data(p_prod, h_events):

        report_start = pd.Timestamp(report_day_start).normalize()

        all_hours = pd.date_range(
            report_start,
            report_start + pd.Timedelta(hours=23),
            freq="h"
        )

        output_hourly = (
            p_prod
            .dropna(subset=["test_hour"])
            .groupby(["test_hour", "pf_status"])
            .agg(units=("serial_no", "count"))
            .reset_index()
        )

        output_pivot = (
            output_hourly
            .pivot_table(
                index="test_hour",
                columns="pf_status",
                values="units",
                aggfunc="sum",
                fill_value=0
            )
            .reindex(all_hours, fill_value=0)
        )

        # --------------------------------------------------
        # Active sites per hour + dynamic ideal UPH per hour
        # Count sites per handler first, then sum across handlers.
        # --------------------------------------------------
        active_sites_by_handler_hour = (
            p_prod
            .dropna(subset=["test_hour"])
            .groupby(["test_hour", "handler_clean"])["site_no"]
            .nunique()
            .reset_index(name="active_sites")
        )

        # active_sites_hourly = (
        #     active_sites_by_handler_hour
        #     .groupby("test_hour")["active_sites"]
        #     .sum()
        #     .reindex(all_hours, fill_value=0)
        # )

        # target_uph_hourly = (
        #     3600
        #     * active_sites_hourly
        #     * (IDEAL_YIELD / 100)
        #     / (IDEAL_TEST_TIME + IDEAL_INDEX_TIME)
        # )

        target_uph_fixed = (
            TARGET_OEE
            * MAX_TEST_SITE_QTY
            * 3600
            / (IDEAL_TEST_TIME + IDEAL_INDEX_TIME)
        )

        target_uph_hourly = pd.Series(
            target_uph_fixed,
            index=all_hours
        )

        target_upd_fixed = target_uph_fixed * 24

        # output_pivot["ACTIVE_SITES"] = active_sites_hourly
        output_pivot["TARGET_UPH_ACTIVE_SITES"] = target_uph_hourly

        for col in ["PASS", "FAIL"]:
            if col not in output_pivot.columns:
                output_pivot[col] = 0

        output_pivot["TOTAL"] = output_pivot["PASS"] + output_pivot["FAIL"]

        flow_count_hourly = (
            p_prod
            .dropna(subset=["test_hour"])
            .groupby(["test_hour", "flow_group"])
            .agg(units=("serial_no", "count"))
            .reset_index()
        )

        flow_count_pivot = (
            flow_count_hourly
            .pivot_table(
                index="test_hour",
                columns="flow_group",
                values="units",
                aggfunc="sum",
                fill_value=0
            )
            .reindex(all_hours, fill_value=0)
        )

        for flow_col in ["FT", "RT"]:
            if flow_col not in flow_count_pivot.columns:
                flow_count_pivot[flow_col] = 0

        output_pivot["FT_UNITS"] = flow_count_pivot["FT"]
        output_pivot["RT_UNITS"] = flow_count_pivot["RT"]

        event_hourly = (
            h_events
            .dropna(subset=["event_hour"])
            .groupby(["event_hour", "event_category"])
            .agg(duration_sec=("duration_sec", "sum"))
            .reset_index()
        )

        event_pivot_sec = (
            event_hourly
            .pivot_table(
                index="event_hour",
                columns="event_category",
                values="duration_sec",
                aggfunc="sum",
                fill_value=0
            )
            .reindex(all_hours, fill_value=0)
        )

        raw_total_event_sec = event_pivot_sec.sum(axis=1)

        scale_factor = pd.Series(
            np.where(raw_total_event_sec > 3600, 3600 / raw_total_event_sec, 1),
            index=event_pivot_sec.index
        )

        event_pivot_sec_scaled = event_pivot_sec.mul(scale_factor, axis=0)

        total_event_sec = event_pivot_sec_scaled.sum(axis=1).clip(upper=3600)
        uptime_sec = (3600 - total_event_sec).clip(lower=0)

        efficiency_pct = event_pivot_sec_scaled.div(3600).mul(100)

        # --------------------------------------------------
        # Split available UP_TIME into:
        # - UP_TIME      = FT / first-pass production share
        # - RETEST_TIME  = RT / retest production share
        #
        # Note:
        # We split the original available uptime by FT vs RT test-time ratio.
        # This preserves the original 100% hourly stack logic.
        # --------------------------------------------------

        flow_hourly_sec = (
            p_prod
            .dropna(subset=["test_hour"])
            .groupby(["test_hour", "flow_group"])
            .agg(flow_test_sec=("test_time_sec", "sum"))
            .reset_index()
        )

        flow_pivot_sec = (
            flow_hourly_sec
            .pivot_table(
                index="test_hour",
                columns="flow_group",
                values="flow_test_sec",
                aggfunc="sum",
                fill_value=0
            )
            .reindex(all_hours, fill_value=0)
        )

        for flow_col in ["FT", "RT"]:
            if flow_col not in flow_pivot_sec.columns:
                flow_pivot_sec[flow_col] = 0

        ft_sec = flow_pivot_sec["FT"]
        rt_sec = flow_pivot_sec["RT"]
        total_prod_flow_sec = ft_sec + rt_sec

        ft_share = np.where(
            total_prod_flow_sec > 0,
            ft_sec / total_prod_flow_sec,
            1.0
        )

        rt_share = np.where(
            total_prod_flow_sec > 0,
            rt_sec / total_prod_flow_sec,
            0.0
        )

        available_pct = uptime_sec / 3600 * 100

        # If no units were tested in that hour, show 0% instead of fake 100% uptime
        has_output = output_pivot["TOTAL"] > 0
        available_pct = available_pct.where(has_output, 0)

        efficiency_pct["UP_TIME"] = available_pct * ft_share
        efficiency_pct["RETEST_TIME"] = available_pct * rt_share

        keep_cols = [
            "UP_TIME",
            "RETEST_TIME",
            "PAUSE",
            "ACCESS_GUARD_INTERRUPTION",
            "SAFETY_DOOR",
            "ROBOT_ARM_NOT_READY",
            "VACUUM_ERROR",
            "VISION_ERROR",
            "TESTER_NG",
            "HANDLER_LOAD_UNLOAD",
            "TESTA_CONTINUOUS_NG_FAIL",
            "TESTB_CONTINUOUS_NG_FAIL",
            "BINNING_TIMEOUT",
            "DUT_SENSOR_FAIL",
            "NEST_FAIL",
            "LOADER_EVENT",
            "LOT_MOVE_IN",
            "LOT_MOVE_OUT",
            "LOT_MOVE_OUT_START",
            "SITE_STATUS",
            "SITE_USE_RATE",
            "TESTER_RESULT_FAIL",
            "CLOSE_SITE_ASSIST",
            "OPEN_SITE_ASSIST",
            "OTHER",
        ]

        for col in keep_cols:
            if col not in efficiency_pct.columns:
                efficiency_pct[col] = 0

        efficiency_pct = efficiency_pct[keep_cols]

        nonzero_cols = [
            col for col in efficiency_pct.columns
            if col == "UP_TIME" or efficiency_pct[col].sum() > 0
        ]

        efficiency_pct = efficiency_pct[nonzero_cols]

        return all_hours, output_pivot, event_pivot_sec_scaled, efficiency_pct

    def make_gauge_fig(metrics, title):
        fig = go.Figure()

        gauge_items = [
            ("OEE", metrics["OEE"], [0.00, 0.22]),
            ("Utilization", metrics["Availability"], [0.26, 0.48]),
            ("Output Attainment", metrics["performance"], [0.52, 0.74]),
            ("Yield", metrics["Quality"], [0.78, 1.00]),
        ]

        for label, value, domain_x in gauge_items:
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=value,
                    title=dict(text=label, font=dict(size=15)),
                    number=dict(suffix="%", font=dict(size=24)),
                    gauge=dict(
                        axis=dict(range=[0, 100]),
                        bar=dict(color=get_ryg_color(value)),
                        bgcolor="#FFFFFF",
                        borderwidth=1,
                        bordercolor="#CCCCCC",
                    ),
                    domain=dict(x=domain_x, y=[0, 1])
                )
            )

        fig.update_layout(
            # title=dict(
            #     text=f"<b>{title}</b>",
            #     x=0.01,
            #     xanchor="left",
            #     font=dict(size=20)
            # ),
            title=None,
            height=260,
            margin=dict(l=30, r=30, t=55, b=20),
            paper_bgcolor=PLOT_BG,
            font=dict(family="Arial", color="#222222"),
        )

        return fig

    def make_output_fig(
        output_pivot,
        all_hours,
        target_uph
    ):
        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=output_pivot.index,
                y=output_pivot["PASS"],
                name="PASS",
                marker_color=PASS_COLOR,
                text=output_pivot["PASS"].astype(int),
                textposition="inside",
                textfont=dict(size=11),
                insidetextfont=dict(size=11),
                hovertemplate="Hour: %{x}<br>PASS: %{y}<extra></extra>",
            )
        )

        fig.add_trace(
            go.Bar(
                x=output_pivot.index,
                y=output_pivot["FAIL"],
                name="FAIL",
                marker_color=FAIL_COLOR,
                text=output_pivot["FAIL"].astype(int),
                textposition="outside",
                textangle=0,
                textfont=dict(size=11, color="#222222"),
                cliponaxis=False,
                hovertemplate=(
                    "<b>Hour:</b> %{x|%H:%M}<br>"
                    "<b>FAIL:</b> %{y}<extra></extra>"
                ),
            )
        )

        if "TARGET_UPH_ACTIVE_SITES" in output_pivot.columns:

            target_uph_display = int(
                round(output_pivot["TARGET_UPH_ACTIVE_SITES"].dropna().iloc[0])
            )

            fig.add_trace(
                go.Scatter(
                    x=all_hours,
                    y=output_pivot["TARGET_UPH_ACTIVE_SITES"],
                    mode="lines",
                    name=f"Target UPH @ 80% OEE ({target_uph_display})",
                    opacity=0.75,
                    line=dict(
                        color="black",
                        width=1.5,
                        dash="dash",
                    ),
                    hovertemplate=(
                        "<b>Hour:</b> %{x|%H:%M}<br>"
                        "<b>Target UPH:</b> %{y:.1f}<br>"
                        "<extra></extra>"
                    ),
                )
            )

        fig.update_layout(
            title=dict(
                text="<b>Output count per hour</b>",
                x=0.01,
                xanchor="left"
            ),
            height=390,
            barmode="stack",
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial",
                font_color="#222222",
                bordercolor="#BDBDBD",
            ),
            # margin=dict(l=70, r=30, t=175, b=35),
            bargap=0.15,
            uniformtext=dict(minsize=11, mode="show"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.08,
                xanchor="left",
                x=0,
                title_text=""
            ),
            margin=dict(l=70, r=30, t=105, b=35),
            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(family="Arial", color="#222222"),
        )

        fig.update_yaxes(title_text="Units", gridcolor="#E5E5E5")
        fig.update_xaxes(
            tickmode="array",
            tickvals=all_hours,
            ticktext=[
                f"<b>{pd.Timestamp(h).strftime('%m/%d')}</b><br>{pd.Timestamp(h).strftime('%H:%M')}"
                for h in all_hours
            ],
            tickangle=0,
            tickfont=dict(size=9, color="black"),
            automargin=True,
            gridcolor="#E5E5E5",
        )

        return fig

    def make_efficiency_fig(efficiency_pct, all_hours, hour_lot_map=None):
        fig = go.Figure()

        for col in efficiency_pct.columns:
            if col == "UP_TIME":
                color = UPTIME_COLOR
            elif col == "RETEST_TIME":
                color = RETEST_TIME_COLOR
            else:
                color = get_event_color(col)

            if col == "UP_TIME":
                bar_text = efficiency_pct[col].round(1).astype(str) + "%"
                text_position = "inside"
                text_font = dict(size=10, color="#222222")
            else:
                bar_text = None
                text_position = None
                text_font = None

            if col == "UP_TIME":
                hover_icon = "🟢"
            elif col == "RETEST_TIME":
                hover_icon = "♻️"
            else:
                hover_icon = "🛑"

            fig.add_trace(
                go.Bar(
                    x=efficiency_pct.index,
                    y=efficiency_pct[col],
                    name=col,
                    marker_color=color,
                    text=bar_text,
                    textposition=text_position,
                    textfont=text_font,
                    insidetextfont=text_font,
                    textangle=0,
                    constraintext="none",
                    hovertemplate=(
                        "<b>⏱️ Hour:</b> %{x|%H:%M}<br>"
                        f"<b>{hover_icon} {col}:</b> %{{y:.2f}}%"
                        "<extra></extra>"
                    ),
                )
            )

        fig.update_layout(
            title=dict(
                text="<b>Efficiency % per hour</b>",
                x=0.01,
                xanchor="left"
            ),
            height=540,
            barmode="stack",
            hovermode="closest",
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial",
                font_color="#222222",
                bordercolor="#BDBDBD",
            ),
            margin=dict(l=70, r=30, t=60, b=230),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.58,
                xanchor="left",
                x=0,
                title_text="",
                font=dict(size=10)
            ),
            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(family="Arial", color="#222222"),
        )

        fig.update_yaxes(title_text="% of hour", range=[0, 100], gridcolor="#E5E5E5")

        fig.update_xaxes(
            title_text="",
            tickmode="array",
            tickvals=all_hours,
            ticktext=[
                f"<b>{pd.Timestamp(h).strftime('%m/%d')}</b><br>{pd.Timestamp(h).strftime('%H:%M')}"
                for h in all_hours
            ],
            tickangle=0,
            tickfont=dict(size=9, color="black"),
            automargin=True,
            gridcolor="#E5E5E5",
        )

        fig.add_annotation(
            x=-0.055,
            y=-0.105,
            xref="paper",
            yref="paper",
            text="<b>Date</b>",
            showarrow=False,
            xanchor="right",
            yanchor="top",
            font=dict(size=9, color="black"),
        )

        fig.add_annotation(
            x=-0.055,
            y=-0.155,
            xref="paper",
            yref="paper",
            text="<b>Time</b>",
            showarrow=False,
            xanchor="right",
            yanchor="top",
            font=dict(size=9, color="black"),
        )

        fig.add_annotation(
            x=-0.055,
            y=-0.225,
            xref="paper",
            yref="paper",
            text="<b>Lot</b>",
            showarrow=False,
            xanchor="right",
            yanchor="top",
            font=dict(size=9, color="black"),
        )

        if hour_lot_map is not None:
            for hour in all_hours:
                lot_no = hour_lot_map.get(hour, "")
                if not lot_no:
                    continue

                fig.add_annotation(
                    x=hour,
                    y=-0.23,
                    xref="x",
                    yref="paper",
                    text=str(lot_no),
                    showarrow=False,
                    textangle=-45,
                    xanchor="center",
                    yanchor="top",
                    font=dict(size=9, color="black"),
                )

        return fig

    def make_event_summary_fig(event_pivot_sec_scaled, total_available_sec, top_n=None):
        event_summary = (
            event_pivot_sec_scaled
            .drop(columns=["UP_TIME"], errors="ignore")
            .sum()
            .reset_index()
        )

        event_summary.columns = ["event_category", "total_sec"]
        event_summary["total_pct_available"] = event_summary["total_sec"] / total_available_sec * 100
        event_summary = event_summary[event_summary["total_pct_available"] > 0].copy()
        event_summary = event_summary.sort_values("total_pct_available", ascending=False)

        if top_n is not None:
            event_summary = event_summary.head(top_n)

        event_summary = event_summary.sort_values("total_pct_available", ascending=True)

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                y=event_summary["event_category"],
                x=event_summary["total_pct_available"],
                orientation="h",
                marker_color=[get_event_color(cat) for cat in event_summary["event_category"]],
                text=event_summary["total_pct_available"].round(2).astype(str) + "%",
                textposition="outside",
                textfont=dict(size=9),
                hovertemplate=(
                    "<b>🛠️ Event:</b> %{y}<br>"
                    "<b>📉 Loss:</b> %{x:.2f}% of available hours"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )

        fig.update_layout(
            title=dict(
                text="<b>Top 10 Handler Event Summary (% of available hours)</b>",
                x=0.01,
                xanchor="left"
            ),
            height=340,
            hovermode="closest",
            margin=dict(l=260, r=80, t=60, b=50),
            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(family="Arial", color="#222222"),
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial",
                font_color="#222222",
                bordercolor="#BDBDBD",
            ),
        )

        fig.update_xaxes(title_text="% of available hours", gridcolor="#E5E5E5")
        fig.update_yaxes(title_text="")

        return fig

    def make_handler_downtime_table(handler_df):
        summary = (
            handler_df
            .groupby("handler_clean", dropna=False)
            .agg(
                total_events=("ID_EventLog", "count"),
                total_downtime_min=("duration_min", "sum"),
            )
            .reset_index()
        )

        top_event = (
            handler_df
            .groupby(["handler_clean", "event_category"], dropna=False)
            .agg(event_downtime_min=("duration_min", "sum"))
            .reset_index()
            .sort_values(["handler_clean", "event_downtime_min"], ascending=[True, False])
        )

        top_event = top_event.drop_duplicates("handler_clean")[["handler_clean", "event_category"]]

        summary = summary.merge(top_event, on="handler_clean", how="left")
        summary = summary.sort_values("total_downtime_min", ascending=False)

        fig = go.Figure(
            data=[
                go.Table(
                    header=dict(
                        values=[
                            "<b>Handler</b>",
                            "<b>Total Events</b>",
                            "<b>Total Downtime Min</b>",
                            "<b>Top Event</b>",
                        ],
                        fill_color="#F2F2F2",
                        align="left",
                        font=dict(color="#222222", size=12),
                        line_color="#BDBDBD",
                        line_width=1,
                    ),
                    cells=dict(
                        values=[
                            summary["handler_clean"],
                            summary["total_events"].astype(int),
                            summary["total_downtime_min"].round(1),
                            summary["event_category"],
                        ],
                        fill_color="#FFFFFF",
                        align="left",
                        font=dict(color="#222222", size=11),
                        height=26,                     
                        line_color="#D0D0D0",
                        line_width=1,
                    )
                )
            ]
        )

        fig.update_layout(
            title=dict(
                text="<b>Total downtime by handler</b>",
                x=0.01,
                xanchor="left"
            ),
            height=340,
            margin=dict(l=20, r=20, t=60, b=20),
            paper_bgcolor=PLOT_BG,
            font=dict(family="Arial", color="#222222"),
        )

        return fig

    def make_event_downtime_table(handler_df):
        summary = (
            handler_df
            .groupby("event_category", dropna=False)
            .agg(
                event_occurrences=("ID_EventLog", "count"),
                lost_sec=("duration_sec", "sum"),
            )
            .reset_index()
        )

        summary = summary[summary["lost_sec"] > 0].copy()
        summary = summary.sort_values("lost_sec", ascending=False).reset_index(drop=True)

        if summary.empty:
            summary = pd.DataFrame({
                "event_category": ["NO_LOSS_RECORDED"],
                "event_occurrences": [0],
                "lost_sec": [0],
            })

        summary["rank"] = summary.index + 1

        max_lost_sec = summary["lost_sec"].max()

        summary["lost_time_bar"] = summary.apply(
            lambda r: make_html_bar_label(
                r["lost_sec"],
                max_lost_sec,
                format_duration_hms(r["lost_sec"]),
                width=18,
                color="#D95F5F"
            ),
            axis=1
        )

        fig = go.Figure(
            data=[
                go.Table(
                    columnwidth=[45, 260, 260, 120],
                    header=dict(
                        values=[
                            "<b>Rank</b>",
                            "<b>Handler Event</b>",
                            "<b>Lost Time</b>",
                            "<b>Event Occurrences</b>",
                        ],
                        fill_color="#F2F2F2",
                        align="left",
                        font=dict(color="#222222", size=12),
                        line_color="#BDBDBD",
                        line_width=1,
                    ),
                    cells=dict(
                        values=[
                            summary["rank"],
                            summary["event_category"],
                            summary["lost_time_bar"],
                            summary["event_occurrences"].astype(int),
                        ],
                        fill_color="#FFFFFF",
                        align="left",
                        font=dict(
                            color=[
                                "black",
                                "black",
                                "#D95F5F",
                                "black",
                            ],
                            size=11
                        ),
                        height=28,
                        line_color="#D0D0D0",
                        line_width=1,
                    )
                )
            ]
        )

        fig.update_layout(
            title=dict(
                text="<b>Total downtime by handler event</b>",
                x=0.01,
                xanchor="left"
            ),
            height=360,
            margin=dict(l=20, r=30, t=60, b=20),
            paper_bgcolor=PLOT_BG,
            font=dict(family="Arial", color="#222222"),
        )

        return fig

    def html_header(title, subtitle):
        return f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background: #FAFAFA;
                    color: #222222;
                }}
                .report-header {{
                    background: #F2F2F2;
                    border-left: 8px solid #444444;
                    padding: 18px 22px;
                    margin-bottom: 18px;
                }}
                .report-title {{
                    font-size: 26px;
                    font-weight: 700;
                    margin-bottom: 6px;
                    letter-spacing: 0.3px;
                }}
                .report-subtitle {{
                    font-size: 14px;
                    color: #555555;
                }}
                h2 {{
                    margin-top: 28px;
                    padding-top: 14px;
                    border-top: 2px solid #DDDDDD;
                    font-size: 20px;
                }}
                .chart-block {{
                    background: #FFFFFF;
                    padding: 10px;
                    margin-bottom: 16px;
                    border: 1px solid #E0E0E0;
                }}
                .row4-grid {{
                    display: grid;
                    grid-template-columns: 1.35fr 1fr;
                    gap: 12px;
                    align-items: start;
                }}
                @media (max-width: 1200px) {{
                    .row4-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="report-header">
                <div class="report-title">{title}</div>
                <div class="report-subtitle">{subtitle}</div>
            </div>
        """

    def html_footer():
        return "</body></html>"

    def add_section(html_parts, section_title, p_prod, h_events, target_uph, overall=False):
        if p_prod.empty or h_events.empty:
            return

        all_hours, output_pivot, event_pivot_sec_scaled, efficiency_pct = build_hourly_data(
            p_prod,
            h_events
        )

        total_available_sec = len(all_hours) * 3600

        # --------------------------------------------------
        # Lot labels shown below Row 3 chart
        # --------------------------------------------------

        p_prod["mother_lot"] = (
            p_prod["schedule_no"]
            .fillna("")
            .astype(str)
            .str[:6]
        )

        if overall:

            hour_lot_map = (
                p_prod
                .dropna(subset=["test_hour"])
                .groupby("test_hour")["mother_lot"]
                .agg(
                    lambda x: "<br>".join(
                        sorted(x.dropna().unique())[:3]
                    )
                )
                .to_dict()
            )

        else:

            hour_lot_map = (
                p_prod
                .dropna(subset=["test_hour"])
                .groupby("test_hour")["schedule_no"]
                .agg(
                    lambda x: (
                        x.value_counts().index[0]
                        if len(x.dropna())
                        else ""
                    )
                )
                .to_dict()
            )

        metrics = calc_oee_metrics(output_pivot, efficiency_pct, target_uph)

        fig_gauge = make_gauge_fig(metrics, section_title)
        fig_output = make_output_fig(output_pivot, all_hours, target_uph)
        fig_eff = make_efficiency_fig(
            efficiency_pct,
            all_hours,
            hour_lot_map
        )

        if overall:
            fig_event = make_event_summary_fig(
                event_pivot_sec_scaled,
                total_available_sec,
                top_n=10
            )
            fig_table = make_handler_downtime_table(h_events)
        else:
            fig_event = make_event_summary_fig(
                event_pivot_sec_scaled,
                total_available_sec,
                top_n=10
            )
            fig_table = make_event_downtime_table(h_events)

        html_parts.append(f"<h2>{section_title}</h2>")
        html_parts.append("<div class='chart-block'>")
        html_parts.append(to_html(fig_gauge, include_plotlyjs="cdn", full_html=False))
        html_parts.append(to_html(fig_output, include_plotlyjs=False, full_html=False))
        html_parts.append(to_html(fig_eff, include_plotlyjs=False, full_html=False))
        html_parts.append("<div class='row4-grid'>")
        html_parts.append(to_html(fig_event, include_plotlyjs=False, full_html=False))
        html_parts.append(to_html(fig_table, include_plotlyjs=False, full_html=False))
        html_parts.append("</div>")
        html_parts.append("</div>")

    report_date = (
        prod_matched["test_datetime"].max().strftime("%m/%d/%Y")
        if prod_matched["test_datetime"].notna().any()
        else "Unknown Date"
    )

    page_group_title = (
        prod_matched["device_page_group"]
        .dropna()
        .mode()
        .iloc[0]
        if not prod_matched["device_page_group"].dropna().empty
        else "UNKNOWN"
    )

    # =====================================================
    # EXPORT 2: ONE HTML REPORT PER HANDLER
    # =====================================================

    handlers = sorted(prod_matched["handler_clean"].dropna().unique())

    for handler_clean in handlers:
        p_prod = prod_matched[
            prod_matched["handler_clean"].astype(str) == str(handler_clean)
        ].copy()

        h_events = handler_matched[
            handler_matched["handler_clean"].astype(str) == str(handler_clean)
        ].copy()

        if p_prod.empty or h_events.empty:
            print(f"Skipping handler {handler_clean}: missing production or handler events")
            continue

        handler_html = []

        handler_html.append(
            html_header(
                title=f"🔧 {handler_clean} - 24H OEE REPORT ({report_date})",
                subtitle=(
                    f"📊 Handler-level production, active-site target UPH, efficiency loss, and downtime analysis"
                )
            )
        )

        add_section(
            html_parts=handler_html,
            section_title=f"Handler {handler_clean}",
            p_prod=p_prod,
            h_events=h_events,
            # target_uph=PER_HANDLER_TARGET_UPH,
            target_uph=None,
            overall=False,
        )

        handler_html.append(html_footer())

        handler_safe_name = safe_filename(handler_clean)

        handler_path = out_dir / f"oee_per_handler_report_{handler_safe_name}.html"
        handler_path.write_text("".join(handler_html), encoding="utf-8")

        print(f"Saved per-handler OEE report: {handler_path}")

def format_duration_hms(seconds):
    seconds = int(round(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def make_bar_label(value, max_value, label, width=18):
    if max_value <= 0:
        blocks = 0
    else:
        blocks = int(round((value / max_value) * width))

    blocks = max(1, blocks) if value > 0 else 0
    return f"{'█' * blocks} {label}"

def make_html_bar_label(value, max_value, label, width=18, color="#D95F5F"):
    if max_value <= 0:
        blocks = 0
    else:
        blocks = int(round((value / max_value) * width))

    blocks = max(1, blocks) if value > 0 else 0
    return f"{'█' * blocks} {label}"

def build_rolling_7day_report(
    prod_df,
    handler_df,
    out_dir,
    rolling_start_date,
    rolling_end_date,
):
    prod_df = prod_df.copy()
    handler_df = handler_df.copy()

    rolling_start_date = pd.Timestamp(rolling_start_date).normalize()
    rolling_end_date = pd.Timestamp(rolling_end_date).normalize()
    rolling_day_end = rolling_end_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    prod_df = prod_df[
        (prod_df["test_datetime"] >= rolling_start_date) &
        (prod_df["test_datetime"] <= rolling_day_end)
    ].copy()

    handler_df = handler_df[
        (handler_df["event_time"] >= rolling_start_date) &
        (handler_df["event_time"] <= rolling_day_end)
    ].copy()

    if prod_df.empty or handler_df.empty:
        print("Skipping rolling 7-day report: no production or handler data.")
        return

    prod_df["report_day"] = prod_df["test_datetime"].dt.floor("D")
    handler_df["report_day"] = handler_df["event_time"].dt.floor("D")

    all_days = pd.date_range(rolling_start_date, rolling_end_date, freq="D")

    target_uph = (
        TARGET_OEE
        * MAX_TEST_SITE_QTY
        * 3600
        / (IDEAL_TEST_TIME + IDEAL_INDEX_TIME)
    )
    target_upd = target_uph * 24

    def build_daily_metrics(p_prod, h_events):
        rows = []
        event_pivot_days = []

        for report_day in all_days:
            day_start = pd.Timestamp(report_day).normalize()
            day_end = day_start + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

            day_hours = pd.date_range(day_start, day_start + pd.Timedelta(hours=23), freq="h")

            p_day = p_prod[
                (p_prod["test_datetime"] >= day_start) &
                (p_prod["test_datetime"] <= day_end)
            ].copy()

            h_day = h_events[
                (h_events["event_time"] >= day_start) &
                (h_events["event_time"] <= day_end)
            ].copy()

            output_hourly = (
                p_day
                .dropna(subset=["test_hour"])
                .groupby(["test_hour", "pf_status"])
                .agg(units=("serial_no", "count"))
                .reset_index()
            )

            output_pivot = (
                output_hourly
                .pivot_table(
                    index="test_hour",
                    columns="pf_status",
                    values="units",
                    aggfunc="sum",
                    fill_value=0
                )
                .reindex(day_hours, fill_value=0)
            )

            for col in ["PASS", "FAIL"]:
                if col not in output_pivot.columns:
                    output_pivot[col] = 0

            output_pivot["TOTAL"] = output_pivot["PASS"] + output_pivot["FAIL"]

            event_hourly = (
                h_day
                .dropna(subset=["event_hour"])
                .groupby(["event_hour", "event_category"])
                .agg(duration_sec=("duration_sec", "sum"))
                .reset_index()
            )

            event_pivot_sec = (
                event_hourly
                .pivot_table(
                    index="event_hour",
                    columns="event_category",
                    values="duration_sec",
                    aggfunc="sum",
                    fill_value=0
                )
                .reindex(day_hours, fill_value=0)
            )

            raw_total_event_sec = event_pivot_sec.sum(axis=1)

            scale_factor = pd.Series(
                np.where(raw_total_event_sec > 3600, 3600 / raw_total_event_sec, 1),
                index=event_pivot_sec.index
            )

            event_pivot_sec_scaled = event_pivot_sec.mul(scale_factor, axis=0)

            total_event_sec = event_pivot_sec_scaled.sum(axis=1).clip(upper=3600)
            uptime_sec = (3600 - total_event_sec).clip(lower=0)

            flow_hourly_sec = (
                p_day
                .dropna(subset=["test_hour"])
                .groupby(["test_hour", "flow_group"])
                .agg(flow_test_sec=("test_time_sec", "sum"))
                .reset_index()
            )

            flow_pivot_sec = (
                flow_hourly_sec
                .pivot_table(
                    index="test_hour",
                    columns="flow_group",
                    values="flow_test_sec",
                    aggfunc="sum",
                    fill_value=0
                )
                .reindex(day_hours, fill_value=0)
            )

            for flow_col in ["FT", "RT"]:
                if flow_col not in flow_pivot_sec.columns:
                    flow_pivot_sec[flow_col] = 0

            ft_sec = flow_pivot_sec["FT"]
            rt_sec = flow_pivot_sec["RT"]
            total_flow_sec = ft_sec + rt_sec

            ft_share = np.where(
                total_flow_sec > 0,
                ft_sec / total_flow_sec,
                1.0
            )

            has_output = output_pivot["TOTAL"] > 0

            available_pct = uptime_sec / 3600 * 100
            available_pct = available_pct.where(has_output, 0)

            utilization_pct = (available_pct * ft_share).mean()

            total_units = output_pivot["TOTAL"].sum()
            pass_units = output_pivot["PASS"].sum()

            target_uph = (
                TARGET_OEE
                * MAX_TEST_SITE_QTY
                * 3600
                / (IDEAL_TEST_TIME + IDEAL_INDEX_TIME)
            )

            target_units = target_uph * len(day_hours)

            output_attainment_pct = (
                total_units / target_units * 100
                if target_units > 0
                else 0
            )
            output_attainment_pct = min(output_attainment_pct, 100)

            yield_pct = (
                pass_units / total_units * 100
                if total_units > 0
                else 0
            )

            oee_pct = (
                utilization_pct / 100
                * output_attainment_pct / 100
                * yield_pct / 100
                * 100
            )

            rows.append({
                "report_day": report_day,
                "OEE": oee_pct,
                "Utilization": utilization_pct,
                "Output Attainment": output_attainment_pct,
                "Yield": yield_pct,
            })

            event_pivot_sec_scaled["report_day"] = report_day
            event_pivot_days.append(event_pivot_sec_scaled)

        metrics_daily = pd.DataFrame(rows).set_index("report_day")

        event_pivot_sec_scaled_daily = (
            pd.concat(event_pivot_days)
            .groupby("report_day")
            .sum()
            .reindex(all_days, fill_value=0)
        )

        return metrics_daily, event_pivot_sec_scaled_daily

    def make_metric_fig(metrics_daily, title):
        fig = go.Figure()

        metric_colors = {
            "Output Attainment": "#B7DDF5",  # darker light blue
            "Utilization": "#F7D85C",        # darker light yellow
            "Yield": "#7FCC8A",              # darker PASS green
        }

        for metric_name in ["Output Attainment", "Utilization", "Yield"]:
            fig.add_trace(
                go.Bar(
                    x=metrics_daily.index,
                    y=metrics_daily[metric_name],
                    name=metric_name,
                    marker=dict(
                        color=metric_colors.get(metric_name),
                        line=dict(color="#9E9E9E", width=1.2)
                    ),
                    opacity=0.95,
                    text=None,
                    hovertemplate=(
                        "<b>📅 Date:</b> %{x|%m/%d}<br>"
                        f"<b>📊 {metric_name}:</b> %{{y:.1f}}%<extra></extra>"
                    ),
                )
            )

        fig.add_trace(
            go.Scatter(
                x=metrics_daily.index,
                y=metrics_daily["OEE"],
                mode="lines+markers+text",
                name="OEE",
                line=dict(color="black", width=2.5),
                marker=dict(color="black", size=7),
                text=metrics_daily["OEE"].round(1).astype(str) + "%",
                textposition="top center",
                textfont=dict(size=11, color="black"),
                hovertemplate=(
                    "<b>📅 Date:</b> %{x|%m/%d}<br>"
                    "<b>🎯 OEE:</b> %{y:.1f}%<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            title=dict(
                text=f"<b>{title}</b>",
                x=0.01,
                xanchor="left"
            ),
            height=455,
            margin=dict(l=70, r=30, t=95, b=60),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=1.08,
                xanchor="left",
                x=0,
                title_text="",
            ),
            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(family="Arial", color="#222222"),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial",
                font_color="#222222",
                bordercolor="#BDBDBD",
            ),
        )

        fig.update_yaxes(
            title_text="%",
            range=[0, 110],
            gridcolor="#E5E5E5"
        )

        fig.update_xaxes(
            tickmode="array",
            tickvals=all_days,
            ticktext=[pd.Timestamp(d).strftime("%m/%d") for d in all_days],
            gridcolor="#E5E5E5",
        )

        return fig

    def make_top_losses_table(event_pivot_sec_scaled, h_events, title):
        total_available_sec = len(all_days) * 24 * 3600

        total_loss = (
            event_pivot_sec_scaled
            .sum()
            .reset_index()
        )
        total_loss.columns = ["event_category", "lost_sec"]

        total_loss = total_loss[total_loss["lost_sec"] > 0].copy()

        if total_loss.empty:
            total_loss = pd.DataFrame({
                "event_category": ["NO_LOSS_RECORDED"],
                "lost_sec": [0],
            })

        latest_day = all_days[-1]
        prev_days = all_days[:-1]

        latest_loss_pct = (
            event_pivot_sec_scaled.loc[latest_day] / (24 * 3600) * 100
            if latest_day in event_pivot_sec_scaled.index
            else pd.Series(dtype=float)
        )

        prev_avg_loss_pct = (
            event_pivot_sec_scaled.loc[prev_days].mean() / (24 * 3600) * 100
            if len(prev_days) > 0
            else pd.Series(dtype=float)
        )

        total_loss["loss_pct"] = total_loss["lost_sec"] / total_available_sec * 100

        total_loss["latest_loss_pct"] = total_loss["event_category"].map(latest_loss_pct).fillna(0)
        total_loss["prev_avg_loss_pct"] = total_loss["event_category"].map(prev_avg_loss_pct).fillna(0)
        total_loss["trend_pct"] = total_loss["latest_loss_pct"] - total_loss["prev_avg_loss_pct"]

        event_count = (
            h_events
            .groupby("event_category")
            .agg(event_occurrences=("ID_EventLog", "count"))
            .reset_index()
        )

        total_loss = total_loss.merge(
            event_count,
            on="event_category",
            how="left"
        )

        total_loss["event_occurrences"] = total_loss["event_occurrences"].fillna(0).astype(int)

        total_loss = (
            total_loss
            .sort_values("lost_sec", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )

        total_loss["rank"] = total_loss.index + 1

        max_lost_sec = total_loss["lost_sec"].max()

        # dark red lost-time bar
        total_loss["lost_time_bar"] = total_loss.apply(
            lambda r: make_html_bar_label(
                r["lost_sec"],
                max_lost_sec,
                format_duration_hms(r["lost_sec"]),
                width=18,
                color="#D95F5F"
            ),
            axis=1
        )

        def loss_pct_ryg_label(x):
            if x >= 15:
                return f"🔴 {x:.2f}%"
            elif x >= 5:
                return f"🟡 {x:.2f}%"
            else:
                return f"🟢 {x:.2f}%"


        def trend_label(x):
            if x > 0:
                return f"🔴 {x:+.2f}%"
            elif x < 0:
                return f"🟢 {x:+.2f}%"
            else:
                return f"⚪ {x:+.2f}%"

        total_loss["loss_pct_label"] = total_loss["loss_pct"].map(loss_pct_ryg_label)
        total_loss["trend_pct_label"] = total_loss["trend_pct"].map(trend_label)

        fig = go.Figure(
            data=[
                go.Table(
                    columnwidth=[45, 230, 280, 120, 115, 105],
                    header=dict(
                        values=[
                            "<b>Rank</b>",
                            "<b>Handler Event</b>",
                            "<b>Lost Time</b>",
                            "<b>Event Occurrences</b>",
                            "<b>7-Day Loss %</b>",
                            "<b>Trend % (Today vs Prev 6D)</b>",
                        ],
                        fill_color="#FFFFFF",
                        align="left",
                        font=dict(color="black", size=11),
                        line_color="#BDBDBD",
                    ),
                    cells=dict(
                        values=[
                            total_loss["rank"],
                            total_loss["event_category"],
                            total_loss["lost_time_bar"],
                            total_loss["event_occurrences"],
                            total_loss["loss_pct_label"],
                            total_loss["trend_pct_label"],
                        ],
                        fill_color="#FFFFFF",
                        align="left",
                        font=dict(
                            color=[
                                "black",
                                "black",
                                "#D95F5F",
                                "black",
                                "black",
                                "black",
                            ],
                            size=11
                        ),
                        height=28,
                        line_color="#D0D0D0",
                    ),
                )
            ]
        )

        fig.update_layout(
            title=dict(text=f"<b>{title}</b>", x=0.01, xanchor="left"),
            height=400,
            margin=dict(l=20, r=20, t=65, b=20),
            paper_bgcolor=PLOT_BG,
            font=dict(family="Arial", color="#222222"),
        )

        return fig

    def html_header(title, subtitle):
        return f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background: #FAFAFA;
                    color: #222222;
                }}
                .report-header {{
                    background: #F2F2F2;
                    border-left: 8px solid #444444;
                    padding: 18px 22px;
                    margin-bottom: 18px;
                }}
                .report-title {{
                    font-size: 26px;
                    font-weight: 700;
                    margin-bottom: 6px;
                }}
                .report-subtitle {{
                    font-size: 14px;
                    color: #555555;
                }}
                h2 {{
                    margin-top: 28px;
                    padding-top: 14px;
                    border-top: 2px solid #DDDDDD;
                    font-size: 20px;
                }}
                .chart-block {{
                    background: #FFFFFF;
                    padding: 10px;
                    margin-bottom: 16px;
                    border: 1px solid #E0E0E0;
                }}
            </style>
        </head>
        <body>
            <div class="report-header">
                <div class="report-title">{title}</div>
                <div class="report-subtitle">{subtitle}</div>
            </div>
        """

    page_group_title = (
        prod_df["device_page_group"].dropna().mode().iloc[0]
        if not prod_df["device_page_group"].dropna().empty
        else "UNKNOWN"
    )

    html_parts = []

    html_parts.append(
        html_header(
            title="📈 Rolling 7-Day OEE Report",
            subtitle=(
                f"📅 {rolling_start_date.strftime('%m/%d/%Y')} – "
                f"{rolling_end_date.strftime('%m/%d/%Y')} | "
                f"📈 Daily OEE trend, Output Attainment, Utilization, Yield, and Top Downtime Losses"
            )
        )
    )

    handlers = sorted(prod_df["handler_clean"].dropna().unique())

    for handler_clean in handlers:
        p_prod = prod_df[
            prod_df["handler_clean"].astype(str) == str(handler_clean)
        ].copy()

        h_events = handler_df[
            handler_df["handler_clean"].astype(str) == str(handler_clean)
        ].copy()

        if p_prod.empty or h_events.empty:
            continue

        metrics_daily, event_pivot_sec_scaled = build_daily_metrics(p_prod, h_events)

        fig_metric = make_metric_fig(
            metrics_daily,
            title=f"Handler {handler_clean} - Rolling 7-Day OEE Metrics",
        )

        fig_losses = make_top_losses_table(
            event_pivot_sec_scaled,
            h_events,
            title=f"Handler {handler_clean} - Top Losses",
        )
        html_parts.append(f"<h2>Handler {handler_clean}</h2>")
        html_parts.append("<div class='chart-block'>")
        html_parts.append(to_html(fig_metric, include_plotlyjs="cdn", full_html=False))
        html_parts.append(to_html(fig_losses, include_plotlyjs=False, full_html=False))
        html_parts.append("</div>")

    html_parts.append("</body></html>")

    rolling_path = out_dir / "oee_rolling_7day_report.html"
    rolling_path.write_text("".join(html_parts), encoding="utf-8")

    print(f"Saved rolling 7-day OEE report: {rolling_path}")

# =====================================================
# EXPORTS
# =====================================================

def export_csvs(
    out_dir,
    handler_df,
    prod_df,
    handler_matched,
    prod_matched,
    lot_summary,
    handler_category_summary,
    site_summary,
    prod_hourly_summary,
    handler_hourly_summary,
):
    lot_summary.to_csv(
        out_dir / "micro_oee_lot_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )

    handler_category_summary.to_csv(
        out_dir / "micro_oee_handler_category_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )

    site_summary.to_csv(
        out_dir / "micro_oee_site_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )

    prod_hourly_summary.to_csv(
        out_dir / "micro_oee_production_hourly_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )

    handler_hourly_summary.to_csv(
        out_dir / "micro_oee_handler_hourly_summary.csv",
        index=False,
        encoding="utf-8-sig"
    )

    handler_df.to_csv(
        out_dir / "micro_oee_handler_events_all.csv",
        index=False,
        encoding="utf-8-sig"
    )

    prod_df.to_csv(
        out_dir / "micro_oee_production_units_all.csv",
        index=False,
        encoding="utf-8-sig"
    )

    handler_matched.to_csv(
        out_dir / "micro_oee_handler_events_matched.csv",
        index=False,
        encoding="utf-8-sig"
    )

    prod_matched.to_csv(
        out_dir / "micro_oee_production_units_matched.csv",
        index=False,
        encoding="utf-8-sig"
    )


# =====================================================
# MAIN
# =====================================================

def main():
    # Kill any previously opened Streamlit process before running again
    os.system("taskkill /F /IM streamlit.exe >nul 2>&1")
    os.system("taskkill /F /IM python.exe /FI \"WINDOWTITLE eq streamlit*\" >nul 2>&1")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Handler CSV Folder:", HANDLER_CSV_FOLDER)
    print("TXT Folder        :", TXT_FOLDER)
    print("Output Dir        :", OUT_DIR)

    # -----------------------------
    # Load input files
    # -----------------------------

    print(f"Report Date        : {REPORT_DATE.date()}")
    print(f"Rolling 7D Start   : {ROLLING_START_DATE.date()}")
    print(f"Rolling 7D End     : {ROLLING_END_DATE.date()}")

    print(f"Report Date  : {REPORT_DATE.date()}")
    print(f"TXT Folder   : {TXT_FOLDER}")

    if USE_FTP_DOWNLOAD:
        for d in pd.date_range(ROLLING_START_DATE, ROLLING_END_DATE, freq="D"):
            download_handler_csv_from_ftp(
                target_date=d,
                local_csv_root=HANDLER_CSV_FOLDER,
            )

        download_txt_files_from_ftp(
            start_date=ROLLING_START_DATE,
            end_date=ROLLING_END_DATE,
            local_txt_folder=TXT_FOLDER,
        )
    else:
        print("\nFTP download disabled.")
        print("Using local handler CSV folder:", HANDLER_CSV_FOLDER)
        print("Using local TXT folder        :", TXT_FOLDER)

    handler_df = load_handler_csv_folder(
        HANDLER_CSV_FOLDER,
        start_date=ROLLING_START_DATE,
        end_date=ROLLING_END_DATE,
    )

    print("\nHandler rows:", len(handler_df))
    print("Handler lots:", handler_df["LotInfo"].nunique())
    print("Handler event_time null count:", int(handler_df["event_time"].isna().sum()))
    print("\nHandler preview:")
    print(handler_df.head().to_string())

    prod_raw = load_all_txt_files(TXT_FOLDER)
    prod_df = standardize_prod_data(prod_raw)

    prod_df = prod_df.drop_duplicates(
        subset=[
            "source_file",
            "schedule_no",
            "serial_no",
            "flow",
            "site_no",
            "test_datetime",
            "test_time_sec",
            "pf_status",
        ]
    ).reset_index(drop=True)

    # Keep full 7-day dataset for rolling report before 24H filtering
    rolling_lots = sorted(
        set(handler_df["LotInfo"].dropna().astype(str).str.strip())
        .intersection(
            set(prod_df["schedule_no"].dropna().astype(str).str.strip())
        )
    )

    prod_matched_rolling = prod_df[
        prod_df["schedule_no"].isin(rolling_lots)
    ].copy()

    handler_matched_rolling = handler_df[
        handler_df["LotInfo"].isin(rolling_lots)
    ].copy()

    print("\nRolling 7D matched lots:", len(rolling_lots))
    print("Rolling 7D prod rows   :", len(prod_matched_rolling))
    print("Rolling 7D handler rows:", len(handler_matched_rolling))

    prod_df_rolling = prod_df.copy()
    handler_df_rolling = handler_df.copy()

    print("\nProduction rows after de-duplication:", len(prod_df))

    # -----------------------------
    # Auto-detect report date from handler CSV filename first
    # -----------------------------

    TARGET_DATE_AUTO = REPORT_DATE

    DAY_START_AUTO = TARGET_DATE_AUTO
    DAY_END_AUTO = TARGET_DATE_AUTO + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    print(f"Report date: {TARGET_DATE_AUTO.date()}")
    print(f"Analysis window: {DAY_START_AUTO} to {DAY_END_AUTO}")

    # -----------------------------
    # Keep lots that overlap report day
    # -----------------------------

    # Lot is included if its TXT lot window overlaps the report day.
    lot_overlap = (
        (prod_df["lot_start_time"] <= DAY_END_AUTO) &
        (prod_df["lot_end_time"] >= DAY_START_AUTO)
    )

    unit_inside_day = (
        (prod_df["test_datetime"] >= DAY_START_AUTO) &
        (prod_df["test_datetime"] <= DAY_END_AUTO)
    )

    report_lots = (
        prod_df.loc[lot_overlap | unit_inside_day, "schedule_no"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
    )

    prod_df = prod_df[prod_df["schedule_no"].isin(report_lots)].copy()
    handler_df = handler_df[handler_df["LotInfo"].isin(report_lots)].copy()

    prod_df["inside_report_day"] = (
        (prod_df["test_datetime"] >= DAY_START_AUTO) &
        (prod_df["test_datetime"] <= DAY_END_AUTO)
    )

    handler_df["inside_report_day"] = (
        (handler_df["event_time"] >= DAY_START_AUTO) &
        (handler_df["event_time"] <= DAY_END_AUTO)
    )

    print(f"\nReport window: {DAY_START_AUTO} to {DAY_END_AUTO}")
    print("Overlapping report lots:", len(report_lots))
    print("Production rows from overlapping lots:", len(prod_df))
    print("Handler rows from overlapping lots:", len(handler_df))
    print("Production rows inside report day:", int(prod_df["inside_report_day"].sum()))
    print("Handler rows inside report day:", int(handler_df["inside_report_day"].sum()))

    # -----------------------------
    # Match and summarize
    # -----------------------------
    matched_lots, handler_matched, prod_matched = match_lots(handler_df, prod_df)

    prod_matched_24h = prod_matched[
        prod_matched["inside_report_day"]
    ].copy()

    handler_matched_24h = handler_matched[
        handler_matched["inside_report_day"]
    ].copy()

    # =====================================================
    # NORMAL FLOW CONTINUES
    # =====================================================

    lot_summary = build_lot_summary(handler_matched_24h, prod_matched_24h)

    handler_category_summary = build_handler_category_summary(
        handler_matched_24h
    )

    prod_matched_24h, site_summary = build_site_summary(
        prod_matched_24h
    )

    prod_hourly_summary, handler_hourly_summary = build_hourly_summaries(
        prod_matched_24h,
        handler_matched_24h
    )

    # -----------------------------
    # Export CSVs
    # -----------------------------
    export_csvs(
        out_dir=OUT_DIR,
        handler_df=handler_df,
        prod_df=prod_df,
        handler_matched=handler_matched,
        prod_matched=prod_matched,
        lot_summary=lot_summary,
        handler_category_summary=handler_category_summary,
        site_summary=site_summary,
        prod_hourly_summary=prod_hourly_summary,
        handler_hourly_summary=handler_hourly_summary,
    )

    # -----------------------------
    # Build HTML reports
    # -----------------------------
    build_oee_visual_reports(
        prod_matched=prod_matched_24h,
        handler_matched=handler_matched_24h,
        out_dir=OUT_DIR,
        report_day_start=DAY_START_AUTO
    )

    build_rolling_7day_report(
        prod_df=prod_matched_rolling,
        handler_df=handler_matched_rolling,
        out_dir=OUT_DIR,
        rolling_start_date=ROLLING_START_DATE,
        rolling_end_date=ROLLING_END_DATE,
    )

    # -----------------------------
    # Final status
    # -----------------------------
    print("\nDONE")
    print("Exports saved to:")
    print(OUT_DIR)

    print("\nHTML reports:")
    for html_file in sorted(OUT_DIR.glob("*.html")):
        print(" -", html_file.name)

    print("\nCSV reports:")
    for csv_file in sorted(OUT_DIR.glob("*.csv")):
        print(" -", csv_file.name)


if __name__ == "__main__":
    main()


# In[ ]:





# In[ ]:




