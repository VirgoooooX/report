"""
Property-based tests for store_raw_records function (Task 8.3).

**Validates: Requirements 8.2, 8.3**

Property 10: PASS records have NULL test_params — For any stored PASS record,
test_params SHALL be NULL.

Property 11: FAIL records preserve test parameters — For any stored FAIL record
with parameters, deserializing test_params JSON SHALL produce the original
parameter dict.
"""

import json
import os
import tempfile

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Set up a fresh test DB before importing modules that use db
TEST_DB = tempfile.mktemp(suffix='.db')
import db
db.DB_PATH = TEST_DB
db.init_db()

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from checkitem_generator import store_raw_records


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_alnum_chars = st.sampled_from(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
)

serial_number_strategy = st.text(alphabet=_alnum_chars, min_size=3, max_size=15)

rel_event_strategy = st.sampled_from([
    "REL_T0", "CP_100%", "BC_CWCB_SHORT_140%", "TC_300CYCLES",
    "RANDOM_DROP_1M_PB", "REL_T500", "CP_200%", "BC_CWCB_SHORT_100%",
])

item_strategy = st.sampled_from([
    "BT-OTA", "Charging", "FACT", "ISB", "Touch-CAL-Post", "Cosmetic",
])

end_time_strategy = st.from_regex(
    r"2026-0[1-9]-[012][0-9] [012][0-9]:[0-5][0-9]:[0-5][0-9]",
    fullmatch=True,
)

version_strategy = st.from_regex(r"[0-9]\.[0-9]\.[0-9]", fullmatch=True)

station_id_strategy = st.text(alphabet=_alnum_chars, min_size=3, max_size=20)

# Parameter name strategy: alphanumeric with underscores, non-empty
param_name_strategy = st.text(
    alphabet=st.sampled_from(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"
    ),
    min_size=3,
    max_size=20,
)

# Parameter value strategy: finite floats in a reasonable range
param_value_strategy = st.floats(
    min_value=-10000.0, max_value=10000.0,
    allow_nan=False, allow_infinity=False,
)

# Source file strategy
source_file_strategy = st.text(alphabet=_alnum_chars, min_size=3, max_size=15).map(
    lambda s: s + ".csv"
)


@st.composite
def pass_record(draw):
    """Generate a PASS record dict."""
    return {
        "serial_number": draw(serial_number_strategy),
        "rel_event": draw(rel_event_strategy),
        "effective_cp": draw(rel_event_strategy),
        "item": draw(item_strategy),
        "status": "PASS",
        "end_time": draw(end_time_strategy),
        "failing_tests": "",
        "station_id": draw(station_id_strategy),
        "version": draw(version_strategy),
        "test_params": None,
        "source_file": draw(source_file_strategy),
    }


@st.composite
def fail_record_with_params(draw):
    """Generate a FAIL record dict with non-empty test_params."""
    num_params = draw(st.integers(min_value=1, max_value=5))
    param_names = draw(st.lists(
        param_name_strategy, min_size=num_params, max_size=num_params, unique=True
    ))
    param_values = draw(st.lists(
        param_value_strategy, min_size=num_params, max_size=num_params
    ))
    test_params = dict(zip(param_names, param_values))

    failing_test = draw(st.text(
        alphabet=st.sampled_from(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_ "
        ),
        min_size=3, max_size=30,
    ))

    return {
        "serial_number": draw(serial_number_strategy),
        "rel_event": draw(rel_event_strategy),
        "effective_cp": draw(rel_event_strategy),
        "item": draw(item_strategy),
        "status": "FAIL",
        "end_time": draw(end_time_strategy),
        "failing_tests": failing_test,
        "station_id": draw(station_id_strategy),
        "version": draw(version_strategy),
        "test_params": test_params,
        "source_file": draw(source_file_strategy),
    }


@st.composite
def fail_record_without_params(draw):
    """Generate a FAIL record dict with no test_params (None)."""
    failing_test = draw(st.text(
        alphabet=st.sampled_from(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_ "
        ),
        min_size=3, max_size=30,
    ))

    return {
        "serial_number": draw(serial_number_strategy),
        "rel_event": draw(rel_event_strategy),
        "effective_cp": draw(rel_event_strategy),
        "item": draw(item_strategy),
        "status": "FAIL",
        "end_time": draw(end_time_strategy),
        "failing_tests": failing_test,
        "station_id": draw(station_id_strategy),
        "version": draw(version_strategy),
        "test_params": None,
        "source_file": draw(source_file_strategy),
    }


@st.composite
def mixed_records(draw):
    """Generate a list of mixed PASS and FAIL records."""
    pass_recs = draw(st.lists(pass_record(), min_size=0, max_size=5))
    fail_with_params = draw(st.lists(fail_record_with_params(), min_size=0, max_size=5))
    fail_without_params = draw(st.lists(fail_record_without_params(), min_size=0, max_size=3))

    all_records = pass_recs + fail_with_params + fail_without_params
    # Ensure at least one record
    assume(len(all_records) > 0)

    # Shuffle
    shuffled = draw(st.permutations(all_records))
    return list(shuffled)


