"""
Check Item CSV Import — Daily Report Excel Generator.

核心职责：从 CSV raw data + DB 定义生成兼容 engine.py 的 Daily Report Excel。
"""

import csv
import datetime
import io
import json
import re

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter

import db
from base_manager import get_sn_mapping_from_db, get_sn_lookup_dicts


# Mapping of filename keywords to canonical item type names.
# Keys are matched case-insensitively against the filename.
_KEYWORD_TO_TYPE: dict[str, str] = {
    "BT-OTA": "BT-OTA",
    "Charging": "Charging",
    "FACT": "FACT",
    "ISB": "ISB",
    "Touch-Cal-Post": "Touch-CAL-Post",
    "COSMETIC": "Cosmetic",
}

# Column names we need to extract from the CSV header row.
_REQUIRED_COLUMNS = [
    "SerialNumber",
    "REL Event",
    "Test Pass/Fail Status",
    "EndTime",
    "List of Failing Tests",
    "Station ID",
    "Version",
]

# Metadata row prefixes that should be skipped (rows between header and data).
_METADATA_PREFIXES = (
    "Display Name",
    "PDCA Priority",
    "Upper Limit",
    "Lower Limit",
    "Measurement Unit",
)


def identify_csv_type(filename: str) -> str | None:
    """Identify the check item type from a CSV filename by keyword matching.

    Scans the filename for known keywords (case-insensitive) and returns
    the canonical item type name. Returns None if no keyword matches.

    Args:
        filename: The CSV filename (may include path components).

    Returns:
        The canonical item type string, or None if unrecognized.
    """
    filename_lower = filename.lower()
    for keyword, item_type in _KEYWORD_TO_TYPE.items():
        if keyword.lower() in filename_lower:
            return item_type
    return None


def sort_and_filter_tfinal(records: list[dict]) -> list[dict]:
    """Sort records by end_time ascending and discard records after REL_TFINAL per SN.

    For each unique serial_number, finds the first record with rel_event == "REL_TFINAL".
    All records for that SN with end_time strictly after the REL_TFINAL event's end_time
    are discarded. SNs without a REL_TFINAL event keep all their records.

    Args:
        records: List of parsed record dicts (must have 'end_time', 'serial_number',
                 'rel_event' keys).

    Returns:
        A new list sorted by end_time ascending, with post-TFINAL records removed.
    """
    # Sort all records by end_time ascending
    sorted_records = sorted(records, key=lambda r: r.get("end_time", ""))

    # For each SN, find the end_time of the first REL_TFINAL event
    tfinal_times: dict[str, str] = {}
    for rec in sorted_records:
        sn = rec.get("serial_number", "")
        if sn not in tfinal_times and rec.get("rel_event") == "REL_TFINAL":
            tfinal_times[sn] = rec.get("end_time", "")

    # Filter: keep records where SN has no TFINAL, or end_time <= TFINAL end_time
    result = []
    for rec in sorted_records:
        sn = rec.get("serial_number", "")
        if sn not in tfinal_times:
            # No TFINAL for this SN — keep all records
            result.append(rec)
        else:
            # Keep records with end_time <= TFINAL end_time
            if rec.get("end_time", "") <= tfinal_times[sn]:
                result.append(rec)

    return result


# Events that are anomalies — they should be attributed to the preceding valid CP.
_ANOMALY_EVENTS = frozenset([
    "REL FA RETEST",
    "SEND TO FA",
    "STOP TEST",
    "RETURN TO REL",
])


def attribute_anomaly_cps(records: list[dict]) -> list[dict]:
    """Attribute anomaly events to the preceding valid CP per serial number.

    For each record, sets an `effective_cp` field:
    - If the record's rel_event is a normal CP (not an anomaly), effective_cp = rel_event.
    - If the record's rel_event is an anomaly event, effective_cp = the most recent
      preceding non-anomaly CP for that same serial number.
    - If an anomaly event has no preceding valid CP, effective_cp = rel_event itself.

    Records must already be sorted by end_time ascending.

    Args:
        records: List of parsed record dicts (sorted by end_time ascending).
                 Must have 'serial_number' and 'rel_event' keys.

    Returns:
        The same list with `effective_cp` field added/set on each record.
    """
    # Track the last valid (non-anomaly) CP per serial number
    last_valid_cp: dict[str, str] = {}

    for rec in records:
        sn = rec.get("serial_number", "")
        rel_event = rec.get("rel_event", "")

        if rel_event in _ANOMALY_EVENTS:
            # Attribute to the preceding valid CP for this SN
            if sn in last_valid_cp:
                rec["effective_cp"] = last_valid_cp[sn]
            else:
                # Edge case: no preceding valid CP — use rel_event itself
                rec["effective_cp"] = rel_event
        else:
            # Normal CP — effective_cp is itself, and update tracker
            rec["effective_cp"] = rel_event
            last_valid_cp[sn] = rel_event

    return records


