from uritemplate import URITemplate
import re
from collections.abc import Iterable
from datetime import date, datetime
from dateutil import parser


class Functions:
    _cache = dict()

    @staticmethod
    def all():
        return {
            'ttl_fmt': turtle_format,  # todo -- remove this in 0.2.0 -- deprecated use, now use `| ttl(...)` instead
            'uritexpand': uritexpand,
            'regexreplace': regexreplace,
            'map': map_build,
            'unparse': xml_unparse,    # todo -- remove this in 0.2.0 -- depracted use, no longer needed since xmlasdict
        }


class Filters:
    @staticmethod
    def all():
        return {
            'ttl': turtle_format,  # new way of using this formatting
        }


def turtle_value(content, quote, type_name, suffix=None):
    if suffix is None:
        suffix = "^^" + type_name
    return quote + str(content) + quote + suffix


def turtle_format_boolean(content, quote, suffix):
    # make rigid bool
    if not isinstance(content, bool):
        asbool = str(content).lower() not in ['', '0', 'no', 'false', 'off']
        content = asbool
    # serialize to string again
    return turtle_value(str(content).lower(), quote, "xsd:boolean")


def turtle_format_integer(content, quote, suffix):
    # make rigid int
    if not isinstance(content, int):
        asint = int(str(content))
        assert str(content) == str(asint), "int format does not round-trip [ %s <> %s ]" % (str(content), str(asint))
        content = asint
    # serialize to string again
    return turtle_value(str(content), quote, "xsd:integer")


def turtle_format_double(content, quote, suffix):
    # make rigid double
    if not isinstance(content, float):
        assert str(float) and float is not None, "double format requires actual input"
        asdbl = float(str(content))
        content = asdbl
    # serialize to string again
    return turtle_value(str(content), quote, "xsd:double")


def turtle_format_date(content, quote, suffix):
    # make rigid date
    if not isinstance(content, date):
        asdt = parser.isoparse(content).date()
    else:
        asdt = content
    return turtle_value(asdt.isoformat(), quote, "xsd:date")


def turtle_format_datetime(content, quote, suffix):
    # make rigid datetime
    if not isinstance(content, datetime):
        asdtm = parser.isoparse(content)
    else:
        asdtm = content
    return turtle_value(asdtm.isoformat(), quote, "xsd:datetime")


def turtle_format_uri(content, quote, suffix):
    # assume content is valid uri for now
    uri = content
    return turtle_value(uri, quote, "xsd:anyURI")


def turtle_format_string(content, quote, suffix):
    # deal with escapes -- note: code is odd to read, but this escapes single \ to double \\
    content = str(content).replace('\\', '\\\\')
    if '\n' in content or quote in content:
        triplus_pattern = r"([']{3}[']*)" if quote == "'" else r'(["]{3}["]*)'
        esc_qt = "\\" + quote                     # escaped quote
        quote = quote * 3                         # make long quote variant
        content = re.sub(
            triplus_pattern,                      # find sequences of 3 or more quotes...
            lambda x: esc_qt * len(x.group()),    # and have each of them escaped
            content                               # so all ''' should become \'\'\' in the content
        )
    assert quote not in content, "ttl format error: still having applied quote format (%s) in text content" % quote
    return turtle_value(content, quote, "xsd:string", suffix)


TTL_FMT_TYPE_FN = {
    "xsd:boolean": turtle_format_boolean,
    "xsd:integer": turtle_format_integer,
    "xsd:double": turtle_format_double,
    "xsd:date": turtle_format_date,
    "xsd:datetime": turtle_format_datetime,
    "xsd:anyURI": turtle_format_uri,
    "xsd:string": turtle_format_string,
}


def turtle_format(content, type_name: str, quote: str = "'"):

    assert quote in "'\"", "ttl format only accepts ' or \" as valid quotes."
    if content is None:
        content = ''

    suffix = None
    if type_name.startswith('@'):
        suffix = type_name
        # assuming string content for further quoting rules
        type_name = "xsd:string"

    type_format_fn = TTL_FMT_TYPE_FN.get(type_name, None)
    assert type_format_fn is not None, "type_name '%s' not supported." % type_name

    return type_format_fn(content, quote, suffix)


def uritexpand(template: str, context):
    return URITemplate(template).expand(context)


def regexreplace(find: str, replace: str, text: str):
    return re.sub(find, replace, text)


class ValueMapper:
    def __init__(self):
        self._map = dict()

    def add(self, key, val):
        if key in self._map:
            assert val == self._map[key], "duplicate key '%s' with distinct values not allowed to build map" % key
        self._map[key] = val

    def apply(self, record: dict, origin_name: str, target_name: str, fallback=None) -> None:
        assert target_name not in record, "applying map refuses to overwrite content already in record"
        key = record[origin_name]
        val = self._map.get(key, fallback)
        record[target_name] = val


def map_build(it: Iterable, key_name: str, val_name: str = None, cached_as: str = None) -> ValueMapper:
    assert key_name, "cannot build map without valid key-name"
    # note: id val_name is None, we just map to the whole record
    if cached_as is not None and cached_as in Functions._cache:
        return Functions._cache[cached_as]
    # else - make map
    vmap = ValueMapper()
    # - populate it
    for item in it:
        target = item[val_name] if val_name is not None else item
        vmap.add(item[key_name], target)
    # add it to the cache
    if cached_as is not None:
        Functions._cache[cached_as] = vmap
    return vmap


def xml_unparse(wrapper):
    return str(wrapper)
