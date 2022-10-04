DEFAULT_YEAR = 2022


class MunicipalitiesError(Exception):
    """General exception for municipalities lib"""

    pass


class MunicipalitiesNotFoundError(MunicipalitiesError):
    """Exception for no municipality match"""

    pass


def handle_get_municipalities(tbl, params):
    """
    Returns a slice of the municipalities table for the appropriate year

    This function will use the pagination params (or default values) to
    return the appropropriate slice of the municiaplities table and the
    year param (or default value) to select the year.

    This table will include these columns: "year", "GEOID", "county", "municipality"

    If the results are emtpy, this function will throw a MunicipalitiesNotFound exception.

    Args:
        municipalities: municipalies table
        params: dict of params, possibly including pagination params and year param

    Returns:
        subset of municipalitities table for the appropriate year
        dict of pagination-related params and year param
    """
    year = params.get("year", DEFAULT_YEAR)
    page_size = params.get("page_size", 100)
    page_number = params.get("page_number", 1)
    aux = {"year": year, "page_size": page_size, "page_number": page_number}

    filtered = tbl[(tbl["first_year"] <= year) & (tbl["final_year"] >= year)]
    if filtered.empty:
        status_msg = f"Year {year} not found"
        raise MunicipalitiesNotFoundError(status_msg)
    page_count = (len(filtered) - 1) // page_size + 1
    if page_number < 1 or page_number > page_count:
        status_msg = f"Page number {page_number} not found"
        raise MunicipalitiesNotFoundError(status_msg)

    offset = (page_number - 1) * page_size
    page = filtered.iloc[offset : offset + page_size].copy()
    page["year"] = year
    result_set = page[["year", "GEOID", "county", "municipality"]]
    aux["record_count"] = len(filtered)
    return result_set, aux


def handle_get_municipality(tbl, params):
    """
    Returns the specified municipality for the specified year.

    The GEOID and year should be in the params dict.

    If no municipality is found, MunicipalitiesNotFoundError will be thrown.

    The single row will include these columns: "year", "GEOID", "county", "municipality"

    Args:
        municipalities: municipalities table
        params: dict of params, including "GEOID" and "year"

    Returns:
        Single row municipalities table
        dict containing GEOID  and year params
    """
    year = params.get("year", DEFAULT_YEAR)
    GEOID = params["GEOID"]
    aux = {"year": year, "GEOID": GEOID}

    filtered = tbl[
        (tbl["GEOID"] == GEOID)
        & (tbl["first_year"] <= year)
        & (tbl["final_year"] >= year)
    ].copy()
    if filtered.empty:
        status_msg = f"Year {year} not found for GEOID {GEOID}"
        raise MunicipalitiesNotFoundError(status_msg)

    filtered["year"] = year
    result_set = filtered[["year", "GEOID", "county", "municipality"]]
    return result_set, aux


def handle_get_xrefs(tbl, params):
    """
    Returns a slice of the XREFs table generated for a pair of years

    This function will use the pagination params (or default values) to
    return the appropropriate slice of the XREF table for year and year_ref.
    The year and year_ref params must be included in the params dict.

    This table will include these columns: "year", "GEOID", "year_ref", "GEOID_ref"

    If the results are emtpy, this function will throw a MunicipalitiesNotFound exception.

    Args:
        municipalities: municipalities table
        params: dict of params, possibly including pagination params and year params

    Returns:
        subset of XREF table for the appropriate years
        dict of pagination-related params and year params
    """
    page_size = params.get("page_size", 100)
    page_number = params.get("page_number", 1)
    year = params["year"]
    year_ref = params["year_ref"]
    aux = {
        "year": year,
        "year_ref": year_ref,
        "page_size": page_size,
        "page_number": page_number,
    }

    cur_tbl = tbl[(tbl["first_year"] <= year) & (tbl["final_year"] >= year)]
    if cur_tbl.empty:
        status_msg = f"Year {year} not found"
        raise MunicipalitiesNotFoundError(status_msg)

    page_count = (len(cur_tbl) - 1) // page_size + 1
    if page_number < 1 or page_number > page_count:
        status_msg = f"Page number {page_number} not found"
        raise MunicipalitiesNotFoundError(status_msg)
    offset = (page_number - 1) * page_size
    page = cur_tbl.iloc[offset : offset + page_size]

    ref_tbl = tbl[(tbl["first_year"] <= year_ref) & (tbl["final_year"] >= year_ref)]
    if ref_tbl.empty:
        status_msg = f"Reference year {year_ref} not found"
        raise MunicipalitiesNotFoundError(status_msg)

    result_set = page.set_index("GEOID_Y2K").join(
        ref_tbl.set_index("GEOID_Y2K"),
        rsuffix="_ref",
    )[["GEOID_ref", "GEOID"]]
    result_set["year"] = year
    result_set["year_ref"] = year_ref
    result_set = result_set[["year_ref", "year", "GEOID_ref", "GEOID"]]
    aux["record_count"] = len(cur_tbl)
    return result_set, aux