def deduplicate_records(records: list[dict]) -> list[dict]:
    """Deduplicate records by keeping only the latest record per (SN, effective_cp, item) group.

    For each unique combination of (serial_number, effective_cp, item), keeps only
    the record with the latest (maximum) end_time. Since records are expected to be
    sorted by end_time ascending, the last record encountered in each group wins.

    Args:
        records: List of parsed record dicts (already sorted by end_time ascending,
                 with effective_cp set). Must have 'serial_number', 'effective_cp',
                 'item', and 'end_time' keys.

    Returns:
        A new list containing only the latest record per group.
    """
    # Use a dict keyed by (serial_number, effective_cp, item) to track the latest record
    latest: dict[tuple[str, str, str], dict] = {}

    for rec in records:
        key = (
            rec.get("serial_number", ""),
            rec.get("effective_cp", ""),
            rec.get("item", ""),
        )
        # Since records are sorted by end_time ascending, later records overwrite earlier ones.
        # But we also explicitly compare end_time to handle any ordering edge cases.
        existing = latest.get(key)
        if existing is None or rec.get("end_time", "") >= existing.get("end_time", ""):
            latest[key] = rec

    return list(latest.values())


def filter_valid_sns(records: list[dict], valid_sns: set) -> list[dict]:
    """Filter parsed records to keep only those with serial numbers in the valid set.

    Records whose serial_number is not in valid_sns are silently discarded.

    Args:
        records: List of parsed record dicts (from parse_csv_file).
        valid_sns: Set of valid serial number strings (from DB SN mapping).

    Returns:
        A new list containing only records with serial_number in valid_sns.
    """
    return [r for r in records if r.get("serial_number") in valid_sns]


def parse_csv_file(file_content: str | bytes, item_type: str) -> list[dict]:
    """Parse a check item CSV file and extract test records.

    Finds the header row by scanning for a row containing 'SerialNumber',
    then extracts data records with key fields. For FAIL records, also
    extracts parameter columns (index 13+) as a dict.

    Args:
        file_content: The CSV file content as string or bytes.
        item_type: The canonical item type (e.g., 'FACT', 'ISB').

    Returns:
        A list of dicts, each containing:
            - serial_number: str
            - rel_event: str
            - status: str ('PASS' or 'FAIL')
            - end_time: str (timestamp)
            - failing_tests: str (may be empty)
            - station_id: str
            - version: str
            - item: str (the item_type passed in)
            - test_params: dict | None (parameter name→value for FAIL records)

    Returns an empty list if no header row with 'SerialNumber' is found.
    """
    # Normalize input to string
    if isinstance(file_content, bytes):
        file_content = file_content.decode("utf-8", errors="ignore")

    reader = csv.reader(io.StringIO(file_content))

    # Step 1: Find the header row (the row containing 'SerialNumber')
    header_row = None
    header_row_idx = -1
    for idx, row in enumerate(reader):
        if "SerialNumber" in row:
            header_row = row
            header_row_idx = idx
            break

    if header_row is None:
        return []

    # Step 2: Build column index mapping for required fields
    col_indices: dict[str, int] = {}
    for col_name in _REQUIRED_COLUMNS:
        try:
            col_indices[col_name] = header_row.index(col_name)
        except ValueError:
            # Column not found — will be treated as empty string
            col_indices[col_name] = -1

    # Parameter columns start at index 13 (the 14th column, 1-indexed)
    param_start_idx = 13
    param_names = header_row[param_start_idx:] if len(header_row) > param_start_idx else []

    # Step 3: Read data rows, skipping metadata rows
    records: list[dict] = []
    for row in reader:
        # Skip empty rows
        if not row or all(cell.strip() == "" for cell in row):
            continue

        # Skip metadata rows (Display Name, PDCA Priority, etc.)
        first_cell = row[0].strip() if row else ""
        if any(first_cell.startswith(prefix) for prefix in _METADATA_PREFIXES):
            continue

        # Extract required fields
        def _get(col_name: str) -> str:
            idx = col_indices[col_name]
            if idx < 0 or idx >= len(row):
                return ""
            return row[idx].strip()

        serial_number = _get("SerialNumber")
        # Skip rows without a serial number (likely empty/malformed)
        if not serial_number:
            continue

        status = _get("Test Pass/Fail Status")
        rel_event = _get("REL Event")
        end_time = _get("EndTime")
        failing_tests = _get("List of Failing Tests")
        station_id = _get("Station ID")
        version = _get("Version")

        # For FAIL records, extract parameter columns as dict
        test_params: dict | None = None
        if status == "FAIL" and param_names:
            params = {}
            for i, param_name in enumerate(param_names):
                col_idx = param_start_idx + i
                if col_idx >= len(row):
                    break
                value = row[col_idx].strip()
                if value and param_name.strip():
                    # Try to convert to float for numeric values
                    try:
                        params[param_name.strip()] = float(value)
                    except ValueError:
                        # Keep as string if not numeric
                        params[param_name.strip()] = value
            if params:
                test_params = params

        records.append({
            "serial_number": serial_number,
            "rel_event": rel_event,
            "status": status,
            "end_time": end_time,
            "failing_tests": failing_tests,
            "station_id": station_id,
            "version": version,
            "item": item_type,
            "test_params": test_params,
        })

    return records

