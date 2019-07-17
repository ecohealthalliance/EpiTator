from __future__ import absolute_import
import six
import logging


def nested_items(d):
    """
    Iterates over all the items in nested dictionaries returning path arrays
    with values.
    """
    for k, v in d.items():
        if isinstance(v, dict):
            for kpath, v2 in nested_items(v):
                yield [k] + kpath, v2
        else:
            yield [k], v


def get_path(d, path, default=None):
    if not isinstance(d, dict):
        # print "Could not get %s in non-dict %s" % (path, d)
        return None
    if isinstance(path, six.string_types):
        path = path.split('.')
    if len(path) == 1:
        return d.get(path[0], default)
    else:
        return get_path(d.get(path[0], {}), path[1:])


def assertHasProps(d, props):
    """
    All the properties and values in props must also exist in d for this
    assertion to be True.
    """
    missing_props = []
    for kpath, v in nested_items(props):
        dv = get_path(d, kpath)
        if dv != v:
            missing_props.append(kpath)
    if len(missing_props) > 0:
        raise AssertionError(
            "Missing properties:\n{}".format('\n'.join(
                "%s: %s != %s" % ('.'.join(p), get_path(d, p), get_path(props, p))
                for p in missing_props)))


def assertMetadataContents(test, expected):
    """
    Checks to see whether the list of attributes contains all the expected
    attributes provided.
    """
    missing_metadata = []
    surplus_metadata = []
    incorrect_metadata = []
    for keypath, expected_val in nested_items(expected):
        test_val = get_path(test, keypath)
        if test_val is None:
            missing_metadata.append(keypath)
        elif hasattr(test_val, "__iter__"):
            # Look for expected items absent from test
            missing_idx = [attr not in test_val for attr in expected_val]
            if any(missing_idx):
                missing_attrs = [attr for attr, m in zip(expected_val, missing_idx) if m]
                missing_metadata.append((keypath, missing_attrs))
            # Look for test items not present in expected
            surplus_idx = [attr not in expected_val for attr in test_val]
            if any(surplus_idx):
                surplus_attrs = [attr for attr, s in zip(test_val, surplus_idx) if s]
                surplus_metadata.append((keypath, surplus_attrs))
        else:
            if test_val != expected_val:
                incorrect_metadata.append((keypath, test_val))
    if len(missing_metadata) + len(incorrect_metadata) > 0:
        raise AssertionError("""
Test Metadata: {}
Expected Metadata {}
Errors:
    Missing: {}
    Surplus: {}
    Incorrect: {}
""".format(test, expected, missing_metadata, surplus_metadata, incorrect_metadata))


def with_log_level(logger, level):
    old_level = logger.level or logging.ERROR

    def decorator(fun):
        def logged_fun(*args, **kwargs):
            logger.setLevel(level)
            try:
                result = fun(*args, **kwargs)
                logger.setLevel(old_level)
                return result
            except:  # noqa: E722
                logger.setLevel(old_level)
                raise
        return logged_fun
    return decorator
