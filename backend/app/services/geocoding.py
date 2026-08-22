from dataclasses import dataclass
from decimal import Decimal

import httpx

from app.config import get_settings

GEOAPIFY_SEARCH_URL = "https://api.geoapify.com/v1/geocode/search"


@dataclass(frozen=True)
class GeocodedAddress:
    formatted_address: str
    postal_code: str
    latitude: Decimal
    longitude: Decimal


def geocode_address(address: str) -> GeocodedAddress:
    settings = get_settings()
    if not settings.geoapify_api_key:
        raise GeocodingConfigurationError("Geoapify API key is not configured")

    params = {
        "text": address,
        "apiKey": settings.geoapify_api_key,
        "limit": 1,
        "format": "json",
    }
    if settings.geocoding_country_code:
        params["filter"] = f"countrycode:{settings.geocoding_country_code}"

    try:
        response = httpx.get(GEOAPIFY_SEARCH_URL, params=params, timeout=7.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise GeocodingProviderError("Geocoding provider unavailable") from exc

    results = response.json().get("results", [])
    if not results:
        raise GeocodingNoResultError("No matching address found")

    result = results[0]
    postal_code = result.get("postcode")
    if not postal_code:
        raise GeocodingMissingPostcodeError("Address has no postcode")

    return GeocodedAddress(
        formatted_address=result.get("formatted") or address,
        postal_code=str(postal_code),
        latitude=Decimal(str(result["lat"])),
        longitude=Decimal(str(result["lon"])),
    )


class GeocodingConfigurationError(Exception):
    pass


class GeocodingNoResultError(Exception):
    pass


class GeocodingMissingPostcodeError(Exception):
    pass


class GeocodingProviderError(Exception):
    pass