# Strife failure detection patterns.
# Each tuple: (compiled regex pattern, threshold value).
# If the CP name matches the pattern and the captured numeric value exceeds the threshold,
# the failure is classified as "strife_fail"; otherwise "spec_fail".
_STRIFE_PATTERNS: list[tuple[re.Pattern, int]] = [
    (re.compile(r"RANDOM DROP 1M PB_(\d+)", re.IGNORECASE), 200),
    (re.compile(r"RANDOM DROP 1M GRA_(\d+)", re.IGNORECASE), 20),
    (re.compile(r"15MM PROBE SP_(\d+)KG", re.IGNORECASE), 21),
    (re.compile(r"CLEANING_SPRAY_OP1_AFTER (\d+)HRS", re.IGNORECASE), 72),
    (re.compile(r"RBI_(\d+)CM", re.IGNORECASE), 10),
    (re.compile(r"BC_.*_(\d+)%", re.IGNORECASE), 100),
]


def _is_strife_failure(cp_name: str) -> bool:
    """Determine if a CP name indicates a strife failure based on numeric thresholds.

    Checks the CP name against known patterns. If a pattern matches and the
    captured numeric value exceeds the associated threshold, the failure is strife.

    Args:
        cp_name: The checkpoint name to evaluate.

    Returns:
        True if the CP name indicates a strife failure, False otherwise.
    """
    cp_upper = cp_name.strip().upper()
    for pattern, threshold in _STRIFE_PATTERNS:
        m = pattern.search(cp_upper)
        if m:
            value = int(m.group(1))
            if value > threshold:
                return True
    return False


def detect_strife_failures(records: list[dict], cp_schedule: dict) -> list[dict]:
    """Classify FAIL records as strife or spec failures based on CP name thresholds.

    For each record:
    - If status is not "FAIL", sets failure_type to None.
    - If status is "FAIL", checks the effective_cp against known strife patterns.
      If the CP name matches a strife pattern (numeric value exceeds threshold),
      sets failure_type to "strife_fail"; otherwise "spec_fail".

    The cp_schedule parameter provides the CP schedule from DB (wf_id → [cp_names]).
    It is available for future use (e.g., resolving CP names from schedule context)
    but the current implementation determines strife status directly from the
    effective_cp field on each record.

    Args:
        records: List of deduplicated record dicts (with effective_cp set).
                 Must have 'status' and 'effective_cp' keys.
        cp_schedule: Dict mapping wf_id to ordered list of CP names from DB.

    Returns:
        The same list with `failure_type` field added to each record:
        - "strife_fail" for strife failures
        - "spec_fail" for spec failures
        - None for PASS records
    """
    for rec in records:
        status = rec.get("status", "")
        if status != "FAIL":
            rec["failure_type"] = None
        else:
            effective_cp = rec.get("effective_cp", "")
            if _is_strife_failure(effective_cp):
                rec["failure_type"] = "strife_fail"
            else:
                rec["failure_type"] = "spec_fail"

    return records


