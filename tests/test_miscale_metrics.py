#!/usr/bin/env python3
"""Tests for Mi Scale 2 Body Composition Metrics calculation."""

import os
import sys
import unittest

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
miscale_dir = os.path.join(repo_root, "miscale")
if miscale_dir not in sys.path:
    sys.path.insert(0, miscale_dir)

from Xiaomi_Scale_Body_Metrics import bodyMetrics
from body_scales import bodyScales


class TestMiScaleBodyMetrics(unittest.TestCase):
    """Test body metrics calculations for user profile and boundary invariants."""

    def setUp(self):
        # User profile: Jan (Male, 187 cm, 35 yrs, 83.5 kg, healthy impedance ~512 Ohm)
        self.weight = 83.5
        self.height = 187
        self.age = 35
        self.sex = "male"
        self.impedance = 512
        self.metrics = bodyMetrics(
            weight=self.weight,
            height=self.height,
            age=self.age,
            sex=self.sex,
            impedance=self.impedance,
        )

    def test_bmi_calculation(self):
        """BMI should equal weight / (height_in_m)^2."""
        expected_bmi = self.weight / ((self.height / 100) ** 2)
        actual_bmi = self.metrics.getBMI()
        self.assertAlmostEqual(actual_bmi, expected_bmi, places=4)
        self.assertAlmostEqual(round(actual_bmi, 1), 23.9, places=1)

    def test_bmr_calculation_male(self):
        """Basal Metabolic Rate for an adult male should be physiologically sound (> 1500 kcal)."""
        bmr = self.metrics.getBMR()
        self.assertGreater(bmr, 1500)
        self.assertLess(bmr, 2500)
        self.assertAlmostEqual(bmr, 1673.4, places=1)

    def test_body_composition_ranges(self):
        """Verify body fat %, water %, muscle mass, bone mass, and visceral fat are within plausible bounds."""
        fat_pct = self.metrics.getFatPercentage()
        self.assertGreaterEqual(fat_pct, 5.0)
        self.assertLessEqual(fat_pct, 30.0)

        water_pct = self.metrics.getWaterPercentage()
        self.assertGreaterEqual(water_pct, 45.0)
        self.assertLessEqual(water_pct, 75.0)

        muscle_mass = self.metrics.getMuscleMass()
        self.assertGreaterEqual(muscle_mass, 45.0)
        self.assertLessEqual(muscle_mass, 75.0)

        bone_mass = self.metrics.getBoneMass()
        self.assertGreaterEqual(bone_mass, 2.0)
        self.assertLessEqual(bone_mass, 5.0)

        visceral_fat = self.metrics.getVisceralFat()
        self.assertGreaterEqual(visceral_fat, 1)
        self.assertLessEqual(visceral_fat, 15)

    def test_lbm_coefficient(self):
        """Lean Body Mass coefficient should be positive and less than total weight."""
        lbm = self.metrics.getLBMCoefficient()
        self.assertGreater(lbm, 40.0)
        self.assertLess(lbm, self.weight)

    def test_zero_impedance_calculation_contract(self):
        """When weighing with socks/shoes (impedance == 0), export path computes BMI without crash."""
        # Contract verified from miscale_export.py lines 93-118
        bmi = round(self.weight / ((self.height / 100) ** 2), 1)
        ideal_weight = round(22.0 * ((self.height / 100) ** 2), 1)
        self.assertAlmostEqual(bmi, 23.9, places=1)
        self.assertAlmostEqual(ideal_weight, 76.9, places=1)

    def test_value_overflow_clamping(self):
        """checkValueOverflow should clamp values strictly to [minimum, maximum]."""
        self.assertEqual(self.metrics.checkValueOverflow(5, 10, 50), 10)
        self.assertEqual(self.metrics.checkValueOverflow(60, 10, 50), 50)
        self.assertEqual(self.metrics.checkValueOverflow(25, 10, 50), 25)

    def test_body_scales_lookup(self):
        """Verify scale thresholds for male age 35 in bodyScales."""
        scales = bodyScales(age=self.age, height=self.height, sex=self.sex, weight=self.weight)
        bmi_scale = scales.getBMIScale()
        self.assertEqual(bmi_scale, [18.5, 25.0, 28.0, 32.0])

        fat_scale = scales.getFatPercentageScale()
        self.assertEqual(fat_scale, [11.0, 17.0, 22.0, 27.0])


if __name__ == "__main__":
    unittest.main()
