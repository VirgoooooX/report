"""
Property-based tests for checkitem_generator.py.

**Validates: Requirements 3.1, 3.2, 3.3**

Property 4: Filename keyword detection — For any filename containing exactly
one known keyword, identification SHALL return the correct item type.

Property 5: CSV field extraction round-trip — For any generated CSV with known
field values, parsing SHALL extract all fields correctly.
"""

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from checkitem_generator import identify_csv_type, parse_csv_file, attribute_anomaly_cps


# ---------------------------------------------------------------------------
# Known keywords and their expected canonical item types
# ---------------------------------------------------------------------------

KEYWORD_TO_EXPECTED_TYPE = {
    "BT-OTA": "BT-OTA",
    "Charging": "Charging",
    "FACT": "FACT",
    "ISB": "ISB",
    "Touch-Cal-Post": "Touch-CAL-Post",
    "COSMETIC": "Cosmetic",
}

KEYWORDS = list(KEYWORD_TO_EXPECTED_TYPE.keys())


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Characters allowed in filename prefix/suffix (alphanumeric + dashes + underscores)
_filename_chars = st.sampled_from(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
)

# Random prefix/suffix for filenames (0 to 30 chars)
filename_part_strategy = st.text(alphabet=_filename_chars, min_size=0, max_size=30)

# Pick a random keyword from the 6 known keywords
keyword_strategy = st.sampled_from(KEYWORDS)


@st.composite
def filename_with_one_keyword(draw):
    """Generate a filename containing exactly one known keyword.

    Constructs: {prefix}{keyword}{suffix}.csv
    Ensures the prefix and suffix do not accidentally contain another keyword.
    """
    keyword = draw(keyword_strategy)
    prefix = draw(filename_part_strategy)
    suffix = draw(filename_part_strategy)

    # Ensure prefix+suffix don't accidentally contain another keyword
    combined = (prefix + suffix).lower()
    for other_kw in KEYWORDS:
        if other_kw.lower() != keyword.lower():
            assume(other_kw.lower() not in combined)

    filename = f"{prefix}{keyword}{suffix}.csv"
    return filename, keyword


@st.composite
def filename_without_keywords(draw):
    """Generate a filename that does NOT contain any known keyword."""
    # Use only lowercase letters and digits to avoid accidental keyword matches
    safe_chars = st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_")
    name = draw(st.text(alphabet=safe_chars, min_size=1, max_size=40))

    # Ensure no keyword appears in the generated name
    name_lower = name.lower()
    for kw in KEYWORDS:
        assume(kw.lower() not in name_lower)

    return f"{name}.csv"


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------

class TestFilenameKeywordDetection:
    """Property 4: Filename keyword detection.

    **Validates: Requirements 3.1**

    For any filename containing exactly one known keyword, identification
    SHALL return the correct item type.
    """

    @given(data=filename_with_one_keyword())
    @settings(max_examples=300, deadline=None)
    def test_single_keyword_returns_correct_type(self, data):
        """A filename with exactly one keyword returns the correct item type."""
        filename, keyword = data
        expected_type = KEYWORD_TO_EXPECTED_TYPE[keyword]
        result = identify_csv_type(filename)
        assert result == expected_type, (
            f"For filename '{filename}' with keyword '{keyword}', "
            f"expected '{expected_type}' but got '{result}'"
        )

    @given(filename=filename_without_keywords())
    @settings(max_examples=300, deadline=None)
    def test_no_keyword_returns_none(self, filename):
        """A filename with no known keywords returns None."""
        result = identify_csv_type(filename)
        assert result is None, (
            f"For filename '{filename}' with no keywords, "
            f"expected None but got '{result}'"
        )


# ---------------------------------------------------------------------------
# Property 5: CSV field extraction round-trip
# ---------------------------------------------------------------------------

# CSV column order as defined in the spec:
# Site, Product, SerialNumber, Special Build Name, Special Build Description,
# Unit Number, Station ID, Test Pass/Fail Status, StartTime, EndTime, Version,
# List of Failing Tests, REL Event, [param columns...]
_CSV_HEADER_COLUMNS = [
    "Site",
    "Product",
    "SerialNumber",
    "Special Build Name",
    "Special Build Description",
    "Unit Number",
    "Station ID",
    "Test Pass/Fail Status",
    "StartTime",
    "EndTime",
    "Version",
    "List of Failing Tests",
    "REL Event",
]

# Strategies for generating field values
_alnum_chars = st.sampled_from(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
)