# ---------------------------------------------------------------------------
# Excel Generation — WF Sheet Layout (openpyxl)
# ---------------------------------------------------------------------------

# Fixed check item order for all WF sheets.
CHECK_ITEMS = ["Cosmetic", "ISB", "FACT", "BT-OTA", "Touch-CAL-Post", "Charging"]

# --- Color coding constants ---
PASS_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
PASS_FONT = Font(color="006100")
SPEC_FAIL_FILL = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
STRIFE_FAIL_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
STRIFE_FAIL_FONT = Font(color="000000")

# Number of check item columns per CP group.
_ITEMS_PER_CP = len(CHECK_ITEMS)  # 6


def _is_chemical_wf(wf_num) -> bool:
    """Return True if the WF number indicates a Chemical workflow (29.x or 30).

    Chemical WFs get an extra "Chemical" column before the first CP group.

    Args:
        wf_num: WF number as int, float, or string (e.g., 29, 29.1, 30, "29.1").

    Returns:
        True if the WF is a Chemical workflow.
    """
    try:
        num = float(wf_num)
    except (TypeError, ValueError):
        return False
    # WF 29.x (29 <= num < 30) or exactly 30
    return (29 <= num < 30) or num == 30


def create_wf_sheet(wb: Workbook, wf_num, wf_name: str, cp_list: list[str],
                    sn_data: list[dict], is_chemical: bool | None = None,
                    records_by_sn: dict | None = None):
    """Create a WF sheet in the workbook with proper header layout.

    Creates a sheet named `Sys WF{wf_num}_{wf_name}` and writes:
    - Row 1: Header row with fixed columns (%, Completion%, Config, Unit#, S/N)
             followed by merged CP group headers (each spanning 6 columns).
    - Row 2: Sub-header row with check item names under each CP group.
    - Row 3+: Data rows with SN info and test results (if records_by_sn provided).

    For Chemical WFs (29.x, 30), an extra "Chemical" column is inserted
    between S/N and the first CP group.

    Args:
        wb: The openpyxl Workbook to add the sheet to.
        wf_num: WF number (int, float, or string). Used in sheet name and
                chemical detection.
        wf_name: Human-readable WF name (e.g., "ISB + FACT + BT-OTA").
        cp_list: Ordered list of checkpoint names for this WF.
        sn_data: List of dicts with SN info: [{serial_number, config, unit_number}, ...].
                 Used to write data rows (Config, Unit#, S/N columns).
        is_chemical: Override chemical detection. If None, auto-detects from wf_num.
        records_by_sn: Optional dict mapping serial_number to
                       {(effective_cp, item): record_dict}. When provided,
                       populate_wf_data is called to fill in results with color coding.

    Returns:
        The created worksheet.
    """
    # Determine chemical status
    if is_chemical is None:
        is_chemical = _is_chemical_wf(wf_num)

    # Format WF number for sheet name: integer if whole number, else decimal
    try:
        num_val = float(wf_num)
        if num_val == int(num_val):
            wf_num_str = str(int(num_val))
        else:
            wf_num_str = str(num_val)
    except (TypeError, ValueError):
        wf_num_str = str(wf_num)

    sheet_name = f"Sys WF{wf_num_str}_{wf_name}"
    # Excel sheet names are limited to 31 characters
    if len(sheet_name) > 31:
        sheet_name = sheet_name[:31]

    ws = wb.create_sheet(title=sheet_name)

    # --- Fixed header columns ---
    fixed_headers = ["%", "Completion%", "Config", "Unit#", "S/N"]
    header_row_idx = 1  # Row 1 (1-indexed in openpyxl)
    sub_header_row_idx = 2  # Row 2

    # Write fixed headers in row 1
    for col_idx, header in enumerate(fixed_headers, start=1):
        ws.cell(row=header_row_idx, column=col_idx, value=header)

    # Also write fixed headers in row 2 (sub-header row keeps them for alignment)
    for col_idx, header in enumerate(fixed_headers, start=1):
        ws.cell(row=sub_header_row_idx, column=col_idx, value=header)

    # --- Chemical column (if applicable) ---
    cp_start_col = len(fixed_headers) + 1  # Column after S/N (6)

    if is_chemical:
        # Add "Chemical" header in row 1 at the column after S/N
        ws.cell(row=header_row_idx, column=cp_start_col, value="Chemical")
        ws.cell(row=sub_header_row_idx, column=cp_start_col, value="")
        cp_start_col += 1  # CP groups start one column later

    # --- CP group headers (row 1) and check item sub-headers (row 2) ---
    current_col = cp_start_col
    for cp_name in cp_list:
        start_col = current_col
        end_col = current_col + _ITEMS_PER_CP - 1

        # Merge CP name across 6 columns in row 1
        if _ITEMS_PER_CP > 1:
            ws.merge_cells(
                start_row=header_row_idx, start_column=start_col,
                end_row=header_row_idx, end_column=end_col
            )
        ws.cell(row=header_row_idx, column=start_col, value=cp_name)

        # Write check item sub-headers in row 2
        for item_offset, item_name in enumerate(CHECK_ITEMS):
            ws.cell(row=sub_header_row_idx, column=current_col + item_offset, value=item_name)

        current_col = end_col + 1

    # --- Data rows (row 3+): write SN info columns ---
    for row_offset, sn_info in enumerate(sn_data):
        data_row = 3 + row_offset  # Starting from row 3
        ws.cell(row=data_row, column=3, value=sn_info.get("config", ""))
        ws.cell(row=data_row, column=4, value=sn_info.get("unit_number", ""))
        ws.cell(row=data_row, column=5, value=sn_info.get("serial_number", ""))

    # --- Populate results with color coding (if records provided) ---
    if records_by_sn is not None and sn_data:
        populate_wf_data(ws, sn_data, cp_list, records_by_sn, is_chemical)

    return ws


