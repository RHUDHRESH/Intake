"""Manual runner for the adaptive questionnaire test suite."""

import sys

from tests.test_business_owner_flow import test_business_owner_complete_flow
from tests.test_framework_selection import test_framework_selection_logic
from tests.test_location_integration import test_location_integration
from tests.test_personal_brand_flow import test_personal_brand_flow
from tests.test_startup_founder_flow import test_startup_founder_flow


def run_all_tests() -> bool:
    """Run the full questionnaire system test battery."""

    print("[TEST RUNNER] Executing questionnaire system tests")
    results = {}

    for name, func in [
        ("business_owner", test_business_owner_complete_flow),
        ("startup_founder", test_startup_founder_flow),
        ("personal_brand", test_personal_brand_flow),
        ("location", test_location_integration),
        ("framework_selection", test_framework_selection_logic),
    ]:
        try:
            func()
            results[name] = True
        except Exception as exc:  # pragma: no cover - debugging utility
            print(f"[TEST RUNNER] {name} failed: {exc}")
            results[name] = False

    print("[TEST RUNNER] Summary")
    passed = sum(1 for value in results.values() if value)
    total = len(results)
    for key, value in results.items():
        status = "PASSED" if value else "FAILED"
        print(f"  {key}: {status}")

    print(f"[TEST RUNNER] {passed}/{total} tests passed")
    return passed == total


def test_run_all_tests() -> None:
    """Ensure the bundled runner reports success when all flows pass."""

    assert run_all_tests() is True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
