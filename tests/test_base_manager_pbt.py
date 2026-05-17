"""
Property-based tests for base_manager.py.

**Validates: Requirements 1.1, 1.2, 1.3**

Property 1: SN mapping round-trip — For any valid SN mapping data,
serializing to CSV then parsing SHALL produce equivalent mappings.

Property 2: CP exclusion invariant — For any parsed CP schedule, the output
SHALL never contain excluded CP names, and remaining CPs maintain original
relative order.

Property 3: Test plan extraction — For any valid test plan CSV, parsing SHALL
produce a mapping where each WF has a non-empty list of test names.
"""
import csv
import os
import tempfile

import hypothesis
from hypothesis import given, settings, assume
from hypothesis import strategies as st

import base_manager


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Serial numbers: non-empty alphanumeric strings (realistic SN format)
sn_strategy = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
    min_size=1,
    max_size=12,
)

# Config: from known config choices
config_strategy = st.sampled_from(["R1FNF", "R2CNM", "R3", "R4"])

# WF ID: string numbers like "1", "14.1", "29.3"
wf_id_strategy = st.one_of(
    st.integers(min_value=1, max_value=50).map(str),
    st.tuples(
        st.integers(min_value=1, max_value=50),
        st.integers(min_value=1, max_value=9),
    ).map(lambda t: f"{t[0]}.{t[1]}"),
)

# Unit number: non-empty alphanumeric strings with dashes (e.g., ER2-1-1)
unit_number_strategy = st.from_regex(r"E[A-Z][0-9]-[0-9]{1,2}-[0-9]{1,3}", fullmatch=True)

# A single SN mapping entry
sn_entry_strategy = st.fixed_dictionaries({
    "serial_number": sn_strategy,
    "config": config_strategy,
    "wf_id": wf_id_strategy,
    "unit_number": unit_number_strategy,
})

# A list of SN mapping entries (1 to 50 entries)
sn_mapping_list_strategy = st.lists(sn_entry_strategy, min_size=1, max_size=50)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_sn_mapping_csv(entries):
    """Write SN mapping entries to a temporary CSV file and return its path."""
    fieldnames = ["serial_number", "config", "Product", "unit_number", "start_date", "wf_id"]
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            writer.writerow({
                "serial_number": entry["serial_number"],
                "config": entry["config"],
                "Product": "B529",
                "unit_number": entry["unit_number"],
                "start_date": "20260416",
                "wf_id": entry["wf_id"],
            })
    return path


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------

class TestSnMappingRoundTrip:
    """Property 1: SN mapping round-trip.

    **Validates: Requirements 1.1**

    For any valid SN mapping data, serializing to CSV then parsing
    SHALL produce equivalent mappings (first occurrence wins for duplicates).
    """

    @given(entries=sn_mapping_list_strategy)
    @settings(max_examples=200, deadline=None)
    def test_round_trip_preserves_mappings(self, entries):
        """Parsing a CSV written from valid entries produces the same mapping."""
        # Compute expected result: first occurrence wins for duplicate SNs
        expected_mapping = {}
        for entry in entries:
            sn = entry["serial_number"]
            if sn not in expected_mapping:
                expected_mapping[sn] = {
                    "config": entry["config"],
                    "wf_id": entry["wf_id"],
                    "unit_number": entry["unit_number"],
                }

        # Write to CSV and parse
        path = write_sn_mapping_csv(entries)
        try:
            result = base_manager.parse_sn_mapping(path)

            # Verify sn_count matches unique SNs
            assert result["sn_count"] == len(expected_mapping)

            # Verify each SN mapping matches expected (first occurrence)
            for sn, expected_info in expected_mapping.items():
                assert sn in result["sn_mapping"], f"SN {sn} missing from parsed result"
                actual_info = result["sn_mapping"][sn]
                assert actual_info["config"] == expected_info["config"]
                assert actual_info["wf_id"] == expected_info["wf_id"]
                assert actual_info["unit_number"] == expected_info["unit_number"]

            # Verify no extra SNs in result
            assert len(result["sn_mapping"]) == len(expected_mapping)
        finally:
            os.remove(path)

    @given(entries=sn_mapping_list_strategy)
    @settings(max_examples=200, deadline=None)
    def test_config_quantities_match(self, entries):
        """Config quantities reflect the count of unique SNs per config (first occurrence wins)."""
        # Compute expected config quantities based on first-occurrence semantics
        seen_sns = set()
        expected_quantities = {}
        for entry in entries:
            sn = entry["serial_number"]
            if sn not in seen_sns:
                seen_sns.add(sn)
                config = entry["config"]
                expected_quantities[config] = expected_quantities.get(config, 0) + 1

        # Write to CSV and parse
        path = write_sn_mapping_csv(entries)
        try:
            result = base_manager.parse_sn_mapping(path)
            assert result["config_quantities"] == expected_quantities
        finally:
            os.remove(path)

    @given(entries=sn_mapping_list_strategy)
    @settings(max_examples=100, deadline=None)
    def test_duplicate_sns_keep_first(self, entries):
        """When duplicate SNs exist, only the first occurrence is kept."""
        # Intentionally create duplicates by doubling the list
        doubled = entries + entries

        # Expected: first occurrence wins
        expected_mapping = {}
        for entry in entries:
            sn = entry["serial_number"]
            if sn not in expected_mapping:
                expected_mapping[sn] = {
                    "config": entry["config"],
                    "wf_id": entry["wf_id"],
                    "unit_number": entry["unit_number"],
                }

        path = write_sn_mapping_csv(doubled)
        try:
            result = base_manager.parse_sn_mapping(path)

            # Count should be unique SNs only
            assert result["sn_count"] == len(expected_mapping)

            # Values should match first occurrence
            for sn, expected_info in expected_mapping.items():
                actual_info = result["sn_mapping"][sn]
                assert actual_info["config"] == expected_info["config"]
                assert actual_info["wf_id"] == expected_info["wf_id"]
                assert actual_info["unit_number"] == expected_info["unit_number"]
        finally:
            os.remove(path)