def populate_wf_data(ws, sn_data: list[dict], cp_list: list[str],
                     records_by_sn: dict, is_chemical: bool = False):
    """Populate data rows with SN results and apply color coding.

    For each SN in sn_data, writes status values ("PASS" or "FAIL") in the
    appropriate cells and applies color coding based on the record's failure_type:
    - PASS: green background (#C6EFCE), green font (#006100)
    - spec_fail: red background (#FF0000), white font (default)
    - strife_fail: yellow background (#FFFF00), black font (#000000)
    - Empty cells (no record) get no color.

    Args:
        ws: The openpyxl worksheet to populate.
        sn_data: List of dicts with SN info: [{serial_number, config, unit_number}, ...].
                 Determines row order (row 3+).
        cp_list: Ordered list of checkpoint names for this WF.
        records_by_sn: Dict mapping serial_number to a dict of
                       {(effective_cp, item): record_dict}. Each record_dict must
                       have 'status' and 'failure_type' keys.
        is_chemical: Whether this is a Chemical WF (shifts CP columns by 1).
    """
    # Determine the starting column for CP data
    # Fixed columns: %, Completion%, Config, Unit#, S/N = 5 columns
    fixed_col_count = 5
    cp_start_col = fixed_col_count + 1  # Column 6

    if is_chemical:
        cp_start_col += 1  # Chemical column shifts CPs to column 7

    # Populate data for each SN
    for row_offset, sn_info in enumerate(sn_data):
        data_row = 3 + row_offset  # Data starts at row 3
        sn = sn_info.get("serial_number", "")

        # Get this SN's records lookup
        sn_records = records_by_sn.get(sn, {})

        # Iterate through each CP and each check item
        current_col = cp_start_col
        for cp_name in cp_list:
            for item_offset, item_name in enumerate(CHECK_ITEMS):
                col = current_col + item_offset
                record = sn_records.get((cp_name, item_name))

                if record is not None:
                    status = record.get("status", "")
                    failure_type = record.get("failure_type")
                    cell = ws.cell(row=data_row, column=col, value=status)

                    # Apply color coding
                    if status == "PASS":
                        cell.fill = PASS_FILL
                        cell.font = PASS_FONT
                    elif failure_type == "strife_fail":
                        cell.fill = STRIFE_FAIL_FILL
                        cell.font = STRIFE_FAIL_FONT
                    elif failure_type == "spec_fail":
                        cell.fill = SPEC_FAIL_FILL
                    # else: no color for unknown status

            current_col += _ITEMS_PER_CP


# ---------------------------------------------------------------------------
# Raw Record Storage
# ---------------------------------------------------------------------------