serial_number_strategy = st.text(alphabet=_alnum_chars, min_size=1, max_size=20)

rel_event_strategy = st.sampled_from([
    "REL_T0", "CP_100%", "BC_CWCB_SHORT_140%", "TC_300CYCLES",
    "RANDOM_DROP_1M_PB", "REL_T500", "CP_200%",
])

status_strategy = st.sampled_from(["PASS", "FAIL"])

end_time_strategy = st.from_regex(
    r"2026-0[1-9]-[012][0-9] [012][0-9]:[0-5][0-9]:[0-5][0-9]",
    fullmatch=True,
)

version_strategy = st.from_regex(r"[0-9]\.[0-9]\.[0-9]", fullmatch=True)

station_id_strategy = st.text(alphabet=_alnum_chars, min_size=3, max_size=15)

# Safe text that won't contain commas, newlines, or quotes (avoids CSV escaping issues)
# Also excludes leading/trailing spaces since parse_csv_file strips values.
_safe_text_chars = st.sampled_from(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
)
safe_text_strategy = st.text(alphabet=_safe_text_chars, min_size=0, max_size=20)

# Metadata prefixes that the parser skips — the Site (first) column must not
# start with any of these.
_METADATA_PREFIXES = (
    "Display Name", "PDCA Priority", "Upper Limit", "Lower Limit",
    "Measurement Unit",
)

# Strategy for the Site column (first column) that avoids metadata prefixes
@st.composite
def _site_strategy(draw):
    """Generate a Site value that won't be mistaken for a metadata row."""
    value = draw(safe_text_strategy)
    for prefix in _METADATA_PREFIXES:
        assume(not value.startswith(prefix))
    return value

item_type_strategy = st.sampled_from([
    "BT-OTA", "Charging", "FACT", "ISB", "Touch-CAL-Post", "Cosmetic",
])

# Parameter name strategy (simple alphanumeric names)
param_name_strategy = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"),
    min_size=3,
    max_size=15,
)

# Parameter value strategy (floats with reasonable range)
param_value_strategy = st.floats(
    min_value=-1000.0, max_value=1000.0,
    allow_nan=False, allow_infinity=False,
)


@st.composite
def csv_record_pass(draw):
    """Generate a PASS CSV record with known field values."""
    serial_number = draw(serial_number_strategy)
    rel_event = draw(rel_event_strategy)
    end_time = draw(end_time_strategy)
    version = draw(version_strategy)
    station_id = draw(station_id_strategy)
    item_type = draw(item_type_strategy)

    # Build the CSV row values (matching _CSV_HEADER_COLUMNS order)
    row_values = [
        draw(_site_strategy()),     # Site (must not start with metadata prefix)
        draw(safe_text_strategy),   # Product
        serial_number,              # SerialNumber
        draw(safe_text_strategy),   # Special Build Name
        draw(safe_text_strategy),   # Special Build Description
        draw(safe_text_strategy),   # Unit Number
        station_id,                 # Station ID
        "PASS",                     # Test Pass/Fail Status
        draw(end_time_strategy),    # StartTime
        end_time,                   # EndTime
        version,                    # Version
        "",                         # List of Failing Tests (empty for PASS)
        rel_event,                  # REL Event
    ]

    expected = {
        "serial_number": serial_number,
        "rel_event": rel_event,
        "status": "PASS",
        "end_time": end_time,
        "failing_tests": "",
        "station_id": station_id,
        "version": version,
        "item": item_type,
        "test_params": None,
    }

    return row_values, expected, item_type, []


