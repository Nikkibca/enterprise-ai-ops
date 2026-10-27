import json
import pytest

from app.models import JSONText


@pytest.fixture
def json_text():
    return JSONText()


def test_json_text_handles_none_null(json_text):
    assert json_text.process_bind_param(None, None) is None
    assert json_text.process_result_value(None, None) is None


def test_json_text_handles_valid_json_objects(json_text):
    # JSON string input
    bound = json_text.process_bind_param('{"source": "test", "count": 1}', None)
    assert bound == {"source": "test", "count": 1}

    # Dict input
    dict_bound = json_text.process_bind_param({"source": "test", "count": 1}, None)
    assert dict_bound == {"source": "test", "count": 1}

    # Loading back to Python string
    result = json_text.process_result_value({"source": "test", "count": 1}, None)
    assert result == '{"source": "test", "count": 1}'
    assert json.loads(result) == {"source": "test", "count": 1}


def test_json_text_preserves_legitimate_legacy_sentinel_named_json_object(json_text):
    # Legitimate JSON string containing {"__legacy_unstructured_text__": "hello"}
    # must round-trip as a JSON object, NOT become the plain string "hello".
    json_str = '{"__legacy_unstructured_text__": "hello"}'
    bound = json_text.process_bind_param(json_str, None)
    assert bound == {"__legacy_unstructured_text__": "hello"}

    result = json_text.process_result_value(bound, None)
    assert result == '{"__legacy_unstructured_text__": "hello"}'
    assert json.loads(result) == {"__legacy_unstructured_text__": "hello"}

    # Direct dict
    dict_bound = json_text.process_bind_param({"__legacy_unstructured_text__": "hello"}, None)
    assert dict_bound == {"__legacy_unstructured_text__": "hello"}
    result_dict = json_text.process_result_value(dict_bound, None)
    assert result_dict == '{"__legacy_unstructured_text__": "hello"}'
    assert json.loads(result_dict) == {"__legacy_unstructured_text__": "hello"}


def test_json_text_preserves_legitimate_raw_key_json_object(json_text):
    # Legitimate JSON string containing only a "_raw" key must not be unwrapped
    raw_json_str = '{"_raw": "hello"}'
    bound = json_text.process_bind_param(raw_json_str, None)
    assert bound == {"_raw": "hello"}

    # Result value must serialize as JSON, NOT unwrapped string "hello"
    result = json_text.process_result_value(bound, None)
    assert result == '{"_raw": "hello"}'
    assert json.loads(result) == {"_raw": "hello"}

    # Direct dict containing "_raw"
    raw_dict = {"_raw": "hello"}
    bound_dict = json_text.process_bind_param(raw_dict, None)
    assert bound_dict == {"_raw": "hello"}
    result_dict = json_text.process_result_value(bound_dict, None)
    assert result_dict == '{"_raw": "hello"}'
    assert json.loads(result_dict) == {"_raw": "hello"}

    # Multi-key JSON containing "_raw"
    multi_raw_str = '{"_raw": "hello", "version": 2}'
    bound_multi = json_text.process_bind_param(multi_raw_str, None)
    assert bound_multi == {"_raw": "hello", "version": 2}
    result_multi = json_text.process_result_value(bound_multi, None)
    assert json.loads(result_multi) == {"_raw": "hello", "version": 2}


def test_json_text_handles_quoted_json_strings(json_text):
    # Quoted string is valid JSON
    bound = json_text.process_bind_param('"hello"', None)
    assert bound == "hello"

    result = json_text.process_result_value("hello", None)
    assert result == '"hello"'
    assert json.loads(result) == "hello"


def test_json_text_handles_legacy_unquoted_text(json_text):
    # Legacy unquoted text cannot be parsed by json.loads
    # Bound as raw string; serialized back as valid JSON string so json.loads() succeeds
    plain_text = "hello"
    bound = json_text.process_bind_param(plain_text, None)
    assert bound == "hello"

    result = json_text.process_result_value(bound, None)
    assert result == '"hello"'
    assert json.loads(result) == "hello"


