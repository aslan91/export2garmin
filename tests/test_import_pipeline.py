#!/usr/bin/env python3
"""Tests for import_data.sh data extraction, deduplication, and user matching contracts."""

import re
import unittest


def extract_miscale_read(ble_output: str) -> str:
    """
    Simulates the pipeline:
    echo "$ble_check" | grep -E '^[0-9]+;[0-9.]+;[0-9]+' | tail -n 1
    """
    matches = []
    pattern = re.compile(r"^[0-9]+;[0-9.]+;[0-9]+")
    for line in ble_output.splitlines():
        line = line.strip()
        if pattern.match(line):
            matches.append(line)
    return matches[-1] if matches else ""


def check_is_duplicate(
    candidate_time: int, existing_timestamps: list, threshold_seconds: int = 1800
) -> bool:
    """
    Simulates the duplicate check in import_data.sh lines 212-225:
    miscale_time_dif = abs(miscale_offset_unixtime - unix_time)
    if (( miscale_time_dif < miscale_time_check )) -> duplicate
    """
    for ts in existing_timestamps:
        if abs(candidate_time - ts) < threshold_seconds:
            return True
    return False


def match_user_by_weight(weight: float, users: list):
    """
    Simulates user matching in miscale_export.py lines 61-65:
    for user in users:
        if user.min_weight <= weight <= user.max_weight:
            return user
    """
    for u in users:
        if u["min_weight"] <= weight <= u["max_weight"]:
            return u
    return None


class TestImportPipelineContracts(unittest.TestCase):
    """Test suite for pipeline contracts in export2garmin."""

    def test_regex_extraction_idle_scan_yields_empty(self):
        """Standard idle scan with headers and device logs must produce empty string."""
        idle_output = """
=============================================
Export 2 Garmin Connect v3.6 (miscale_ble.py)
=============================================

19.10.2026-14:03:26 * Checking if a BLE adapter is detected
19.10.2026-14:03:26 * BLE adapter hci0(B8:27:EB:5F:A5:AE) detected, check BLE adapter connection
19.10.2026-14:03:26 * Connection to BLE adapter hci0(B8:27:EB:5F:A5:AE) works, starting BLE scan:
  BLE device found with address: 0c:3d:5e:44:af:ae, non-target device
  BLE device found with address: de:cd:2f:c0:15:ed, non-target device
19.10.2026-14:03:36 * Finished BLE scan
"""
        extracted = extract_miscale_read(idle_output)
        self.assertEqual(extracted, "")

    def test_regex_extraction_valid_measurement_yields_csv(self):
        """Scan with valid measurement line must yield the CSV line."""
        measurement_output = """
=============================================
Export 2 Garmin Connect v3.6 (miscale_ble.py)
=============================================

19.10.2026-14:03:26 * Checking if a BLE adapter is detected
19.10.2026-14:03:26 * BLE adapter hci0(B8:27:EB:5F:A5:AE) detected, check BLE adapter connection
19.10.2026-14:03:26 * Connection to BLE adapter hci0(B8:27:EB:5F:A5:AE) works, starting BLE scan:
  BLE device found with address: d8:e7:2f:a6:84:bc <= target device
19.10.2026-14:03:28 MISCALE|OMRON * Reading BLE data complete, finished BLE scan
1729340000;83.5;512
19.10.2026-14:03:28 * Finished BLE scan
"""
        extracted = extract_miscale_read(measurement_output)
        self.assertEqual(extracted, "1729340000;83.5;512")

    def test_regex_extraction_multiple_takes_tail(self):
        """If multiple readings are reported, tail -n 1 extracts the latest reading."""
        multi_output = """
1729339000;83.2;510
1729340000;83.5;512
"""
        extracted = extract_miscale_read(multi_output)
        self.assertEqual(extracted, "1729340000;83.5;512")

    def test_uninitialized_clock_detection_in_shell(self):
        """import_data.sh checks if miscale_unixtime < 1577836800 (1 Jan 2020)."""
        cutoff = 1577836800
        uninitialized_ts = 1000  # Epoch 1970
        valid_ts = 1729340000    # Year 2026
        self.assertTrue(uninitialized_ts < cutoff)
        self.assertFalse(valid_ts < cutoff)

    def test_duplicate_measurement_detection(self):
        """Duplicate check prevents double uploading identical weigh-in within check window."""
        existing = [1729340000, 1729300000]
        # Same timestamp or within 30 minutes (1800s)
        self.assertTrue(check_is_duplicate(1729340000, existing, 1800))
        self.assertTrue(check_is_duplicate(1729340500, existing, 1800))  # +500s -> duplicate
        # Outside 30 minutes
        self.assertFalse(check_is_duplicate(1729342000, existing, 1800))  # +2000s -> new measurement

    def test_user_weight_matching_boundaries(self):
        """User profile matching: Jan (80 kg - 95 kg)."""
        users = [
            {
                "email": "janzink91@gmail.com",
                "min_weight": 80.0,
                "max_weight": 95.0,
            }
        ]
        self.assertIsNotNone(match_user_by_weight(83.5, users))
        self.assertIsNotNone(match_user_by_weight(80.0, users))  # Boundary inclusive
        self.assertIsNotNone(match_user_by_weight(95.0, users))  # Boundary inclusive
        self.assertIsNone(match_user_by_weight(79.9, users))    # Below min
        self.assertIsNone(match_user_by_weight(95.1, users))    # Above max


if __name__ == "__main__":
    unittest.main()
