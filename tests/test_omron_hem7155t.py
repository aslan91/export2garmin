#!/usr/bin/env python3
"""Tests for Omron HEM-7155T BLE binary record parsing."""

import datetime
import importlib.util
import os
import sys
import unittest

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
omron_dir = os.path.join(repo_root, "omron")
device_specific_dir = os.path.join(omron_dir, "deviceSpecific")

for p in [omron_dir, device_specific_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Dynamically import hem-7155t.py (contains hyphen in module filename)
spec = importlib.util.spec_from_file_location(
    "hem7155t", os.path.join(device_specific_dir, "hem-7155t.py")
)
hem7155t_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hem7155t_mod)


def build_omron_hem7155t_record(
    sys_val: int = 120,
    dia_val: int = 80,
    bpm_val: int = 65,
    year_val: int = 2026,
    month_val: int = 10,
    day_val: int = 19,
    hour_val: int = 8,
    minute_val: int = 30,
    second_val: int = 15,
    mov_val: int = 0,
    ihb_val: int = 0,
) -> bytes:
    """Helper to assemble a 16-byte HEM-7155T EEPROM record with exact bit layout."""
    total_bits = 128
    big_int = 0

    def set_bits(val, first, last):
        nonlocal big_int
        shift = total_bits - (last + 1)
        num_bits = (last - first) + 1
        masked = val & ((1 << num_bits) - 1)
        big_int |= masked << shift

    # Note: sys is stored as (sys - 25)
    set_bits(sys_val - 25, 120, 127)
    set_bits(dia_val, 112, 119)
    set_bits(bpm_val, 104, 111)
    set_bits(year_val - 2000, 98, 103)
    set_bits(hour_val, 91, 95)
    set_bits(day_val, 86, 90)
    set_bits(month_val, 82, 85)
    set_bits(ihb_val, 81, 81)
    set_bits(mov_val, 80, 80)
    set_bits(second_val, 74, 79)
    set_bits(minute_val, 68, 73)

    return big_int.to_bytes(16, "little")


class TestOmronHem7155tDriver(unittest.TestCase):
    """Test suite for Omron HEM-7155T bitwise record decoding."""

    def setUp(self):
        self.driver = hem7155t_mod.deviceSpecificDriver()

    def test_normal_measurement_record(self):
        """Standard blood pressure reading: 120/80 mmHg, 65 bpm."""
        raw = build_omron_hem7155t_record(
            sys_val=120,
            dia_val=80,
            bpm_val=65,
            year_val=2026,
            month_val=10,
            day_val=19,
            hour_val=8,
            minute_val=30,
            second_val=15,
            mov_val=0,
            ihb_val=0,
        )
        parsed = self.driver.deviceSpecific_ParseRecordFormat(raw)
        self.assertEqual(parsed["sys"], 120)
        self.assertEqual(parsed["dia"], 80)
        self.assertEqual(parsed["bpm"], 65)
        self.assertEqual(parsed["mov"], 0)
        self.assertEqual(parsed["ihb"], 0)
        self.assertEqual(
            parsed["datetime"], datetime.datetime(2026, 10, 19, 8, 30, 15)
        )

    def test_hypertensive_reading_with_flags(self):
        """Elevated blood pressure with body movement and irregular heartbeat flags set."""
        raw = build_omron_hem7155t_record(
            sys_val=145,
            dia_val=92,
            bpm_val=78,
            year_val=2026,
            month_val=10,
            day_val=19,
            hour_val=19,
            minute_val=45,
            second_val=50,
            mov_val=1,
            ihb_val=1,
        )
        parsed = self.driver.deviceSpecific_ParseRecordFormat(raw)
        self.assertEqual(parsed["sys"], 145)
        self.assertEqual(parsed["dia"], 92)
        self.assertEqual(parsed["bpm"], 78)
        self.assertEqual(parsed["mov"], 1)
        self.assertEqual(parsed["ihb"], 1)

    def test_seconds_clamping(self):
        """Omron firmware sometimes yields seconds > 59 (up to 63); driver clamps to 59."""
        raw = build_omron_hem7155t_record(
            sys_val=118,
            dia_val=76,
            bpm_val=60,
            second_val=62,  # > 59
        )
        parsed = self.driver.deviceSpecific_ParseRecordFormat(raw)
        self.assertEqual(parsed["datetime"].second, 59)

    def test_driver_metadata_invariants(self):
        """Verify device-specific hardware invariants."""
        self.assertEqual(self.driver.deviceEndianess, "little")
        self.assertEqual(self.driver.recordByteSize, 0x10)  # 16 bytes
        self.assertEqual(self.driver.transmissionBlockSize, 0x10)
        self.assertEqual(self.driver.perUserRecordsCountList, [60, 60])  # 2 users, 60 records each


if __name__ == "__main__":
    unittest.main()