# ---------------------------------------------------------------------------
# Property 2: CP exclusion invariant
# ---------------------------------------------------------------------------

# Excluded CP names (must match base_manager.EXCLUDED_CPS, including
# schedule boundary markers — T0 / REL_T0 / End / TFinal / REL_TFINAL —
# which are now filtered alongside the operational CPs).
EXCLUDED_CP_NAMES = [
    'REL FA RETEST',
    'SEND TO FA',
    'STOP TEST',
    'RETURN TO REL',
    'T0',
    'REL_T0',
    'End',
    'TFinal',
    'REL_TFINAL',
]

# Valid CP names (realistic alphanumeric names)
VALID_CP_NAMES = [
    'AAB_T0',
    'LTHS_100HRS',
    'LTHS_200HRS',
    'LTHS_300HRS',
    'LTHS_400HRS',
    'LTHS_500HRS',
    'OP HS_100HRS',
    'OP HS_200HRS',
    'BC_CWCB_SHORT_100%',
    'BC_CWCB_SHORT_140%',
    'TC_300CYCLES',
    'TC_500CYCLES',
    'RANDOM DROP 1M PB_>200',
    'RANDOM DROP 2M PB_>200',
    'TUMBLE_50DROPS',
    'TUMBLE_100DROPS',
]

# Strategy: generate a CP name that is either valid or excluded
cp_name_strategy = st.one_of(
    st.sampled_from(VALID_CP_NAMES),
    st.sampled_from(EXCLUDED_CP_NAMES),
)

# Strategy: a single CP schedule row
cp_row_strategy = st.fixed_dictionaries({
    'cp_name': cp_name_strategy,
    'test_idx': st.integers(min_value=0, max_value=5),
})

# Strategy: a WF with a list of CPs (1 to 15 CPs per WF)
wf_strategy = st.fixed_dictionaries({
    'wf_id': st.integers(min_value=1, max_value=50).map(str),
    'cps': st.lists(cp_row_strategy, min_size=1, max_size=15),
})

# Strategy: multiple WFs (1 to 10 WFs) with unique wf_ids
@st.composite
def cp_schedule_draw(draw):
    """Generate a list of WFs with unique wf_ids."""
    num_wfs = draw(st.integers(min_value=1, max_value=10))
    # Draw unique wf_ids
    wf_ids = draw(
        st.lists(
            st.integers(min_value=1, max_value=50).map(str),
            min_size=num_wfs,
            max_size=num_wfs,
            unique=True,
        )
    )
    wf_list = []
    for wf_id in wf_ids:
        cps = draw(st.lists(cp_row_strategy, min_size=1, max_size=15))
        wf_list.append({'wf_id': wf_id, 'cps': cps})
    return wf_list

cp_schedule_strategy = cp_schedule_draw()