def store_raw_records(records: list[dict], summary: dict):
    """Store all parsed CSV records into the database for historical querying.

    Creates an import_batches entry with statistics, then inserts each record
    into raw_check_item_records. For FAIL records, test_params is stored as
    a JSON string; for PASS records, test_params is NULL.

    Args:
        records: List of parsed record dicts (with effective_cp set).
                 Each must have: serial_number, rel_event, effective_cp, item,
                 status, end_time, failing_tests, station_id, version,
                 source_file, test_params.
        summary: Dict with statistics: {file_count, record_count, valid_sn_count}.

    Returns:
        The import_batch_id of the created batch.
    """
    conn = db.get_conn()
    try:
        today = datetime.date.today().isoformat()
        now = datetime.datetime.now().isoformat()

        # Create import_batches entry
        cur = conn.execute(
            """INSERT INTO import_batches
               (import_date, created_at, file_count, record_count, valid_sn_count, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                today,
                now,
                summary.get('file_count', 0),
                summary.get('record_count', 0),
                summary.get('valid_sn_count', 0),
                'completed',
            ),
        )
        batch_id = cur.lastrowid

        # Insert each record into raw_check_item_records
        rows = []
        for rec in records:
            status = rec.get('status', '')
            # FAIL records: store test_params as JSON; PASS records: NULL
            test_params_value = None
            if status == 'FAIL' and rec.get('test_params'):
                test_params_value = json.dumps(rec['test_params'])

            rows.append((
                batch_id,
                today,
                rec.get('serial_number', ''),
                rec.get('rel_event', ''),
                rec.get('effective_cp', ''),
                rec.get('item', ''),
                status,
                rec.get('end_time', ''),
                rec.get('failing_tests', ''),
                rec.get('station_id', ''),
                rec.get('version', ''),
                test_params_value,
                rec.get('source_file', ''),
            ))

        if rows:
            conn.executemany(
                """INSERT INTO raw_check_item_records
                   (import_batch_id, import_date, serial_number, rel_event,
                    effective_cp, item, status, end_time, failing_tests,
                    station_id, version, test_params, source_file)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )

        conn.commit()
        return batch_id
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Daily Report Orchestrator
# ---------------------------------------------------------------------------


