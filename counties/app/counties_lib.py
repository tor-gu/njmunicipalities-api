class CountiesError(Exception):
    """General exception for counties lib"""

    pass


class CountiesNotFoundError(CountiesError):
    """Exception for no county match"""

    pass


def handle_get_counties(counties, params):
    """
    Returns a subset of the counties table, subject to pagination

    This function will use the pagination params (or default values) to
    return the appropropriate slice of the counties table. It will
    return only two columns:  GEOID and county.

    If the results are emtpy, this function will throw a CountiesNotFound exception.

    Args:
        counties: counties table
        params: dict of params, possibly including pagination params

    Returns:
        subset of counties table
        dict of pagination-related params suitable for passing to torguapi_result
    """

    page_size = params.get("page_size", 100)
    page_number = params.get("page_number", 1)
    page_count = (len(counties) - 1) // page_size + 1

    aux = {
        "page_size": page_size,
        "page_number": page_number,
        "record_count": len(counties),
    }

    if page_number < 1 or page_number > page_count:
        status_msg = f"Page number {page_number} not found"
        raise CountiesNotFoundError(status_msg)

    offset = (page_number - 1) * page_size
    page = counties[offset : offset + page_size].copy()
    result_set = page[["GEOID", "county"]]
    return result_set, aux


def handle_get_county(counties, params):
    """
    Returns the specified county

    The GEOID should be in the params dict.

    If no county is found, CountiesNotFoundError will be thrown.

    The single row will be restricted to "GEOID' and "county"

    Args:
        counties: counties table
        params: dict of params, including "GEOID"

    Returns:
        Single row of counties table,
        dict containing GEOID param
    """
    GEOID = params["GEOID"]
    results = counties[counties["GEOID"] == GEOID][["GEOID", "county"]]
    if results.empty:
        raise CountiesNotFoundError(f"County GEOID {GEOID} not found")
    return results, {"GEOID": GEOID}
