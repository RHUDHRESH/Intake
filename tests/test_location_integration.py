"""Mock coverage for location-aware logic that would use external APIs."""

from typing import Dict


def validate_location(location_string: str) -> Dict[str, object]:
    """Simple mock location validation in place of Google Maps."""

    known_cities = {
        "chennai": (13.0827, 80.2707, "India"),
        "mumbai": (19.0760, 72.8777, "India"),
        "bangalore": (12.9716, 77.5946, "India"),
        "new york": (40.7128, -74.0060, "USA"),
        "london": (51.5072, -0.1276, "UK"),
    }
    lower_location = location_string.lower()

    for city, (lat, lng, country) in known_cities.items():
        if city in lower_location:
            return {
                "valid": True,
                "formatted_address": location_string,
                "lat": lat,
                "lng": lng,
                "country": country,
            }
    return {"valid": False, "error": "Location not found"}


def get_location_insights(location_data: Dict[str, object]) -> Dict[str, object]:
    """Return basic marketing insights based on country metadata."""

    if location_data.get("country") == "India":
        return {
            "market_type": "Emerging market",
            "suggested_platforms": ["WhatsApp Business", "Instagram", "LinkedIn"],
            "local_considerations": [
                "Regional language content",
                "Mobile-first approach",
                "Price sensitivity",
            ],
        }
    return {"market_type": "Developed market"}


def test_location_integration() -> None:
    """Test the mocked location validation and insight helpers."""

    print("[LOCATION] Starting integration test")

    test_locations = [
        "Chennai, India",
        "Mumbai",
        "Bangalore, Karnataka, India",
        "New York City",
        "Invalid Location XYZ",
    ]

    for location in test_locations:
        result = validate_location(location)
        print(f"location lookup: {location} -> {result}")

        if any(city in location.lower() for city in ["chennai", "mumbai", "bangalore"]):
            assert result["valid"] is True
            assert "India" in result.get("formatted_address", "") or result.get("country") == "India"

    chennai_location = validate_location("Chennai, India")
    insights = get_location_insights(chennai_location)
    print(f"insights: {insights}")

    assert insights["market_type"] == "Emerging market"
    assert "WhatsApp Business" in insights["suggested_platforms"]

    print("[LOCATION] Integration test passed")


if __name__ == "__main__":
    test_location_integration()