@st.composite
def csv_record_fail(draw):
    """Generate a FAIL CSV record with known field values and parameters."""
    serial_number = draw(serial_number_strategy)
    rel_event = draw(rel_event_strategy)
    end_time = draw(end_time_strategy)
    version = draw(version_strategy)
    station_id = draw(station_id_strategy)
    item_type = draw(item_type_strategy)
    # Use safe_text_strategy (no spaces at edges) for failing_tests
    failing_tests = draw(st.text(
        alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"),
        min_size=3, max_size=30,
    ))

    # Generate 1-3 parameter columns
    num_params = draw(st.integers(min_value=1, max_value=3))
    param_names = draw(st.lists(
        param_name_strategy,
        min_size=num_params,
        max_size=num_params,
        unique=True,
    ))
    param_values = draw(st.lists(
        param_value_strategy,
        min_size=num_params,
        max_size=num_params,
    ))

    # Build the CSV row values
    row_values = [
        draw(_site_strategy()),     # Site (must not start with metadata prefix)
        draw(safe_text_strategy),   # Product
        serial_number,              # SerialNumber
        draw(safe_text_strategy),   # Special Build Name
        draw(safe_text_strategy),   # Special Build Description
        draw(safe_text_strategy),   # Unit Number
        station_id,                 # Station ID
        "FAIL",                     # Test Pass/Fail Status
        draw(end_time_strategy),    # StartTime
        end_time,                   # EndTime
        version,                    # Version
        failing_tests,              # List of Failing Tests
        rel_event,                  # REL Event
    ]

    # Add parameter values to the row
    for val in param_values:
        row_values.append(str(val))

    expected_params = {name: val for name, val in zip(param_names, param_values)}

    expected = {
        "serial_number": serial_number,
        "rel_event": rel_event,
        "status": "FAIL",
        "end_time": end_time,
        "failing_tests": failing_tests,
        "station_id": station_id,
        "version": version,
        "item": item_type,
        "test_params": expected_params,
    }

    return row_values, expected, item_type, param_names


def _build_csv(header_columns, rows):
    """Build a CSV string from header columns and data rows."""
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header_columns)
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


class TestCSVFieldExtractionRoundTrip:
    """Property 5: CSV field extraction round-trip.

    **Validates: Requirements 3.2, 3.3**

    For any generated CSV with known field values, parsing SHALL extract
    all fields correctly.
    """

    @given(data=csv_record_pass())
    @settings(max_examples=200, deadline=None)
    def test_pass_record_fields_extracted_correctly(self, data):
        """For a PASS record, all key fields are extracted correctly."""
        row_values, expected, item_type, _ = data

        csv_content = _build_csv(_CSV_HEADER_COLUMNS, [row_values])
        records = parse_csv_file(csv_content, item_type)

        assert len(records) == 1, (
            f"Expected 1 record, got {len(records)} for CSV:\n{csv_content}"
        )
        record = records[0]

        assert record["serial_number"] == expected["serial_number"]
        assert record["rel_event"] == expected["rel_event"]
        assert record["status"] == expected["status"]
        assert record["end_time"] == expected["end_time"]
        assert record["failing_tests"] == expected["failing_tests"]
        assert record["station_id"] == expected["station_id"]
        assert record["version"] == expected["version"]
        assert record["item"] == expected["item"]
        assert record["test_params"] is None

    @given(data=csv_record_fail())
    @settings(max_examples=200, deadline=None)
    def test_fail_record_fields_and_params_extracted_correctly(self, data):
        """For a FAIL record, all key fields and parameter values are extracted."""
        row_values, expected, item_type, param_names = data

        # Build header with parameter columns appended
        header = _CSV_HEADER_COLUMNS + param_names
        csv_content = _build_csv(header, [row_values])
        records = parse_csv_file(csv_content, item_type)

        assert len(records) == 1, (
            f"Expected 1 record, got {len(records)} for CSV:\n{csv_content}"
        )
        record = records[0]

        assert record["serial_number"] == expected["serial_number"]
        assert record["rel_event"] == expected["rel_event"]
        assert record["status"] == expected["status"]
        assert record["end_time"] == expected["end_time"]
        assert record["failing_tests"] == expected["failing_tests"]
        assert record["station_id"] == expected["station_id"]
        assert record["version"] == expected["version"]
        assert record["item"] == expected["item"]

        # Verify parameter extraction for FAIL records
        assert record["test_params"] is not None, (
            "FAIL record should have test_params extracted"
        )
        for param_name, expected_val in expected["test_params"].items():
            assert param_name in record["test_params"], (
                f"Parameter '{param_name}' not found in extracted test_params: "
                f"{record['test_params']}"
            )
            assert abs(record["test_params"][param_name] - expected_val) < 1e-6, (
                f"Parameter '{param_name}': expected {expected_val}, "
                f"got {record['test_params'][param_name]}"
            )

    @given(
        records_data=st.lists(csv_record_pass(), min_size=2, max_size=5),
    )
    @settings(max_examples=100, deadline=None)
    def test_multiple_records_all_extracted(self, records_data):
        """For multiple PASS records, all are extracted with correct fields."""
        # Use the same item_type for all records in this test
        item_type = records_data[0][2]
        rows = [data[0] for data in records_data]

        csv_content = _build_csv(_CSV_HEADER_COLUMNS, rows)
        records = parse_csv_file(csv_content, item_type)

        assert len(records) == len(records_data), (
            f"Expected {len(records_data)} records, got {len(records)}"
        )

        for i, (_, expected, _, _) in enumerate(records_data):
            record = records[i]
            assert record["serial_number"] == expected["serial_number"]
            assert record["rel_event"] == expected["rel_event"]
            assert record["status"] == expected["status"]
            assert record["end_time"] == expected["end_time"]


