"""
Property-based tests for /api/raw-records query endpoint (Task 11.2).

**Validates: Requirements 9.1-9.4**

Property 12: Query completeness — For any set of stored records matching a filter,
the query API SHALL return all and only those records.
"""

import csv
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Set up a fresh test DB before importing modules that use db
TEST_DB = tempfile.mktemp(suffix='.db')
import db
db.DB_PATH = TEST_DB
db.init_db()

from hypothesis import given, settings, assume
from hypothesis import strategies as st

import api
import base_manager


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_alnum_chars = st.sampled_from(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
)

# Use a fixed pool of SNs so we can set up SN mapping for them
KNOWN_SNS = ["SN_ALPHA01", "SN_BETA002", "SN_GAMMA03", "SN_DELTA04", "SN_EPSIL05"]
KNOWN_UNITS = ["U-A-1", "U-B-2", "U-C-3", "U-D-4", "U-E-5"]
KNOWN_CONFIGS = ["R1FNF", "R2CNM", "R3", "R4"]

serial_number_strategy = st.sampled_from(KNOWN_SNS)

item_strategy = st.sampled_from([
    "BT-OTA", "Charging", "FACT", "ISB", "Touch-CAL-Post", "Cosmetic",
])

rel_event_strategy = st.sampled_from([
    "REL_T0", "CP_100%", "BC_CWCB_SHORT_140%", "TC_300CYCLES",
    "RANDOM_DROP_1M_PB", "REL_T500",
])

# Generate dates within a controlled range for meaningful date filtering
date_strategy = st.dates(
    min_value=__import__('datetime').date(2026, 4, 1),
    max_value=__import__('datetime').date(2026, 6, 30),
)

time_strategy = st.times(
    min_value=__import__('datetime').time(0, 0, 0),
    max_value=__import__('datetime').time(23, 59, 59),
)

version_strategy = st.from_regex(r"[0-9]\.[0-9]\.[0-9]", fullmatch=True)

station_id_strategy = st.text(alphabet=_alnum_chars, min_size=3, max_size=15)

status_strategy = st.sampled_from(["PASS", "FAIL"])


@st.composite
def raw_record(draw):
    """Generate a single raw check item record."""
    d = draw(date_strategy)
    t = draw(time_strategy)
    end_time = f"{d.isoformat()} {t.strftime('%H:%M:%S')}"

    status = draw(status_strategy)
    failing_tests = ""
    test_params = None
    if status == "FAIL":
        failing_tests = draw(st.text(alphabet=_alnum_chars, min_size=3, max_size=20))
        # Optionally add test params
        if draw(st.booleans()):
            num_params = draw(st.integers(min_value=1, max_value=3))
            keys = draw(st.lists(
                st.text(alphabet=_alnum_chars, min_size=3, max_size=10),
                min_size=num_params, max_size=num_params, unique=True
            ))
            vals = draw(st.lists(
                st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
                min_size=num_params, max_size=num_params
            ))
            test_params = dict(zip(keys, vals))

    return {
        "serial_number": draw(serial_number_strategy),
        "rel_event": draw(rel_event_strategy),
        "effective_cp": draw(rel_event_strategy),
        "item": draw(item_strategy),
        "status": status,
        "end_time": end_time,
        "failing_tests": failing_tests,
        "station_id": draw(station_id_strategy),
        "version": draw(version_strategy),
        "test_params": test_params,
        "source_file": "test_generated.csv",
    }


