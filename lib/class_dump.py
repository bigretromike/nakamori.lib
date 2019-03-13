import json
from collections import defaultdict

# Surprisingly, there is no better way to do this...


def dump_to_text(*args):
    text = ''
    if args is None:
        return text
    for arg in args:
        text = text.strip()
        if arg is None:
            text += ' ' + str(arg)
        elif isinstance(arg, (str, unicode, bytes)):
            text += ' ' + arg
        else:
            text += ' ' + dump(arg)
    return text.strip()


def dump(obj):
    if isinstance(obj, (str, unicode, int, bool, float)):
        return obj
    if isinstance(obj, (list, set, tuple)):
        return json.dumps(dump_iterable(obj))
    if isinstance(obj, (dict, defaultdict)):
        return json.dumps(dump_dictionary(obj))
    return json.dumps(dump_class(obj))


def dump_class(obj):
    result = {}
    if obj is None:
        return result

    members = [attr for attr in dir(obj) if not callable(getattr(obj, attr)) and not attr.startswith("__")]
    for key in members:
        value = getattr(obj, key)
        if isinstance(value, (str, unicode, int, bool, float)):
            result[key] = value
        elif isinstance(value, (list, set, tuple)):
            result[key] = dump_iterable(value)
        elif isinstance(value, (dict, defaultdict)):
            result[key] = dump_dictionary(value)
        else:
            result[key] = dump_class(value)
    return result


def dump_iterable(obj):
    result = []
    for item in obj:
        if isinstance(item, (str, unicode, int, bool, float)):
            result.append(item)
        elif isinstance(item, (list, set, tuple)):
            result.append(dump_iterable(item))
        elif isinstance(item, (dict, defaultdict)):
            result.append(dump_dictionary(item))
        else:
            result.append(dump_class(item))
    return result


def dump_dictionary(obj):
    result = {}
    for key, value in obj.items():
        if isinstance(value, (str, unicode, int, bool, float)):
            result[key] = value
        elif isinstance(value, (list, set, tuple)):
            result[key] = dump_iterable(value)
        elif isinstance(value, (dict, defaultdict)):
            result[key] = dump_dictionary(value)
        else:
            result[key] = dump_class(value)
    return result
