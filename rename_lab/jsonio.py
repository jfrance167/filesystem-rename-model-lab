"""Bounded strict JSON and deterministic report serialization."""
import json
import math

from .core import Invalid, _empty, evaluate

MAX_INPUT_BYTES = 32768
MAX_OUTPUT_BYTES = 262144


def _depth(text):
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '[{':
            depth += 1
            if depth > 6:
                raise Invalid('json_depth')
        elif char in ']}':
            depth -= 1


def _pairs(rows):
    result = {}
    for key, value in rows:
        if key in result:
            raise Invalid('json_duplicate_key')
        result[key] = value
    return result


def _integer(token):
    if len(token.lstrip('-')) > 10:
        raise Invalid('json_integer')
    return int(token)


def _constant(token):
    raise Invalid('json_constant')


def _float(token):
    value = float(token)
    if not math.isfinite(value):
        raise Invalid('json_constant')
    return value


def analyze_json(raw):
    """Return admission report without interpreting any real path or object."""
    if type(raw) is not bytes or len(raw) > MAX_INPUT_BYTES:
        return _empty('invalid_input', 'input_size')
    try:
        text = raw.decode('utf-8')
        if text.startswith('\ufeff'):
            raise UnicodeError('BOM')
    except UnicodeError:
        return _empty('invalid_input', 'invalid_utf8')
    try:
        _depth(text)
        doc = json.loads(text, object_pairs_hook=_pairs, parse_int=_integer,
                         parse_float=_float, parse_constant=_constant)
    except Invalid as error:
        return _empty('invalid_input', str(error))
    except (ValueError, RecursionError):
        return _empty('invalid_input', 'invalid_json')
    return evaluate(doc)


def serialize_report(report):
    """Serialize trusted model reports; logical cap is not physical atomic IO."""
    payload = (json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    if len(payload) > MAX_OUTPUT_BYTES:
        raise ValueError('report limit')
    return payload