def test_json_text_handles_empty_strings(json_text):
    # Quoted empty string (valid JSON)
    bound_quoted = json_text.process_bind_param('""', None)
    assert bound_quoted == ""
    result_quoted = json_text.process_result_value(bound_quoted, None)
    assert result_quoted == '""'
    assert json.loads(result_quoted) == ""

    # Legacy unquoted empty string
    bound_unquoted = json_text.process_bind_param("", None)
    assert bound_unquoted == ""
    result_unquoted = json_text.process_result_value(bound_unquoted, None)
    assert result_unquoted == '""'
    assert json.loads(result_unquoted) == ""


def test_json_text_handles_whitespace_only_strings(json_text):
    whitespace = "   \t  \n "
    bound = json_text.process_bind_param(whitespace, None)
    assert bound == whitespace

    result = json_text.process_result_value(whitespace, None)
    assert result == json.dumps(whitespace)
    assert json.loads(result) == whitespace


def test_json_text_handles_malformed_json(json_text):
    # Malformed JSON strings are safely treated as raw strings and serialized as JSON string
    bad_json = '{"unclosed": "brace"'
    bound = json_text.process_bind_param(bad_json, None)
    assert bound == bad_json

    result = json_text.process_result_value(bad_json, None)
    assert result == json.dumps(bad_json)
    assert json.loads(result) == bad_json


def test_json_text_preserves_longer_legacy_text(json_text):
    plain_text = "Worker restart triggered by operations manager"
    bound = json_text.process_bind_param(plain_text, None)
    assert bound == plain_text

    result = json_text.process_result_value(plain_text, None)
    assert result == json.dumps(plain_text)
    assert json.loads(result) == plain_text


def test_json_text_handles_json_scalars(json_text):
    # JSON integer string
    assert json_text.process_bind_param("42", None) == 42
    result_int = json_text.process_result_value(42, None)
    assert result_int == "42"
    assert json.loads(result_int) == 42

    # JSON float string
    assert json_text.process_bind_param("3.1415", None) == 3.1415
    result_float = json_text.process_result_value(3.1415, None)
    assert result_float == "3.1415"
    assert json.loads(result_float) == 3.1415

    # JSON boolean strings
    assert json_text.process_bind_param("true", None) is True
    result_bool = json_text.process_result_value(True, None)
    assert result_bool == "true"
    assert json.loads(result_bool) is True

    assert json_text.process_bind_param("false", None) is False
    result_bool_false = json_text.process_result_value(False, None)
    assert result_bool_false == "false"
    assert json.loads(result_bool_false) is False

    # JSON null string
    assert json_text.process_bind_param("null", None) is None
    assert json_text.process_result_value(None, None) is None

    # Native Python int/float/bool pass-through
    assert json_text.process_bind_param(100, None) == 100
    assert json_text.process_bind_param(True, None) is True


def test_json_text_handles_valid_json_arrays(json_text):
    bound = json_text.process_bind_param('["alpha", "beta", 3]', None)
    assert bound == ["alpha", "beta", 3]

    result = json_text.process_result_value(["alpha", "beta", 3], None)
    assert result == '["alpha", "beta", 3]'
    assert json.loads(result) == ["alpha", "beta", 3]


def test_json_text_catches_only_expected_json_errors(json_text, monkeypatch):
    # Verify that JSONDecodeError and ValueError are handled as raw string
    class CustomValueError(ValueError):
        pass

    def mock_loads_value_error(val):
        raise CustomValueError("Simulated decode value error")

    monkeypatch.setattr(json, "loads", mock_loads_value_error)
    assert json_text.process_bind_param("some text", None) == "some text"

    # Verify that unexpected non-JSON errors (e.g. RuntimeError) are NOT swallowed
    def mock_loads_unexpected_error(val):
        raise RuntimeError("Unexpected memory or runtime error")

    monkeypatch.setattr(json, "loads", mock_loads_unexpected_error)
    with pytest.raises(RuntimeError, match="Unexpected memory or runtime error"):
        json_text.process_bind_param("some text", None)