# ---------------------------------------------------------------------------
# Property 6: Invalid SN exclusion
# ---------------------------------------------------------------------------

from checkitem_generator import filter_valid_sns, sort_and_filter_tfinal


# ---------------------------------------------------------------------------
# Property 7: Post-TFINAL exclusion
# ---------------------------------------------------------------------------

# Strategy for generating timestamps in a sortable format
_timestamp_strategy = st.from_regex(
    r"2026-0[1-9]-[012][0-9] [012][0-9]:[0-5][0-9]:[0-5][0-9]",
    fullmatch=True,
)

# Strategy for SN identifiers used in TFINAL tests
_tfinal_sn_strategy = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
    min_size=5,
    max_size=12,
)

# Non-TFINAL rel_event values
_non_tfinal_events = st.sampled_from([
    "REL_T0", "CP_100%", "BC_CWCB_SHORT_140%", "TC_300CYCLES",
    "RANDOM_DROP_1M_PB", "REL_T500", "CP_200%",
])


@st.composite
def records_with_tfinal(draw):
    """Generate records for multiple SNs, some with REL_TFINAL events.

    Returns:
        (records, sns_with_tfinal, sns_without_tfinal)
        - records: list of record dicts with mixed SNs and events
        - sns_with_tfinal: set of SNs that have a REL_TFINAL event
        - sns_without_tfinal: set of SNs that do NOT have a REL_TFINAL event
    """
    # Generate 1-4 SNs that WILL have a TFINAL event
    tfinal_sn_list = draw(st.lists(
        _tfinal_sn_strategy, min_size=1, max_size=4, unique=True
    ))
    # Generate 0-3 SNs that will NOT have a TFINAL event
    no_tfinal_sn_list = draw(st.lists(
        _tfinal_sn_strategy, min_size=0, max_size=3, unique=True
    ))
    # Ensure no overlap
    no_tfinal_sn_list = [sn for sn in no_tfinal_sn_list if sn not in set(tfinal_sn_list)]

    records = []

    # For each SN with TFINAL: generate some records before TFINAL, the TFINAL itself,
    # and some records after TFINAL
    for sn in tfinal_sn_list:
        # Generate 1-3 records before TFINAL
        num_before = draw(st.integers(min_value=1, max_value=3))
        for _ in range(num_before):
            records.append({
                "serial_number": sn,
                "rel_event": draw(_non_tfinal_events),
                "status": draw(st.sampled_from(["PASS", "FAIL"])),
                "end_time": draw(_timestamp_strategy),
                "failing_tests": "",
                "station_id": "STATION01",
                "version": "1.0.0",
                "item": "FACT",
                "test_params": None,
            })

        # The TFINAL event itself
        tfinal_time = draw(_timestamp_strategy)
        records.append({
            "serial_number": sn,
            "rel_event": "REL_TFINAL",
            "status": "PASS",
            "end_time": tfinal_time,
            "failing_tests": "",
            "station_id": "STATION01",
            "version": "1.0.0",
            "item": "FACT",
            "test_params": None,
        })

        # Generate 1-3 records AFTER TFINAL (these should be excluded)
        # We ensure end_time > tfinal_time by using a time guaranteed to be later
        num_after = draw(st.integers(min_value=1, max_value=3))
        for _ in range(num_after):
            # Generate a timestamp that is strictly greater than tfinal_time
            after_time = draw(_timestamp_strategy)
            # Ensure it's strictly after tfinal_time by appending 'z' logic won't work;
            # instead, we'll just set it to a known-later value
            # Use a simple approach: if after_time <= tfinal_time, make it later
            if after_time <= tfinal_time:
                # Force a later timestamp by using "2026-09-28 23:59:59"
                after_time = "2026-09-28 23:59:59"
            records.append({
                "serial_number": sn,
                "rel_event": draw(_non_tfinal_events),
                "status": draw(st.sampled_from(["PASS", "FAIL"])),
                "end_time": after_time,
                "failing_tests": "",
                "station_id": "STATION01",
                "version": "1.0.0",
                "item": "FACT",
                "test_params": None,
            })

    # For each SN without TFINAL: generate some records
    for sn in no_tfinal_sn_list:
        num_records = draw(st.integers(min_value=1, max_value=4))
        for _ in range(num_records):
            records.append({
                "serial_number": sn,
                "rel_event": draw(_non_tfinal_events),
                "status": draw(st.sampled_from(["PASS", "FAIL"])),
                "end_time": draw(_timestamp_strategy),
                "failing_tests": "",
                "station_id": "STATION01",
                "version": "1.0.0",
                "item": "FACT",
                "test_params": None,
            })

    # Shuffle records to simulate unordered input
    shuffled = draw(st.permutations(records))

    return list(shuffled), set(tfinal_sn_list), set(no_tfinal_sn_list)


