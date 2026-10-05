"""Validate a complete supplied namespace before private endpoint replay."""
import re

PROFILE = 'ordinary_rename_v1'
CONTEXT = {
    'object_kind': ('regular_files', 'other', 'unknown'),
    'namespace': ('same_mount', 'cross_mount', 'unknown'),
    'resolution': ('complete', 'unknown'),
    'execution': ('assumed_success', 'unknown'),
    'reference_coverage': ('complete', 'unknown'),
}
ROOT_KEYS = ('version', 'profile', 'file_ids', 'name_ids', 'bindings', 'references', 'events', 'context')
ID = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,23}\Z')


class Invalid(ValueError):
    """Internal fixed-code admission rejection; no caller text included."""


def _shape(value, keys):
    if type(value) is not dict:
        raise Invalid('invalid_shape')
    if len(value) != len(keys):
        raise Invalid('invalid_shape')
    # Guard all key identities before set/equality/hash can dispatch caller hooks.
    for key in value:
        if type(key) is not str or len(key) > 32:
            raise Invalid('invalid_shape')
    if set(value) != set(keys):
        raise Invalid('invalid_shape')


def _array(value, low, high):
    if type(value) is not list:
        raise Invalid('invalid_shape')
    if not low <= len(value) <= high:
        raise Invalid('invalid_value')


def _id(value):
    if type(value) is not str:
        raise Invalid('invalid_shape')
    if not 1 <= len(value) <= 24 or ID.fullmatch(value) is None:
        raise Invalid('invalid_value')


def _enum(value, values):
    if type(value) is not str:
        raise Invalid('invalid_shape')
    if len(value) > 32 or value not in values:
        raise Invalid('invalid_value')


def _catalog(value, low, high):
    _array(value, low, high)
    seen = set()
    for identity in value:
        _id(identity)
        if identity in seen:
            raise Invalid('duplicate_id')
        seen.add(identity)
    return seen


def _entries(rows, keys, first_catalog, files):
    _array(rows, 0, 8)
    seen = set()
    for row in rows:
        _shape(row, keys)
        for key in keys:
            _id(row[key])
        identity = row[keys[0]]
        if identity in seen:
            raise Invalid('duplicate_id')
        seen.add(identity)
        if (first_catalog is not None and identity not in first_catalog) or row['file_id'] not in files:
            raise Invalid('unknown_id')


def _validate(doc):
    _shape(doc, ROOT_KEYS)
    if type(doc['version']) is not int:
        raise Invalid('invalid_shape')
    if doc['version'] != 1:
        raise Invalid('invalid_value')
    _enum(doc['profile'], (PROFILE,))
    files = _catalog(doc['file_ids'], 1, 4)
    names = _catalog(doc['name_ids'], 1, 8)
    _entries(doc['bindings'], ('name_id', 'file_id'), names, files)
    _entries(doc['references'], ('reference_id', 'file_id'), None, files)
    _array(doc['events'], 0, 24)
    seen = set()
    for row in doc['events']:
        _shape(row, ('event_id', 'op', 'source_name', 'destination_name'))
        _id(row['event_id'])
        _enum(row['op'], ('rename', 'exchange', 'noreplace', 'whiteout'))
        _id(row['source_name'])
        _id(row['destination_name'])
        if row['event_id'] in seen:
            raise Invalid('duplicate_id')
        seen.add(row['event_id'])
        if row['source_name'] not in names or row['destination_name'] not in names:
            raise Invalid('unknown_id')
    _shape(doc['context'], tuple(CONTEXT))
    for key, values in CONTEXT.items():
        _enum(doc['context'][key], values)
    held = {row['file_id'] for row in doc['bindings'] + doc['references']}
    if files - held:
        raise Invalid('unheld_file')


def _unsupported(doc):
    result = []
    for key, values in CONTEXT.items():
        if doc['context'][key] != values[0]:
            result.append(dict(location='context.' + key, feature=doc['context'][key]))
    for i, row in enumerate(doc['events']):
        if row['op'] != 'rename':
            result.append(dict(location=f'events.{i}.op', feature=row['op']))
    return result


def _empty(status, reason, unsupported=None, trace_error=None):
    return dict(status=status, profile=PROFILE, reason=reason, unsupported=unsupported,
                trace_error=trace_error, initial=None, steps=[], final=None,
                verification=dict.fromkeys(('real_effects', 'permissions', 'durability', 'concurrency'), 'unverified'))


def _snapshot(files, bindings, references):
    rows = []
    for file in sorted(files):
        names = sum(value == file for value in bindings.values())
        refs = sum(value == file for value in references.values())
        rows.append(dict(file_id=file, name_count=names, reference_count=refs,
                         retention='named' if names else 'reference_only' if refs else 'no_declared_holders'))
    return dict(bindings=[dict(name_id=key, file_id=bindings[key]) for key in sorted(bindings)],
                references=[dict(reference_id=key, file_id=references[key]) for key in sorted(references)],
                files=rows)


def _transition(bindings, references, source, destination):
    file = bindings[source]
    victim = bindings.get(destination)
    if source == destination:
        return 'same_name_noop', file, None
    if victim == file:
        return 'same_file_noop', file, None
    bindings.pop(source)
    bindings[destination] = file
    return 'moved' if victim is None else 'replaced', file, victim


def evaluate(document):
    """Return a fresh conditional report; reject subclasses and preserve caller data.

    Full admission precedes unsupported classification. Replay uses private maps;
    a late absent source suppresses all snapshots, not just that step. No real
    syscalls, target paths, live access decisions or persistence are inspected.
    """
    try:
        _validate(document)
    except Invalid as error:
        return _empty('invalid_input', str(error))
    features = _unsupported(document)
    if features:
        return _empty('unsupported', 'unsupported_context_or_operation', unsupported=features)
    bindings = {row['name_id']: row['file_id'] for row in document['bindings']}
    references = {row['reference_id']: row['file_id'] for row in document['references']}
    files = document['file_ids']
    report = _empty('modeled', 'complete')
    report['initial'] = _snapshot(files, bindings, references)
    for i, event in enumerate(document['events']):
        source, destination = event['source_name'], event['destination_name']
        if source not in bindings:
            return _empty('invalid_trace', 'missing_source', trace_error=dict(
                event_index=i, event_id=event['event_id'], violation='source_unbound'))
        effect, file, victim = _transition(bindings, references, source, destination)
        report['steps'].append(dict(event_index=i, event_id=event['event_id'], source_name=source,
            destination_name=destination, effect=effect, file_id=file, displaced_file_id=victim,
            after=_snapshot(files, bindings, references)))
    report['final'] = _snapshot(files, bindings, references)
    return report
