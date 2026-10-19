#!/usr/bin/env python3
"""Tests for Mi Scale 2 BLE advertisement packet decoding and clock invariants."""

import unittest
from datetime import datetime as dt


def decode_miscale_packet(hex_value: str, fallback_timestamp: int = 1729340000):
    """
    Decodes a Mi Body Composition Scale 2 advertisement payload (Service 0x181B / adType 22).
    Follows the exact decoder contract in miscale/miscale_ble.py.
    """
    if len(hex_value) < 30:
        return None

    data = bytes.fromhex(hex_value[4:])
    if len(data) < 13:
        return None

    ctrlByte1 = data[1]
    isStabilized = bool(ctrlByte1 & (1 << 5))
    hasImpedance = bool(ctrlByte1 & (1 << 1))

    if not isStabilized:
        return None

    if hex_value[4:6] == "03":
        # lbs mode
        lb_weight = int((hex_value[28:30] + hex_value[26:28]), 16) * 0.01
        weight = round(lb_weight / 2.2046, 1)
    else:
        # kg mode: raw value in 0.005 kg units (little-endian)
        weight = round((((data[12] & 0xFF) << 8) | (data[11] & 0xFF)) * 0.005, 1)

    impedance = ((data[10] & 0xFF) << 8) | (data[9] & 0xFF) if hasImpedance else 0
    year = int((data[3] << 8) | data[2])

    if year < 2020:
        unix_time = fallback_timestamp
    else:
        dt_str = f"{year},{int(data[4])},{int(data[5])},{int(data[6])},{int(data[7])},{int(data[8])}"
        parsed_dt = dt.strptime(dt_str, "%Y,%m,%d,%H,%M,%S")
        unix_time = int(parsed_dt.timestamp())

    return {
        "unix_time": unix_time,
        "weight": weight,
        "impedance": impedance,
        "is_stabilized": isStabilized,
        "has_impedance": hasImpedance,
    }


def build_miscale_hex(
    weight_kg: float,
    impedance: int = 500,
    year: int = 2026,
    month: int = 10,
    day: int = 19,
    hour: int = 14,
    minute: int = 30,
    second: int = 0,
    stabilized: bool = True,
    has_impedance: bool = True,
    unit_lbs: bool = False,
) -> str:
    """Helper to assemble a canonical 13+ byte hex payload for testing."""
    # Prefix (2 bytes UUID/header)
    prefix = "1b18"
    if unit_lbs:
        unit_byte = 0x03
    else:
        unit_byte = 0x02

    ctrl_byte = 0
    if stabilized:
        ctrl_byte |= 1 << 5
    if has_impedance:
        ctrl_byte |= 1 << 1

    year_bytes = year.to_bytes(2, "little")
    raw_weight = int(round(weight_kg / 0.005))
    weight_bytes = raw_weight.to_bytes(2, "little")
    imp_bytes = impedance.to_bytes(2, "little")

    payload = bytearray([
        unit_byte,
        ctrl_byte,
        year_bytes[0],
        year_bytes[1],
        month,
        day,
        hour,
        minute,
        second,
        imp_bytes[0],
        imp_bytes[1],
        weight_bytes[0],
        weight_bytes[1],
    ])

    return prefix + payload.hex()


class TestMiScaleBleParser(unittest.TestCase):
    """Test suite for Mi Scale 2 BLE advertisement parsing."""

    def test_stabilized_reading_with_impedance(self):
        """Standard adult weigh-in with impedance (e.g. 84.2 kg, 515 Ohm)."""
        hex_data = build_miscale_hex(
            weight_kg=84.2,
            impedance=515,
            year=2026,
            month=10,
            day=19,
            hour=8,
            minute=15,
            second=22,
            stabilized=True,
            has_impedance=True,
        )
        res = decode_miscale_packet(hex_data)
        self.assertIsNotNone(res)
        self.assertEqual(res["weight"], 84.2)
        self.assertEqual(res["impedance"], 515)
        self.assertTrue(res["is_stabilized"])
        self.assertTrue(res["has_impedance"])
        # Check date components
        dt_val = dt.fromtimestamp(res["unix_time"])
        self.assertEqual(dt_val.year, 2026)
        self.assertEqual(dt_val.month, 10)
        self.assertEqual(dt_val.day, 19)
        self.assertEqual(dt_val.hour, 8)
        self.assertEqual(dt_val.minute, 15)
        self.assertEqual(dt_val.second, 22)

    def test_stabilized_reading_without_impedance(self):
        """Weigh-in with socks on: stabilized weight present, but impedance is 0."""
        hex_data = build_miscale_hex(
            weight_kg=83.0,
            impedance=0,
            year=2026,
            stabilized=True,
            has_impedance=False,
        )
        res = decode_miscale_packet(hex_data)
        self.assertIsNotNone(res)
        self.assertEqual(res["weight"], 83.0)
        self.assertEqual(res["impedance"], 0)
        self.assertTrue(res["is_stabilized"])
        self.assertFalse(res["has_impedance"])

    def test_unstabilized_reading_rejected(self):
        """While person is stepping onto scale or moving, isStabilized is False and packet must be skipped."""
        hex_data = build_miscale_hex(
            weight_kg=80.0,
            stabilized=False,
            has_impedance=False,
        )
        res = decode_miscale_packet(hex_data)
        self.assertIsNone(res)

    def test_uninitialized_rtc_clock_fallback(self):
        """
        Scale battery change resets internal RTC to epoch 1970 (year < 2020).
        Parser must substitute current host NTP timestamp to prevent false unsync rejection.
        """
        fallback_ts = 1729340500
        hex_data = build_miscale_hex(
            weight_kg=84.0,
            impedance=500,
            year=1970,  # Uninitialized scale clock
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            stabilized=True,
            has_impedance=True,
        )
        res = decode_miscale_packet(hex_data, fallback_timestamp=fallback_ts)
        self.assertIsNotNone(res)
        self.assertEqual(res["unix_time"], fallback_ts)
        self.assertEqual(res["weight"], 84.0)

    def test_short_or_corrupt_packet_ignored(self):
        """Short or corrupt BLE advertisement strings must not raise exceptions."""
        self.assertIsNone(decode_miscale_packet("1b1802"))
        self.assertIsNone(decode_miscale_packet(""))
        self.assertIsNone(decode_miscale_packet("nonhexstring_short"))


if __name__ == "__main__":
    unittest.main()