class TestSortAndFilterTfinal:
    """Property 7: Post-TFINAL exclusion.

    **Validates: Requirements 4.1, 4.2**

    For any SN with a REL_TFINAL event, no records with EndTime after TFINAL
    SHALL appear in the output. Output SHALL be sorted by end_time ascending.
    """

    @given(data=records_with_tfinal())
    @settings(max_examples=300, deadline=None)
    def test_output_sorted_by_end_time_ascending(self, data):
        """Output records are sorted by end_time in ascending order."""
        records, _, _ = data

        result = sort_and_filter_tfinal(records)

        end_times = [r["end_time"] for r in result]
        assert end_times == sorted(end_times), (
            f"Output is not sorted by end_time ascending: {end_times}"
        )

    @given(data=records_with_tfinal())
    @settings(max_examples=300, deadline=None)
    def test_no_records_after_tfinal_for_sn_with_tfinal(self, data):
        """For any SN with REL_TFINAL, no output records have end_time > TFINAL's end_time."""
        records, sns_with_tfinal, _ = data

        result = sort_and_filter_tfinal(records)

        # Find the TFINAL end_time for each SN (first TFINAL when sorted)
        sorted_input = sorted(records, key=lambda r: r.get("end_time", ""))
        tfinal_times: dict[str, str] = {}
        for rec in sorted_input:
            sn = rec["serial_number"]
            if sn not in tfinal_times and rec["rel_event"] == "REL_TFINAL":
                tfinal_times[sn] = rec["end_time"]

        # Verify no output record for a TFINAL SN has end_time > TFINAL time
        for rec in result:
            sn = rec["serial_number"]
            if sn in tfinal_times:
                assert rec["end_time"] <= tfinal_times[sn], (
                    f"Record for SN '{sn}' has end_time '{rec['end_time']}' "
                    f"which is after TFINAL time '{tfinal_times[sn]}'"
                )

    @given(data=records_with_tfinal())
    @settings(max_examples=300, deadline=None)
    def test_records_for_sns_without_tfinal_all_preserved(self, data):
        """Records for SNs without a TFINAL event are all preserved in the output."""
        records, _, sns_without_tfinal = data

        result = sort_and_filter_tfinal(records)

        # Count input records for non-TFINAL SNs
        input_count = sum(
            1 for r in records if r["serial_number"] in sns_without_tfinal
        )
        # Count output records for non-TFINAL SNs
        output_count = sum(
            1 for r in result if r["serial_number"] in sns_without_tfinal
        )

        assert output_count == input_count, (
            f"Expected {input_count} records for SNs without TFINAL, "
            f"got {output_count}. SNs without TFINAL: {sns_without_tfinal}"
        )


# ---------------------------------------------------------------------------
# Property 6: Invalid SN exclusion
# ---------------------------------------------------------------------------

# Strategy for generating a valid serial number (alphanumeric, 5-20 chars)
_sn_chars = st.sampled_from(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
)
sn_strategy = st.text(alphabet=_sn_chars, min_size=5, max_size=20)


