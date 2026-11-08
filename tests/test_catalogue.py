import json
import pytest
from storydna.catalogue import parse_catalogue, clean_pitch, InputError


def row(i, syn="Something happens. Then more happens."):
    return {"story_id": "S%d" % i, "title": "T%d" % i, "synopsis": syn}


def test_valid_json_and_csv():
    assert len(parse_catalogue(json.dumps([row(1), row(2)]))) == 2
    csv_text = "story_id,title,synopsis\nA,One,Hello there. Bye now.\n"
    assert parse_catalogue(csv_text, "x.csv")[0].story_id == "A"


@pytest.mark.parametrize("raw,fname,frag", [
    ("", "c.json", "parse the JSON"),
    ("[]", "c.json", "empty"),
    ("{not json", "c.json", "parse the JSON"),
    (json.dumps([{"story_id": "A", "title": "x"}]), "c.json", "missing required"),
    (json.dumps([row(1), row(1)]), "c.json", "Duplicate story_id"),
    ("a,b\n1,2\n", "c.csv", "header must contain"),
    (json.dumps({"x": 1}), "c.json", "list of story"),
])
def test_bad_catalogues_give_readable_errors(raw, fname, frag):
    with pytest.raises(InputError) as e:
        parse_catalogue(raw, fname)
    assert frag in str(e.value)


def test_bad_pitches():
    for bad in ["", "   \n ", None]:
        with pytest.raises(InputError):
            clean_pitch(bad)
    with pytest.raises(InputError):
        clean_pitch("x" * 300_000)
    assert clean_pitch("A normal sentence.\x00") == "A normal sentence."
