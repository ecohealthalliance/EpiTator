def nested_items(d):
    """
    Iterates over all the items in nested dictionaries returning path arrays
    with values.
    """
    for k,v in d.items():
        if isinstance(v, dict):
            for kpath, v2 in nested_items(v):
                yield [k] + kpath, v2
        else:
            yield [k], v
def get_path(d, path, default=None):
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
        if not dv or dv != v:
            missing_props.append(kpath)
        
    if len(missing_props) > 0:
        raise AssertionError(
            "Missing properties\n" + str(d) + "\n" + str(props)
        )