@st.composite
def records_with_mixed_sns(draw):
    """Generate a set of valid SNs and a list of records with a mix of valid and invalid SNs.

    Returns:
        (valid_sns, records, expected_valid_count)
        - valid_sns: set of valid serial numbers
        - records: list of record dicts with a mix of valid and invalid SNs
        - expected_valid_count: number of records that have a valid SN
    """
    # Generate a set of valid SNs (at least 1)
    valid_sn_list = draw(st.lists(sn_strategy, min_size=1, max_size=10, unique=True))
    valid_sns = set(valid_sn_list)

    # Generate a set of invalid SNs (guaranteed not in valid_sns)
    invalid_sn_list = draw(st.lists(sn_strategy, min_size=1, max_size=10, unique=True))
    # Filter out any that accidentally match valid SNs
    invalid_sn_list = [sn for sn in invalid_sn_list if sn not in valid_sns]
    # If all got filtered, create a guaranteed-invalid SN
    if not invalid_sn_list:
        invalid_sn_list = ["INVALID_" + valid_sn_list[0] + "_X"]

    # Build records: mix of valid and invalid SNs
    all_sns = [(sn, True) for sn in valid_sn_list] + [(sn, False) for sn in invalid_sn_list]
    # Shuffle the order
    shuffled = draw(st.permutations(all_sns))

    records = []
    expected_valid_count = 0
    for sn, is_valid in shuffled:
        record = {
            "serial_number": sn,
            "rel_event": "CP_100%",
            "status": "PASS",
            "end_time": "2026-05-15 10:00:00",
            "failing_tests": "",
            "station_id": "STATION01",
            "version": "1.0.0",
            "item": "FACT",
            "test_params": None,
        }
        records.append(record)
        if is_valid:
            expected_valid_count += 1

    return valid_sns, records, expected_valid_count


class TestSNFiltering:
    """Property 6: Invalid SN exclusion.

    **Validates: Requirements 3.4**

    For any set of records containing both valid and invalid SNs, filtering
    SHALL produce output containing only valid SNs.
    """

    @given(data=records_with_mixed_sns())
    @settings(max_examples=300, deadline=None)
    def test_output_contains_only_valid_sns(self, data):
        """All records in the output have serial_number in valid_sns."""
        valid_sns, records, _ = data

        result = filter_valid_sns(records, valid_sns)

        for record in result:
            assert record["serial_number"] in valid_sns, (
                f"Output contains record with invalid SN '{record['serial_number']}' "
                f"which is not in valid_sns: {valid_sns}"
            )

    @given(data=records_with_mixed_sns())
    @settings(max_examples=300, deadline=None)
    def test_no_invalid_sns_in_output(self, data):
        """No records with invalid SNs appear in the output."""
        valid_sns, records, _ = data

        result = filter_valid_sns(records, valid_sns)

        invalid_sns_in_output = [
            r["serial_number"] for r in result
            if r["serial_number"] not in valid_sns
        ]
        assert invalid_sns_in_output == [], (
            f"Found invalid SNs in output: {invalid_sns_in_output}"
        )

    @given(data=records_with_mixed_sns())
    @settings(max_examples=300, deadline=None)
    def test_output_count_equals_valid_input_count(self, data):
        """The count of output records equals the count of input records with valid SNs."""
        valid_sns, records, expected_valid_count = data

        result = filter_valid_sns(records, valid_sns)

        assert len(result) == expected_valid_count, (
            f"Expected {expected_valid_count} valid records in output, "
            f"got {len(result)}. "
            f"Valid SNs: {valid_sns}, "
            f"Input SNs: {[r['serial_number'] for r in records]}"
        )


# ---------------------------------------------------------------------------
# Property 8: Anomaly events attributed to valid CP
# ---------------------------------------------------------------------------

# Anomaly events that should be attributed to the preceding valid CP
_ANOMALY_EVENTS = ["REL FA RETEST", "SEND TO FA", "STOP TEST", "RETURN TO REL"]

# Normal (non-anomaly) CP events for generating test data
_NORMAL_CP_EVENTS = [
    "REL_T0", "CP_100%", "BC_CWCB_SHORT_140%", "TC_300CYCLES",
    "RANDOM_DROP_1M_PB", "REL_T500", "CP_200%", "BC_CWCB_SHORT_100%",
]


@st.composite
def event_sequence_for_anomaly_attribution(draw):
    """Generate a sequence of records mixing normal CPs and anomaly events for one or more SNs.

    Returns:
        records: list of record dicts sorted by end_time ascending, with a mix of
                 normal CP events and anomaly events per SN.
    """
    # Generate 1-3 unique SNs
    sn_list = draw(st.lists(
        st.text(
            alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
            min_size=5, max_size=12,
        ),
        min_size=1, max_size=3, unique=True,
    ))

    records = []

    for sn in sn_list:
        # Generate 3-8 events for this SN
        num_events = draw(st.integers(min_value=3, max_value=8))

        for _ in range(num_events):
            # Decide if this event is an anomaly or normal CP
            is_anomaly = draw(st.booleans())
            if is_anomaly:
                rel_event = draw(st.sampled_from(_ANOMALY_EVENTS))
            else:
                rel_event = draw(st.sampled_from(_NORMAL_CP_EVENTS))

            end_time = draw(st.from_regex(
                r"2026-0[1-9]-[012][0-9] [012][0-9]:[0-5][0-9]:[0-5][0-9]",
                fullmatch=True,
            ))

            records.append({
                "serial_number": sn,
                "rel_event": rel_event,
                "status": draw(st.sampled_from(["PASS", "FAIL"])),
                "end_time": end_time,
                "failing_tests": "",
                "station_id": "STATION01",
                "version": "1.0.0",
                "item": "FACT",
                "test_params": None,
            })

    # Sort by end_time ascending (required input for attribute_anomaly_cps)
    records.sort(key=lambda r: r["end_time"])
    return records