def write_cp_schedule_csv(wf_list):
    """Write CP schedule entries to a temporary CSV file and return its path.

    Produces a CSV with columns matching the WaterfallCheckpointSchedule format:
    wf_id, wf id_cp, wf id_cp total, wf id_cp_nci, wf id_cp total_nci,
    test category, rel event cp, checkin, wf test, wf test_cp, wf test_cp total,
    wf id_rel event, wf id_rel event_prev, wf id_rel event_next
    """
    fieldnames = [
        'wf_id', 'wf id_cp', 'wf id_cp total', 'wf id_cp_nci',
        'wf id_cp total_nci', 'test category', 'rel event cp', 'checkin',
        'wf test', 'wf test_cp', 'wf test_cp total', 'wf id_rel event',
        'wf id_rel event_prev', 'wf id_rel event_next',
    ]
    fd, path = tempfile.mkstemp(suffix='.csv')
    os.close(fd)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for wf in wf_list:
            wf_id = wf['wf_id']
            total_cps = len(wf['cps'])
            for idx, cp in enumerate(wf['cps']):
                writer.writerow({
                    'wf_id': wf_id,
                    'wf id_cp': str(idx),
                    'wf id_cp total': str(total_cps),
                    'wf id_cp_nci': str(idx),
                    'wf id_cp total_nci': str(total_cps),
                    'test category': cp['cp_name'],
                    'rel event cp': cp['cp_name'],
                    'checkin': '',
                    'wf test': str(cp['test_idx']),
                    'wf test_cp': str(idx),
                    'wf test_cp total': str(total_cps),
                    'wf id_rel event': f"{wf_id}_{cp['cp_name']}",
                    'wf id_rel event_prev': '',
                    'wf id_rel event_next': '',
                })
    return path


class TestCpExclusionInvariant:
    """Property 2: CP exclusion invariant.

    **Validates: Requirements 1.2**

    For any parsed CP schedule, the output SHALL never contain excluded CP
    names, and remaining CPs maintain original relative order.
    """

    @given(wf_list=cp_schedule_strategy)
    @settings(max_examples=200, deadline=None)
    def test_excluded_cps_never_in_output(self, wf_list):
        """No excluded CP names appear in the parsed output."""
        path = write_cp_schedule_csv(wf_list)
        try:
            result = base_manager.parse_checkpoint_schedule(path)

            # Check that no excluded CP appears in any WF's CP list
            for wf_id, cp_list in result['cp_schedule'].items():
                for cp_name in cp_list:
                    assert cp_name not in base_manager.EXCLUDED_CPS, (
                        f"Excluded CP '{cp_name}' found in WF {wf_id} output"
                    )
        finally:
            os.remove(path)

    @given(wf_list=cp_schedule_strategy)
    @settings(max_examples=200, deadline=None)
    def test_relative_order_preserved(self, wf_list):
        """Non-excluded CPs maintain their original relative order."""
        path = write_cp_schedule_csv(wf_list)
        try:
            result = base_manager.parse_checkpoint_schedule(path)

            # Each WF has a unique wf_id, so compute expected per WF directly
            for wf in wf_list:
                wf_id = wf['wf_id']
                # Expected: filter out excluded, deduplicate preserving order
                expected_cps = []
                seen = set()
                for cp in wf['cps']:
                    name = cp['cp_name']
                    if name not in base_manager.EXCLUDED_CPS and name not in seen:
                        seen.add(name)
                        expected_cps.append(name)

                if not expected_cps:
                    # WF with only excluded CPs won't appear in output
                    assert wf_id not in result['cp_schedule'], (
                        f"WF {wf_id} with only excluded CPs should not be in output"
                    )
                else:
                    assert wf_id in result['cp_schedule'], (
                        f"WF {wf_id} with valid CPs should be in output"
                    )
                    actual_cps = result['cp_schedule'][wf_id]
                    assert actual_cps == expected_cps, (
                        f"WF {wf_id}: expected order {expected_cps}, got {actual_cps}"
                    )
        finally:
            os.remove(path)

    @given(wf_list=cp_schedule_strategy)
    @settings(max_examples=200, deadline=None)
    def test_wf_count_and_cp_count_correct(self, wf_list):
        """wf_count and cp_count match the actual filtered output."""
        path = write_cp_schedule_csv(wf_list)
        try:
            result = base_manager.parse_checkpoint_schedule(path)

            # wf_count should equal number of WFs in cp_schedule
            assert result['wf_count'] == len(result['cp_schedule'])

            # cp_count should equal total CPs across all WFs
            expected_cp_count = sum(
                len(cps) for cps in result['cp_schedule'].values()
            )
            assert result['cp_count'] == expected_cp_count
        finally:
            os.remove(path)


# ---------------------------------------------------------------------------
# Property 3: Test plan extraction
# ---------------------------------------------------------------------------

# Strategy: non-empty alphabetic test name
test_name_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    min_size=1,
    max_size=15,
)

