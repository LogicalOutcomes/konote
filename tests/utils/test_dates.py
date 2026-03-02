import pytest
from datetime import date
from apps.utils.dates import parse_date_safely

def test_parse_date_safely_valid_iso():
    """Test parsing standard ISO 8601 date strings."""
    assert parse_date_safely("2023-01-01") == date(2023, 1, 1)
    assert parse_date_safely("1999-12-31") == date(1999, 12, 31)

def test_parse_date_safely_valid_us_format():
    """Test parsing US date format MM/DD/YYYY."""
    assert parse_date_safely("01/02/2023") == date(2023, 1, 2)
    assert parse_date_safely("12/31/1999") == date(1999, 12, 31)

def test_parse_date_safely_empty_and_none():
    """Test handling of empty strings and None."""
    assert parse_date_safely(None) is None
    assert parse_date_safely("") is None

def test_parse_date_safely_invalid_formats():
    """Test handling of completely invalid date formats."""
    assert parse_date_safely("not-a-date") is None
    assert parse_date_safely("2023/13/45") is None
    assert parse_date_safely("abcd-ef-gh") is None

def test_parse_date_safely_out_of_bounds():
    """Test handling of dates with out-of-bounds components."""
    assert parse_date_safely("2023-13-45") is None
    assert parse_date_safely("2023-02-30") is None
    assert parse_date_safely("13/45/2023") is None