class TestAnomalyCPAttribution:
    """Property 8: Anomaly events attributed to valid CP.

    **Validates: Requirements 4.3**

    For any sequence of events, anomaly events SHALL have effective_cp equal to
    the most recent preceding non-anomaly CP for that SN. Non-anomaly events
    SHALL have effective_cp equal to their own rel_event.
    """

    @given(records=event_sequence_for_anomaly_attribution())
    @settings(max_examples=300, deadline=None)
    def test_anomaly_events_attributed_to_preceding_valid_cp(self, records):
        """Anomaly events get effective_cp from the most recent preceding non-anomaly CP for that SN."""
        result = attribute_anomaly_cps(records)

        # Track the last valid CP per SN as we iterate (same logic the function should use)
        last_valid_cp: dict[str, str] = {}

        for rec in result:
            sn = rec["serial_number"]
            rel_event = rec["rel_event"]

            if rel_event in _ANOMALY_EVENTS:
                # Anomaly event: effective_cp should be the last valid CP for this SN
                if sn in last_valid_cp:
                    assert rec["effective_cp"] == last_valid_cp[sn], (
                        f"Anomaly event '{rel_event}' for SN '{sn}' should have "
                        f"effective_cp='{last_valid_cp[sn]}' but got '{rec['effective_cp']}'"
                    )
                else:
                    # No preceding valid CP — effective_cp should be rel_event itself
                    assert rec["effective_cp"] == rel_event, (
                        f"Anomaly event '{rel_event}' for SN '{sn}' with no preceding CP "
                        f"should have effective_cp='{rel_event}' but got '{rec['effective_cp']}'"
                    )
            else:
                # Normal CP: effective_cp should be itself
                assert rec["effective_cp"] == rel_event, (
                    f"Normal event '{rel_event}' for SN '{sn}' should have "
                    f"effective_cp='{rel_event}' but got '{rec['effective_cp']}'"
                )
                # Update tracker
                last_valid_cp[sn] = rel_event

    @given(records=event_sequence_for_anomaly_attribution())
    @settings(max_examples=300, deadline=None)
    def test_non_anomaly_events_have_effective_cp_equal_to_rel_event(self, records):
        """Non-anomaly events always have effective_cp equal to their own rel_event."""
        result = attribute_anomaly_cps(records)

        for rec in result:
            if rec["rel_event"] not in _ANOMALY_EVENTS:
                assert rec["effective_cp"] == rec["rel_event"], (
                    f"Non-anomaly event '{rec['rel_event']}' for SN '{rec['serial_number']}' "
                    f"should have effective_cp='{rec['rel_event']}' but got '{rec['effective_cp']}'"
                )

    @given(records=event_sequence_for_anomaly_attribution())
    @settings(max_examples=300, deadline=None)
    def test_all_records_have_effective_cp_set(self, records):
        """Every record in the output has an effective_cp field set (not None or missing)."""
        result = attribute_anomaly_cps(records)

        for rec in result:
            assert "effective_cp" in rec, (
                f"Record for SN '{rec['serial_number']}' with rel_event "
                f"'{rec['rel_event']}' is missing 'effective_cp' field"
            )
            assert rec["effective_cp"] is not None, (
                f"Record for SN '{rec['serial_number']}' with rel_event "
                f"'{rec['rel_event']}' has effective_cp=None"
            )
            assert rec["effective_cp"] != "", (
                f"Record for SN '{rec['serial_number']}' with rel_event "
                f"'{rec['rel_event']}' has empty effective_cp"
            )


# ---------------------------------------------------------------------------
# Property 9: Last record wins (deduplication)
# ---------------------------------------------------------------------------

from checkitem_generator import deduplicate_records


# Strategy for generating SN identifiers for deduplication tests
_dedup_sn_strategy = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
    min_size=5, max_size=12,
)