# Strategy: a test plan entry — wf_id with 1-3 test names (some may be empty to test filtering)
@st.composite
def _test_plan_entry_draw(draw):
    """Generate a single test plan row with wf_id and up to 3 test names.

    At least one test name is guaranteed non-empty.
    """
    wf_id = draw(st.integers(min_value=1, max_value=50).map(str))
    # Generate 3 test name slots — each is either a non-empty name or empty string
    test_1 = draw(st.one_of(test_name_strategy, st.just("")))
    test_2 = draw(st.one_of(test_name_strategy, st.just("")))
    test_3 = draw(st.one_of(test_name_strategy, st.just("")))

    # Ensure at least one test name is non-empty
    if not test_1 and not test_2 and not test_3:
        # Force at least one non-empty
        test_1 = draw(test_name_strategy)

    return {
        "wf_id": wf_id,
        "test_1": test_1,
        "test_2": test_2,
        "test_3": test_3,
    }

test_plan_entry_strategy = _test_plan_entry_draw()

# Strategy: list of test plan entries with unique wf_ids
@st.composite
def _test_plan_list_draw(draw):
    """Generate a list of test plan entries with unique wf_ids."""
    num_entries = draw(st.integers(min_value=1, max_value=20))
    wf_ids = draw(
        st.lists(
            st.integers(min_value=1, max_value=50).map(str),
            min_size=num_entries,
            max_size=num_entries,
            unique=True,
        )
    )
    entries = []
    for wf_id in wf_ids:
        entry = draw(_test_plan_entry_draw())
        entry["wf_id"] = wf_id  # Override with unique wf_id
        entries.append(entry)
    return entries

test_plan_list_strategy = _test_plan_list_draw()


def write_test_plan_csv(entries):
    """Write test plan entries to a temporary CSV file and return its path."""
    fieldnames = ["wf id", "wf test_1", "wf test_2", "wf test_3"]
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            writer.writerow({
                "wf id": entry["wf_id"],
                "wf test_1": entry["test_1"],
                "wf test_2": entry["test_2"],
                "wf test_3": entry["test_3"],
            })
    return path


class TestTestPlanExtraction:
    """Property 3: Test plan extraction.

    **Validates: Requirements 1.3**

    For any valid test plan CSV, parsing SHALL produce a mapping where each WF
    has a non-empty list of test names.
    """

    @given(entries=test_plan_list_strategy)
    @settings(max_examples=200, deadline=None)
    def test_each_wf_has_nonempty_test_list(self, entries):
        """Each WF in the output has a non-empty list of test names."""
        path = write_test_plan_csv(entries)
        try:
            result = base_manager.parse_test_plan(path)

            # Every WF in the output must have at least one test name
            for wf_id, test_names in result["test_plan"].items():
                assert len(test_names) > 0, (
                    f"WF {wf_id} has empty test name list"
                )
        finally:
            os.remove(path)

    @given(entries=test_plan_list_strategy)
    @settings(max_examples=200, deadline=None)
    def test_test_names_match_nonempty_inputs(self, entries):
        """The test names match the non-empty input test names for each WF."""
        path = write_test_plan_csv(entries)
        try:
            result = base_manager.parse_test_plan(path)

            for entry in entries:
                wf_id = entry["wf_id"]
                # Compute expected non-empty test names in order
                expected_names = [
                    name for name in [entry["test_1"], entry["test_2"], entry["test_3"]]
                    if name
                ]

                assert wf_id in result["test_plan"], (
                    f"WF {wf_id} missing from parsed result"
                )
                assert result["test_plan"][wf_id] == expected_names, (
                    f"WF {wf_id}: expected {expected_names}, got {result['test_plan'][wf_id]}"
                )
        finally:
            os.remove(path)

    @given(entries=test_plan_list_strategy)
    @settings(max_examples=200, deadline=None)
    def test_wf_names_derived_from_test_names(self, entries):
        """WF names are correctly derived by joining test names with ' + '."""
        path = write_test_plan_csv(entries)
        try:
            result = base_manager.parse_test_plan(path)

            for entry in entries:
                wf_id = entry["wf_id"]
                expected_names = [
                    name for name in [entry["test_1"], entry["test_2"], entry["test_3"]]
                    if name
                ]
                expected_wf_name = " + ".join(expected_names)

                assert wf_id in result["wf_names"], (
                    f"WF {wf_id} missing from wf_names"
                )
                assert result["wf_names"][wf_id] == expected_wf_name, (
                    f"WF {wf_id}: expected name '{expected_wf_name}', got '{result['wf_names'][wf_id]}'"
                )
        finally:
            os.remove(path)

    @given(entries=test_plan_list_strategy)
    @settings(max_examples=200, deadline=None)
    def test_wf_count_matches_unique_wfs(self, entries):
        """wf_count matches the number of unique WFs with at least one test."""
        path = write_test_plan_csv(entries)
        try:
            result = base_manager.parse_test_plan(path)

            # All entries have at least one non-empty test (by construction)
            expected_wf_count = len(entries)
            assert result["wf_count"] == expected_wf_count, (
                f"Expected wf_count={expected_wf_count}, got {result['wf_count']}"
            )
        finally:
            os.remove(path)
