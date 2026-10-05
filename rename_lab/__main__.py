"""Checked stdin/JSON/help delivery; adapted from owned lifecycle CLI pattern."""
import sys

from .jsonio import MAX_INPUT_BYTES, analyze_json, serialize_report

HELP = 'usage: rename_lab [--help]\n\nBounded synthetic ordinary rename; real effects unverified.\nRead one UTF8 JSON document from stdin.\n'


def _text(stream, text):
    if stream is None:
        raise OSError('absent output')
    binary = getattr(stream, 'buffer', None)
    payload = text.encode('utf-8') if binary is not None else text
    destination = binary if binary is not None else stream
    count = destination.write(payload)
    if type(count) is not int or count != len(payload):
        raise OSError('invalid text count')
    destination.flush()


def _io_failure():
    diagnostic = sys.stderr
    # Both dirty sinks must be detached to preserve exit3 at CPython shutdown.
    sys.stdout = sys.stderr = None
    try:
        _text(diagnostic, '{"error":"input_or_output_failure"}\n')
    except (OSError, ValueError, AttributeError):
        pass
    return 3


def main():
    try:
        args = sys.argv[1:]
        if args in (['--help'], ['-h']):
            _text(sys.stdout, HELP)
            return 0
        if args:
            _text(sys.stderr, '{"error":"invalid_arguments"}\n')
            return 2
        if sys.stdin is None:
            raise OSError('absent input')
        report = analyze_json(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        payload = serialize_report(report)
        if sys.stdout is None:
            raise OSError('absent output')
        count = sys.stdout.buffer.write(payload)
        if type(count) is not int or count != len(payload):
            raise OSError('invalid binary count')
        sys.stdout.buffer.flush()
    except (OSError, ValueError, AttributeError):
        return _io_failure()
    return 0 if report['status'] in ('modeled', 'unsupported') else 2


if __name__ == '__main__':
    raise SystemExit(main())