# Strategy for effective_cp values
_dedup_cp_strategy = st.sampled_from([
    "REL_T0", "CP_100%", "BC_CWCB_SHORT_140%", "TC_300CYCLES",
    "RANDOM_DROP_1M_PB", "REL_T500", "CP_200%", "BC_CWCB_SHORT_100%",
])

# Strategy for item types
_dedup_item_strategy = st.sampled_from([
    "BT-OTA", "Charging", "FACT", "ISB", "Touch-CAL-Post", "Cosmetic",
])

# Timestamp strategy for deduplication tests
_dedup_timestamp_strategy = st.from_regex(
    r"2026-0[1-9]-[012][0-9] [012][0-9]:[0-5][0-9]:[0-5][0-9]",
    fullmatch=True,
)


@st.composite
def records_with_duplicates(draw):
    """Generate records where some share the same (serial_number, effective_cp, item) key.

    Returns:
        (records, groups)
        - records: list of record dicts sorted by end_time ascending (with effective_cp set)
        - groups: dict mapping (sn, cp, item) -> list of end_times for that group
    """
    # Generate 2-5 unique keys (sn, cp, item)
    num_keys = draw(st.integers(min_value=2, max_value=5))
    keys = []
    for _ in range(num_keys):
        sn = draw(_dedup_sn_strategy)
        cp = draw(_dedup_cp_strategy)
        item = draw(_dedup_item_strategy)
        keys.append((sn, cp, item))

    # Deduplicate keys (in case of collisions)
    keys = list(set(keys))
    assume(len(keys) >= 2)

    records = []
    groups: dict[tuple[str, str, str], list[str]] = {}

    for key in keys:
        sn, cp, item = key
        # Generate 1-4 records per key (some groups will have duplicates)
        num_records = draw(st.integers(min_value=1, max_value=4))
        end_times = []

        for _ in range(num_records):
            end_time = draw(_dedup_timestamp_strategy)
            end_times.append(end_time)

            records.append({
                "serial_number": sn,
                "effective_cp": cp,
                "item": item,
                "rel_event": cp,
                "status": draw(st.sampled_from(["PASS", "FAIL"])),
                "end_time": end_time,
                "failing_tests": "",
                "station_id": "STATION01",
                "version": "1.0.0",
                "test_params": None,
            })

        groups[key] = end_times

    # Sort by end_time ascending (expected input for deduplicate_records)
    records.sort(key=lambda r: r["end_time"])

    return records, groups


class TestDeduplication:
    """Property 9: Last record wins (deduplication).

    **Validates: Requirements 4.4**

    For any group of records with same (SN, effective_cp, item), the output
    SHALL contain exactly one record with the maximum EndTime.
    """

    @given(data=records_with_duplicates())
    @settings(max_examples=300, deadline=None)
    def test_one_record_per_unique_group(self, data):
        """For each unique (SN, effective_cp, item) group, exactly one record appears in the output."""
        records, groups = data

        result = deduplicate_records(records)

        # Count output records per group key
        output_keys = [
            (r["serial_number"], r["effective_cp"], r["item"])
            for r in result
        ]

        # Each unique group should appear exactly once
        for key in groups:
            count = output_keys.count(key)
            assert count == 1, (
                f"Group {key} should appear exactly once in output, "
                f"but appeared {count} times"
            )

    @given(data=records_with_duplicates())
    @settings(max_examples=300, deadline=None)
    def test_output_record_has_max_end_time(self, data):
        """The output record for each group has the maximum end_time from that group."""
        records, groups = data

        result = deduplicate_records(records)

        # Build lookup from output
        output_by_key = {
            (r["serial_number"], r["effective_cp"], r["item"]): r
            for r in result
        }

        for key, end_times in groups.items():
            expected_max_time = max(end_times)
            output_record = output_by_key.get(key)
            assert output_record is not None, (
                f"Group {key} not found in output"
            )
            assert output_record["end_time"] == expected_max_time, (
                f"Group {key}: expected max end_time '{expected_max_time}' "
                f"but got '{output_record['end_time']}'"
            )

    @given(data=records_with_duplicates())
    @settings(max_examples=300, deadline=None)
    def test_output_count_equals_unique_groups(self, data):
        """Total output count equals the number of unique (SN, effective_cp, item) groups."""
        records, groups = data

        result = deduplicate_records(records)

        assert len(result) == len(groups), (
            f"Expected {len(groups)} unique groups in output, "
            f"got {len(result)} records"
        )
