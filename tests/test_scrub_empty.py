from spit_fhir.fhir_consumers.utils import scrub_empty


def test_drops_empty_string_values():
    assert scrub_empty({"a": "", "b": "keep"}) == {"b": "keep"}


def test_drops_nested_dict_that_becomes_empty():
    assert scrub_empty({"a": {"b": ""}}) is None


def test_filters_empty_strings_out_of_a_list_without_dropping_the_list():
    assert scrub_empty({"a": [1, 2, ""]}) == {"a": [1, 2]}


def test_drops_a_list_key_entirely_when_every_item_is_empty():
    assert scrub_empty({"a": ["", ""]}) is None


def test_leaves_populated_data_untouched():
    payload = {"resourceType": "Patient", "id": "abc", "active": True}
    assert scrub_empty(payload) == payload