def generate_daily_report(csv_files: list) -> tuple[bytes, str, dict]:
    """Orchestrate the full pipeline: read DB definitions → parse CSVs → aggregate → generate Excel.

    Processes uploaded CSV files against DB definitions to produce a Daily Report
    Excel workbook compatible with engine.py.

    Args:
        csv_files: List of file-like objects with `.filename` and `.read()` attributes
                   (e.g., Flask FileStorage objects).

    Returns:
        A tuple of (excel_bytes, filename, summary):
            - excel_bytes: The generated Excel workbook as bytes.
            - filename: The output filename (M60 EVT Rel Daily Report_YYYYMMDD.xlsx).
            - summary: Dict with statistics {file_count, record_count, valid_sn_count, warnings}.

    Raises:
        ValueError: If Base files haven't been uploaded (no SN mapping available).
    """
    # --- Step 1: Read DB definitions ---
    sn_result = get_sn_mapping_from_db()
    if sn_result is None:
        raise ValueError("请先上传 Base 文件 (SN mapping)")

    sn_mapping = sn_result['sn_mapping']
    valid_sns = set(sn_mapping.keys())

    sn_to_wf, sn_to_unit, sn_to_config = get_sn_lookup_dicts()

    # Read CP schedule and test plan/WF names from DB
    conn = db.get_conn()
    try:
        cp_defs = db.get_current_cp_definitions(conn)
        wf_names = db.get_current_wf_definitions(conn)
        test_plan = db.get_current_test_definitions(conn)
    finally:
        conn.close()

    # Build cp_schedule: {wf_id: [cp_name, ...]}
    cp_schedule = {}
    for wf_num, cp_list in cp_defs.items():
        cp_schedule[wf_num] = [cp['cp_name'] for cp in cp_list]

    # --- Step 2: Parse CSV files ---
    all_records: list[dict] = []
    warnings: list[str] = []
    file_count = 0

    for csv_file in csv_files:
        filename = csv_file.filename if hasattr(csv_file, 'filename') else str(csv_file)
        item_type = identify_csv_type(filename)

        if item_type is None:
            warnings.append(f"Unrecognized file type: {filename}")
            continue

        # Read file content
        content = csv_file.read()
        if hasattr(csv_file, 'seek'):
            csv_file.seek(0)  # Reset for potential re-read

        records = parse_csv_file(content, item_type)

        if not records:
            warnings.append(f"No SerialNumber column or no data found in: {filename}")
            continue

        # Filter valid SNs
        valid_records = filter_valid_sns(records, valid_sns)

        # Tag source file
        for rec in valid_records:
            rec['source_file'] = filename

        all_records.extend(valid_records)
        file_count += 1

    if not all_records:
        raise ValueError("所有 CSV 文件中未找到有效数据")

    valid_sn_count = len(set(r['serial_number'] for r in all_records))

    # --- Step 3: Aggregate ---
    # Sort and filter TFINAL
    sorted_records = sort_and_filter_tfinal(all_records)

    # Attribute anomaly CPs
    attributed_records = attribute_anomaly_cps(sorted_records)

    # Deduplicate (last record wins per SN/CP/Item)
    deduped_records = deduplicate_records(attributed_records)

    # Detect strife failures
    final_records = detect_strife_failures(deduped_records, cp_schedule)

    # --- Step 4: Generate Excel workbook ---
    wb = Workbook()
    # Remove the default sheet created by openpyxl
    if wb.active:
        wb.remove(wb.active)

    # Determine which WFs to generate sheets for (sorted numerically)
    wf_nums_sorted = sorted(cp_schedule.keys(), key=lambda x: float(x))

    for wf_num in wf_nums_sorted:
        cp_list = cp_schedule.get(wf_num, [])
        if not cp_list:
            continue

        # Get WF name
        wf_name = wf_names.get(wf_num, "")

        # Get SNs assigned to this WF
        sns_for_wf = [sn for sn, info in sn_mapping.items() if str(info['wf_id']) == str(wf_num)]

        if not sns_for_wf:
            continue

        # Sort SNs by config then unit_number (natural sort)
        def _natural_sort_key(sn):
            config = sn_to_config.get(sn, '')
            unit = sn_to_unit.get(sn, '')
            # Natural sort: split into text/number parts
            parts = [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', str(unit))]
            return (config, parts)

        sns_for_wf.sort(key=_natural_sort_key)

        # Build sn_data list
        sn_data = []
        for sn in sns_for_wf:
            sn_data.append({
                'serial_number': sn,
                'config': sn_to_config.get(sn, ''),
                'unit_number': sn_to_unit.get(sn, ''),
            })

        # Build records_by_sn lookup for this WF's SNs
        records_by_sn: dict[str, dict[tuple[str, str], dict]] = {}
        for rec in final_records:
            sn = rec.get('serial_number', '')
            if sn in set(sns_for_wf):
                if sn not in records_by_sn:
                    records_by_sn[sn] = {}
                key = (rec.get('effective_cp', ''), rec.get('item', ''))
                records_by_sn[sn][key] = rec

        # Create the WF sheet
        create_wf_sheet(wb, wf_num, wf_name, cp_list, sn_data, records_by_sn=records_by_sn)

    # --- Step 5: Save workbook to bytes ---
    output = io.BytesIO()
    wb.save(output)
    excel_bytes = output.getvalue()

    # --- Step 6: Determine filename from latest EndTime ---
    # Find the latest end_time across all records
    all_end_times = [r.get('end_time', '') for r in all_records if r.get('end_time')]
    if all_end_times:
        latest_end_time = max(all_end_times)
        # Parse date from end_time string (various formats possible)
        try:
            # Try ISO format first
            dt = datetime.datetime.fromisoformat(latest_end_time.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Try common datetime formats
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%m/%d/%Y %H:%M:%S',
                            '%Y-%m-%d %H:%M:%S.%f', '%m/%d/%Y %I:%M:%S %p'):
                    try:
                        dt = datetime.datetime.strptime(latest_end_time, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    dt = datetime.datetime.now()
            except Exception:
                dt = datetime.datetime.now()
        date_str = dt.strftime('%Y%m%d')
    else:
        date_str = datetime.date.today().strftime('%Y%m%d')

    filename = f"M60 EVT Rel Daily Report_{date_str}.xlsx"

    # --- Step 7: Build summary ---
    summary = {
        'file_count': file_count,
        'record_count': len(final_records),
        'valid_sn_count': valid_sn_count,
        'warnings': warnings,
    }

    # --- Step 8: Store raw records in DB ---
    store_raw_records(all_records, summary)

    return excel_bytes, filename, summary