# ---------------------------------------------------------------------------
# Helper: fresh DB for each test
# ---------------------------------------------------------------------------

def _clear_tables():
    """Clear raw_check_item_records and import_batches tables."""
    conn = db.get_conn()
    conn.execute("DELETE FROM raw_check_item_records")
    conn.execute("DELETE FROM import_batches")
    conn.commit()
    conn.close()


def _make_summary(records):
    """Create a summary dict from a list of records."""
    sns = set(r["serial_number"] for r in records)
    return {
        "file_count": 1,
        "record_count": len(records),
        "valid_sn_count": len(sns),
    }


# ---------------------------------------------------------------------------
# Property 10: PASS records have NULL test_params
# ---------------------------------------------------------------------------

class TestPassRecordsNullTestParams:
    """Property 10: PASS records have NULL test_params.

    **Validates: Requirements 8.3**

    For any stored PASS record, test_params SHALL be NULL.
    """

    @given(records=mixed_records())
    @settings(max_examples=200, deadline=None)
    def test_pass_records_have_null_test_params_in_db(self, records):
        """For any stored PASS record, test_params is NULL in the database."""
        _clear_tables()

        summary = _make_summary(records)
        batch_id = store_raw_records(records, summary)

        conn = db.get_conn()
        stored_pass_rows = conn.execute(
            "SELECT * FROM raw_check_item_records WHERE import_batch_id = ? AND status = 'PASS'",
            (batch_id,)
        ).fetchall()
        conn.close()

        # Count expected PASS records
        expected_pass_count = sum(1 for r in records if r["status"] == "PASS")
        assert len(stored_pass_rows) == expected_pass_count, (
            f"Expected {expected_pass_count} PASS rows, got {len(stored_pass_rows)}"
        )

        for row in stored_pass_rows:
            assert row["test_params"] is None, (
                f"PASS record for SN '{row['serial_number']}' has non-NULL test_params: "
                f"{row['test_params']}"
            )


# ---------------------------------------------------------------------------
# Property 11: FAIL records preserve test parameters
# ---------------------------------------------------------------------------

class TestFailRecordsPreserveTestParams:
    """Property 11: FAIL records preserve test parameters.

    **Validates: Requirements 8.2**

    For any stored FAIL record with parameters, deserializing test_params JSON
    SHALL produce the original parameter dict.
    """

    @given(records=st.lists(fail_record_with_params(), min_size=1, max_size=5))
    @settings(max_examples=200, deadline=None)
    def test_fail_records_preserve_test_params(self, records):
        """For any stored FAIL record with params, JSON deserialization matches original."""
        _clear_tables()

        summary = _make_summary(records)
        batch_id = store_raw_records(records, summary)

        conn = db.get_conn()
        stored_rows = conn.execute(
            "SELECT * FROM raw_check_item_records WHERE import_batch_id = ? AND status = 'FAIL'",
            (batch_id,)
        ).fetchall()
        conn.close()

        assert len(stored_rows) == len(records), (
            f"Expected {len(records)} FAIL rows, got {len(stored_rows)}"
        )

        # Build a lookup by serial_number + end_time for matching
        # (since multiple records could have same SN, use index-based matching via order)
        # Records are inserted in order, so stored_rows should match insertion order
        for i, (original, stored) in enumerate(zip(records, stored_rows)):
            assert stored["test_params"] is not None, (
                f"FAIL record #{i} for SN '{stored['serial_number']}' has NULL test_params "
                f"but original had: {original['test_params']}"
            )

            deserialized = json.loads(stored["test_params"])
            original_params = original["test_params"]

            # Verify all original keys are present
            assert set(deserialized.keys()) == set(original_params.keys()), (
                f"FAIL record #{i}: key mismatch. "
                f"Expected keys: {set(original_params.keys())}, "
                f"got: {set(deserialized.keys())}"
            )

            # Verify values match (float comparison with tolerance)
            for key in original_params:
                expected_val = original_params[key]
                actual_val = deserialized[key]
                assert abs(actual_val - expected_val) < 1e-6, (
                    f"FAIL record #{i}, param '{key}': "
                    f"expected {expected_val}, got {actual_val}"
                )

    @given(records=st.lists(fail_record_without_params(), min_size=1, max_size=5))
    @settings(max_examples=100, deadline=None)
    def test_fail_records_without_params_have_null_test_params(self, records):
        """FAIL records with no test_params (None) store NULL in the database."""
        _clear_tables()

        summary = _make_summary(records)
        batch_id = store_raw_records(records, summary)

        conn = db.get_conn()
        stored_rows = conn.execute(
            "SELECT * FROM raw_check_item_records WHERE import_batch_id = ? AND status = 'FAIL'",
            (batch_id,)
        ).fetchall()
        conn.close()

        for row in stored_rows:
            assert row["test_params"] is None, (
                f"FAIL record without params for SN '{row['serial_number']}' "
                f"has non-NULL test_params: {row['test_params']}"
            )
