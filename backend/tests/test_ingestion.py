import pytest

from app.services.ingestion import chunk_text, normalize_content


def test_chunk_text_preserves_overlap_for_long_content():
    content = "A" * 220
    chunks = chunk_text(content, size=100, overlap=20)

    assert len(chunks) == 3
    assert chunks[0].content[-20:] == chunks[1].content[:20]
    assert [chunk.position for chunk in chunks] == [0, 1, 2]


def test_chunk_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("content", size=100, overlap=100)


def test_json_is_normalized_stably():
    assert normalize_content('{"z": 1, "a": 2}', "json") == '{\n  "a": 2,\n  "z": 1\n}'


def test_csv_is_converted_to_searchable_records():
    output = normalize_content("id,name\n1,Northwind\n", "csv")

    assert output == "id: 1; name: Northwind"

