def un_none(obj, default):
    """Replace None with empty dict"""
    return obj if obj is not None else default
