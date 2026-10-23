from logscope.normalise import normalise_message


def test_normalise_message_replaces_uuid_hex_and_numbers() -> None:
    message = (
        "Request 123 failed for 550e8400-e29b-41d4-a716-446655440000 "
        "at 0x1f3a after 45.6 ms"
    )

    assert normalise_message(message) == "Request <n> failed for <uuid> at <hex> after <n> ms"


def test_normalise_message_applies_replacements_in_order() -> None:
    message = "trace=0xabc123 retries=3"

    assert normalise_message(message) == "trace=<hex> retries=<n>"