@st.composite
def records_with_filter(draw):
    """Generate a list of records and a valid filter combination to test against."""
    records = draw(st.lists(raw_record(), min_size=1, max_size=15))

    # Pick a SN that exists in the records for the query
    sns_in_records = list(set(r["serial_number"] for r in records))
    target_sn = draw(st.sampled_from(sns_in_records))

    # Optionally pick an item filter from items that exist for this SN
    sn_records = [r for r in records if r["serial_number"] == target_sn]
    items_for_sn = list(set(r["item"] for r in sn_records))

    use_item_filter = draw(st.booleans())
    item_filter = draw(st.sampled_from(items_for_sn)) if use_item_filter else None

    # Optionally pick date range filter
    use_date_from = draw(st.booleans())
    use_date_to = draw(st.booleans())
    date_from = draw(date_strategy) if use_date_from else None
    date_to = draw(date_strategy) if use_date_to else None

    # Ensure date_from <= date_to if both are set
    if date_from and date_to and date_from > date_to:
        date_from, date_to = date_to, date_from

    return {
        "records": records,
        "target_sn": target_sn,
        "item_filter": item_filter,
        "date_from": date_from,
        "date_to": date_to,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_tables():
    """Clear raw_check_item_records and import_batches tables."""
    conn = db.get_conn()
    conn.execute("DELETE FROM raw_check_item_records")
    conn.execute("DELETE FROM import_batches")
    conn.commit()
    conn.close()


def _insert_records(records):
    """Insert records into the database and return the batch_id."""
    conn = db.get_conn()
    cur = conn.execute(
        """INSERT INTO import_batches
           (import_date, created_at, file_count, record_count, valid_sn_count, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ('2026-05-15', '2026-05-15T10:00:00', 1, len(records), len(set(r["serial_number"] for r in records)), 'completed')
    )
    batch_id = cur.lastrowid

    for r in records:
        test_params_json = json.dumps(r["test_params"]) if r["test_params"] else None
        conn.execute(
            """INSERT INTO raw_check_item_records
               (import_batch_id, import_date, serial_number, rel_event, effective_cp,
                item, status, end_time, failing_tests, station_id, version, test_params, source_file)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (batch_id, '2026-05-15', r["serial_number"], r["rel_event"], r["effective_cp"],
             r["item"], r["status"], r["end_time"], r["failing_tests"],
             r["station_id"], r["version"], test_params_json, r["source_file"])
        )
    conn.commit()
    conn.close()
    return batch_id


def _setup_sn_mapping(app_client):
    """Upload a SN mapping that covers all KNOWN_SNS."""
    output = io.BytesIO()
    wrapper = io.TextIOWrapper(output, encoding='utf-8', newline='')
    writer = csv.DictWriter(wrapper, fieldnames=[
        'serial_number', 'config', 'Product', 'unit_number', 'start_date', 'wf_id'
    ])
    writer.writeheader()
    for i, (sn, unit) in enumerate(zip(KNOWN_SNS, KNOWN_UNITS)):
        writer.writerow({
            'serial_number': sn,
            'config': KNOWN_CONFIGS[i % len(KNOWN_CONFIGS)],
            'Product': 'B529',
            'unit_number': unit,
            'start_date': '20260416',
            'wf_id': str(i + 1),
        })
    wrapper.flush()
    wrapper.detach()
    output.seek(0)

    app_client.post('/api/base-files', data={
        'files': (output, 'Serial Numbers EVT FATP.csv'),
    }, content_type='multipart/form-data')


def _compute_expected_records(records, target_sn, item_filter, date_from, date_to):
    """Compute which records should be returned by the API given the filters."""
    expected = []
    for r in records:
        # Filter by SN
        if r["serial_number"] != target_sn:
            continue
        # Filter by item
        if item_filter and r["item"] != item_filter:
            continue
        # Filter by date_from (inclusive)
        if date_from:
            record_date = r["end_time"][:10]  # YYYY-MM-DD
            if record_date < date_from.isoformat():
                continue
        # Filter by date_to (inclusive — API uses end_time <= date_to + ' 23:59:59')
        if date_to:
            record_date = r["end_time"][:10]
            if record_date > date_to.isoformat():
                continue
        expected.append(r)

    # Sort by end_time descending (matching API behavior)
    expected.sort(key=lambda r: r["end_time"], reverse=True)
    return expected


# ---------------------------------------------------------------------------
# Setup: ensure SN mapping is available (done once)
# ---------------------------------------------------------------------------

_sn_mapping_uploaded = False


def _ensure_sn_mapping():
    global _sn_mapping_uploaded
    if not _sn_mapping_uploaded:
        app_client = api.app.test_client()
        _setup_sn_mapping(app_client)
        _sn_mapping_uploaded = True


# ---------------------------------------------------------------------------
# Property 12: Query completeness
# ---------------------------------------------------------------------------

class TestQueryCompleteness:
    """Property 12: Query completeness.

    **Validates: Requirements 9.1-9.4**

    For any set of stored records matching a filter, the query API SHALL return
    all and only those records.
    """

    @given(data=records_with_filter())
    @settings(max_examples=200, deadline=None)
    def test_query_returns_all_and_only_matching_records(self, data):
        """For any stored records and filter combination, the API returns exactly
        the matching records — no more, no less."""
        _ensure_sn_mapping()
        _clear_tables()

        records = data["records"]
        target_sn = data["target_sn"]
        item_filter = data["item_filter"]
        date_from = data["date_from"]
        date_to = data["date_to"]

        # Insert all records into DB
        _insert_records(records)

        # Build query URL
        url = f'/api/raw-records?sn={target_sn}'
        if item_filter:
            url += f'&item={item_filter}'
        if date_from:
            url += f'&from={date_from.isoformat()}'
        if date_to:
            url += f'&to={date_to.isoformat()}'

        # Query the API
        app_client = api.app.test_client()
        resp = app_client.get(url)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.get_json()}"

        result = resp.get_json()
        returned_records = result["records"]

        # Compute expected records
        expected = _compute_expected_records(records, target_sn, item_filter, date_from, date_to)

        # Verify count matches (completeness: all matching records returned)
        assert len(returned_records) == len(expected), (
            f"Expected {len(expected)} records, got {len(returned_records)}. "
            f"SN={target_sn}, item={item_filter}, from={date_from}, to={date_to}"
        )

        # Verify each returned record matches expected (correctness: only matching records)
        for i, (ret, exp) in enumerate(zip(returned_records, expected)):
            assert ret["item"] == exp["item"], (
                f"Record {i}: item mismatch. Expected '{exp['item']}', got '{ret['item']}'"
            )
            assert ret["status"] == exp["status"], (
                f"Record {i}: status mismatch. Expected '{exp['status']}', got '{ret['status']}'"
            )
            assert ret["end_time"] == exp["end_time"], (
                f"Record {i}: end_time mismatch. Expected '{exp['end_time']}', got '{ret['end_time']}'"
            )
            assert ret["effective_cp"] == exp["effective_cp"], (
                f"Record {i}: effective_cp mismatch. "
                f"Expected '{exp['effective_cp']}', got '{ret['effective_cp']}'"
            )

        # Verify SN metadata is correct
        assert result["sn"] == target_sn

    @given(data=records_with_filter())
    @settings(max_examples=100, deadline=None)
    def test_no_records_from_other_sns_leak_through(self, data):
        """The API SHALL NOT return records belonging to a different SN."""
        _ensure_sn_mapping()
        _clear_tables()

        records = data["records"]
        target_sn = data["target_sn"]

        # Insert all records into DB
        _insert_records(records)

        # Query without filters (just SN)
        app_client = api.app.test_client()
        resp = app_client.get(f'/api/raw-records?sn={target_sn}')
        assert resp.status_code == 200

        result = resp.get_json()
        returned_records = result["records"]

        # Every returned record must belong to the target SN
        # (The API doesn't return serial_number in each record, but we can verify
        # by checking the count matches what we expect for this SN only)
        expected_for_sn = [r for r in records if r["serial_number"] == target_sn]
        assert len(returned_records) == len(expected_for_sn), (
            f"Expected {len(expected_for_sn)} records for SN={target_sn}, "
            f"got {len(returned_records)}. Other SN records may have leaked through."
        )

    @given(data=records_with_filter())
    @settings(max_examples=100, deadline=None)
    def test_results_ordered_by_end_time_desc(self, data):
        """Returned records SHALL be ordered by end_time descending."""
        _ensure_sn_mapping()
        _clear_tables()

        records = data["records"]
        target_sn = data["target_sn"]

        _insert_records(records)

        app_client = api.app.test_client()
        resp = app_client.get(f'/api/raw-records?sn={target_sn}')
        assert resp.status_code == 200

        result = resp.get_json()
        returned_records = result["records"]

        end_times = [r["end_time"] for r in returned_records]
        assert end_times == sorted(end_times, reverse=True), (
            f"Records not ordered by end_time DESC: {end_times}"
        )
