from unittest.mock import patch

import pandas as pd

import stocks


def test_get_volume_summary_skips_nan_entries():
    volume_df = pd.DataFrame({"JPM": [100, 200], "GS": [50, float("nan")]})
    with patch("stocks.get_volume_data", return_value=volume_df):
        result = stocks.get_volume_summary(["JPM", "GS"])
    assert result == {"JPM": 200}


def test_get_volume_summary_empty_when_no_data():
    with patch("stocks.get_volume_data", return_value=None):
        result = stocks.get_volume_summary(["JPM"])
    assert result == {}
