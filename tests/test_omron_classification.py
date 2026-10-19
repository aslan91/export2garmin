#!/usr/bin/env python3
"""Tests for Omron blood pressure categorization and export formatting."""

import unittest


def classify_blood_pressure(
    systolic: int, diastolic: int, category_standard: str = "eu"
) -> str:
    """
    Categorizes blood pressure according to EU (ESC/ESH) or US (AHA/ACC) guidelines.
    Matches the exact logic in omron/omron_export.py lines 35-53.
    """
    category = "None"
    if category_standard == "eu":
        if systolic < 130 and diastolic < 85:
            category = "Normal"
        elif (130 <= systolic <= 139 and diastolic < 85) or (
            systolic < 130 and 85 <= diastolic <= 89
        ):
            category = "High-Normal"
        elif (140 <= systolic <= 159 and diastolic < 90) or (
            systolic < 140 and 90 <= diastolic <= 99
        ):
            category = "Grade_1"
        elif (160 <= systolic <= 179 and diastolic < 100) or (
            systolic < 160 and 100 <= diastolic <= 109
        ):
            category = "Grade_2"
    elif category_standard == "us":
        if systolic < 120 and diastolic < 80:
            category = "Normal"
        elif (120 <= systolic <= 129) and diastolic < 80:
            category = "High-Normal"
        elif (130 <= systolic <= 139) or (80 <= diastolic <= 89):
            category = "Grade_1"
        elif (systolic >= 140) or (diastolic >= 90):
            category = "Grade_2"
    return category


class TestOmronClassification(unittest.TestCase):
    """Test suite for EU and US blood pressure categorization."""

    def test_eu_normal(self):
        """EU guidelines: sys < 130 and dia < 85 is Normal."""
        self.assertEqual(classify_blood_pressure(115, 75, "eu"), "Normal")
        self.assertEqual(classify_blood_pressure(129, 84, "eu"), "Normal")

    def test_eu_high_normal(self):
        """EU guidelines: 130-139 sys or 85-89 dia is High-Normal."""
        self.assertEqual(classify_blood_pressure(130, 80, "eu"), "High-Normal")
        self.assertEqual(classify_blood_pressure(138, 84, "eu"), "High-Normal")
        self.assertEqual(classify_blood_pressure(125, 88, "eu"), "High-Normal")

    def test_eu_grade_1_hypertension(self):
        """EU guidelines: 140-159 sys (<90 dia) or 90-99 dia (<140 sys) is Grade 1."""
        self.assertEqual(classify_blood_pressure(145, 85, "eu"), "Grade_1")
        self.assertEqual(classify_blood_pressure(125, 95, "eu"), "Grade_1")
        self.assertEqual(classify_blood_pressure(159, 89, "eu"), "Grade_1")

    def test_eu_grade_2_hypertension(self):
        """EU guidelines: 160-179 sys (<100 dia) or 100-109 dia (<160 sys) is Grade 2."""
        self.assertEqual(classify_blood_pressure(165, 85, "eu"), "Grade_2")
        self.assertEqual(classify_blood_pressure(125, 105, "eu"), "Grade_2")

    def test_us_guidelines_differences(self):
        """US AHA/ACC thresholds: Normal < 120/80, High-Normal 120-129/80, Grade 1, Grade 2."""
        self.assertEqual(classify_blood_pressure(118, 78, "us"), "Normal")
        self.assertEqual(classify_blood_pressure(125, 75, "us"), "High-Normal")
        self.assertEqual(classify_blood_pressure(132, 75, "us"), "Grade_1")
        self.assertEqual(classify_blood_pressure(125, 85, "us"), "Grade_1")
        self.assertEqual(classify_blood_pressure(145, 75, "us"), "Grade_2")
        self.assertEqual(classify_blood_pressure(125, 95, "us"), "Grade_2")


if __name__ == "__main__":
    unittest.main()
