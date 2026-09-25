import unittest
from datetime import date
from unittest import mock

import khal
from khal import calculate_age, parse_birthday


def with_today(year, month, day):
    """Patch khal.date.today() to a fixed date for deterministic tests."""
    fake_date = mock.Mock(wraps=date)
    fake_date.today.return_value = date(year, month, day)
    return mock.patch.object(khal, "date", fake_date)


class TestCalculateAge(unittest.TestCase):
    def test_birthday_already_passed_this_year(self):
        with with_today(2026, 9, 25):
            self.assertEqual(calculate_age(date(2000, 1, 1)), 26)

    def test_birthday_not_yet_this_year(self):
        with with_today(2026, 9, 25):
            self.assertEqual(calculate_age(date(2000, 12, 31)), 25)

    def test_birthday_is_today(self):
        with with_today(2026, 9, 25):
            self.assertEqual(calculate_age(date(2000, 9, 25)), 26)

    def test_birthday_was_yesterday(self):
        with with_today(2026, 9, 25):
            self.assertEqual(calculate_age(date(2000, 9, 24)), 26)

    def test_birthday_is_tomorrow(self):
        with with_today(2026, 9, 25):
            self.assertEqual(calculate_age(date(2000, 9, 26)), 25)

    def test_newborn(self):
        with with_today(2026, 9, 25):
            self.assertEqual(calculate_age(date(2026, 9, 25)), 0)

    def test_leap_day_birthday_before_anniversary(self):
        with with_today(2028, 2, 28):
            self.assertEqual(calculate_age(date(2004, 2, 29)), 23)

    def test_leap_day_birthday_on_anniversary(self):
        with with_today(2028, 2, 29):
            self.assertEqual(calculate_age(date(2004, 2, 29)), 24)

    def test_mar_1_birthday_on_feb_28(self):
        with with_today(2028, 2, 28):
            self.assertEqual(calculate_age(date(2002, 3, 1)), 25)


class TestParseBirthday(unittest.TestCase):
    def test_valid_format(self):
        self.assertEqual(parse_birthday("1990-05-17"), date(1990, 5, 17))

    def test_invalid_format(self):
        with self.assertRaises(ValueError):
            parse_birthday("17/05/1990")

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            parse_birthday("1990-02-30")


if __name__ == "__main__":
    unittest.main()
