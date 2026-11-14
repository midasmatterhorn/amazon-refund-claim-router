"""Label-match helper: the routed set must equal the investigator's pipe-separated set."""
from run_claim import label_match


def test_label_match_true_for_same_set_in_any_order():
    assert label_match({"stock", "billing", "shipping"}, "billing|shipping|stock") is True


def test_label_match_false_when_a_specialist_is_missing():
    assert label_match({"billing"}, "billing|shipping") is False


def test_label_match_false_when_router_invents_a_specialist():
    assert label_match({"billing", "stock"}, "billing") is False
