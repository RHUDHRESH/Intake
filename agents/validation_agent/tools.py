"""Validation utilities for schema, required fields, types, constraints, and custom rules."""
import asyncio
import re
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union

try:  # jsonschema is an optional dependency
    import jsonschema
    from jsonschema.exceptions import ValidationError, SchemaError
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled at runtime
    jsonschema = None
    ValidationError = SchemaError = Exception
    validator_for = None

MISSING = object()
TYPE_MAP: Dict[str, Tuple[type, ...]] = {
    "string": (str,),
    "number": (int, float),
    "integer": (int,),
    "boolean": (bool,),
    "array": (list, tuple),
    "object": (dict,),
}


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _matches_type(value: Any, expected: Union[str, Sequence[str]]) -> bool:
    if value is None:
        return False
    expected_types = (expected,) if isinstance(expected, str) else tuple(expected)
    for expected_type in expected_types:
        py_types = TYPE_MAP.get(expected_type.lower())
        if py_types is None:
            continue
        if isinstance(value, py_types):
            if expected_type.lower() == "integer" and not _is_integer(value):
                continue
            return True
    return False


def _get_nested_value(data: Any, field: str, delimiter: str = ".") -> Any:
    if not isinstance(data, Mapping):
        return MISSING
    current: Any = data
    for part in field.split(delimiter):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return MISSING
    return current


def _validate_schema_sync(data: Any, schema: Mapping[str, Any], draft: Optional[str]) -> Dict[str, Any]:
    if jsonschema is None:
        return {"valid": False, "errors": ["jsonschema is not installed"], "error_count": 1}
    if not isinstance(schema, Mapping):
        return {"valid": False, "errors": ["schema must be a mapping"], "error_count": 1}

    try:
        validator_cls = validator_for(schema) if validator_for else jsonschema.Draft7Validator
        validator = validator_cls(schema)
    except SchemaError as exc:
        return {"valid": False, "errors": [str(exc)], "error_count": 1}
    except Exception as exc:  # pragma: no cover - defensive
        return {"valid": False, "errors": [str(exc)], "error_count": 1}

    errors: List[Dict[str, Any]] = []
    for error in validator.iter_errors(data):
        errors.append(
            {
                "message": error.message,
                "path": list(error.absolute_path),
                "schema_path": list(error.absolute_schema_path),
                "validator": error.validator,
                "validator_value": error.validator_value,
            }
        )
    return {"valid": not errors, "errors": errors, "error_count": len(errors)}


def _validate_required_sync(
    data: Any,
    required_fields: Iterable[str],
    allow_empty: bool,
    delimiter: str,
) -> Dict[str, Any]:
    missing: List[str] = []
    for field in required_fields:
        value = _get_nested_value(data, field, delimiter)
        if value is MISSING:
            missing.append(field)
            continue
        if value is None:
            missing.append(field)
            continue
        if isinstance(value, str) and not allow_empty and not value.strip():
            missing.append(field)
    return {"valid": not missing, "missing": missing, "missing_count": len(missing)}


def _validate_types_sync(
    data: Any,
    type_rules: Mapping[str, Union[str, Sequence[str]]],
    skip_missing: bool,
    delimiter: str,
) -> Dict[str, Any]:
    invalid: Dict[str, str] = {}
    for field, expected in type_rules.items():
        value = _get_nested_value(data, field, delimiter)
        if value is MISSING:
            if not skip_missing:
                invalid[field] = "missing"
            continue
        if value is None:
            invalid[field] = "null"
            continue
        if not _matches_type(value, expected):
            invalid[field] = f"expected {expected}, found {type(value).__name__}"
    return {"valid": not invalid, "invalid_fields": invalid, "invalid_count": len(invalid)}


def _validate_constraints_sync(
    data: Any,
    constraints: Mapping[str, Mapping[str, Any]],
    delimiter: str,
) -> Dict[str, Any]:
    violations: Dict[str, List[str]] = {}
    for field, rules in constraints.items():
        raw_value = _get_nested_value(data, field, delimiter)
        if raw_value is MISSING:
            continue
        field_violations: List[str] = []
        if raw_value is None:
            field_violations.append("value is null")
        else:
            min_value = rules.get("min")
            max_value = rules.get("max")
            if min_value is not None:
                try:
                    if raw_value < min_value:
                        field_violations.append(f"value {raw_value} < min {min_value}")
                except TypeError:
                    field_violations.append("value is not comparable for min check")
            if max_value is not None:
                try:
                    if raw_value > max_value:
                        field_violations.append(f"value {raw_value} > max {max_value}")
                except TypeError:
                    field_violations.append("value is not comparable for max check")

            min_length = rules.get("min_length")
            max_length = rules.get("max_length")
            if min_length is not None:
                try:
                    if len(raw_value) < min_length:
                        field_violations.append(
                            f"length {len(raw_value)} < min_length {min_length}"
                        )
                except TypeError:
                    field_violations.append("value has no length for min_length check")
            if max_length is not None:
                try:
                    if len(raw_value) > max_length:
                        field_violations.append(
                            f"length {len(raw_value)} > max_length {max_length}"
                        )
                except TypeError:
                    field_violations.append("value has no length for max_length check")

            pattern = rules.get("pattern") or rules.get("regex")
            if pattern:
                regex = re.compile(pattern)
                if not isinstance(raw_value, str) or not regex.search(raw_value):
                    field_violations.append("pattern check failed")

            choices = rules.get("choices")
            if choices is not None and raw_value not in choices:
                field_violations.append("value not in allowed choices")

            disallowed = rules.get("disallow") or rules.get("not_in")
            if disallowed is not None and raw_value in disallowed:
                field_violations.append("value is disallowed")

        if field_violations:
            violations[field] = field_violations
    return {"valid": not violations, "violations": violations, "violation_count": len(violations)}


def _rule_non_empty(value: Any, **_: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def _rule_positive(value: Any, **_: Any) -> bool:
    try:
        return value is not None and float(value) > 0
    except (TypeError, ValueError):
        return False


def _rule_non_negative(value: Any, **_: Any) -> bool:
    try:
        return value is not None and float(value) >= 0
    except (TypeError, ValueError):
        return False


_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_REGEX = re.compile(r"^https?://[\w.-]+(?:/[\w\-.~:/?#[\]@!$&'()*+,;=%]*)?$")

def _rule_email(value: Any, **_: Any) -> bool:
    return isinstance(value, str) and bool(_EMAIL_REGEX.match(value))


def _rule_url(value: Any, **_: Any) -> bool:
    return isinstance(value, str) and bool(_URL_REGEX.match(value))


DEFAULT_RULES: Dict[str, Callable[..., bool]] = {
    "non_empty": _rule_non_empty,
    "positive": _rule_positive,
    "non_negative": _rule_non_negative,
    "email": _rule_email,
    "url": _rule_url,
}


def _normalize_custom_rules(
    rules: Union[Mapping[str, Any], Sequence[Any]],
    registry: Mapping[str, Callable[..., bool]],
) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []

    if isinstance(rules, Mapping):
        iterable = [
            {"field": field, "rule": spec}
            for field, spec in rules.items()
        ]
    else:
        iterable = list(rules)

    for entry in iterable:
        if isinstance(entry, Mapping):
            field = entry.get("field")
            rule_spec = entry.get("rule", entry.get("callable"))
            message = entry.get("message")
            args = entry.get("args", [])
            kwargs = entry.get("kwargs", {})
        else:
            field = None
            rule_spec = entry
            message = None
            args = []
            kwargs = {}

        func: Optional[Callable[..., bool]] = None
        rule_name = None

        if callable(rule_spec):
            func = rule_spec
        elif isinstance(rule_spec, str):
            rule_name = rule_spec
            func = registry.get(rule_spec)
        elif isinstance(rule_spec, Mapping):
            inner_rule = rule_spec.get("rule")
            if callable(inner_rule):
                func = inner_rule
            elif isinstance(inner_rule, str):
                rule_name = inner_rule
                func = registry.get(inner_rule)
            args = rule_spec.get("args", args)
            kwargs = rule_spec.get("kwargs", kwargs)
            message = rule_spec.get("message", message)
        else:
            func = None

        normalized.append(
            {
                "field": field,
                "callable": func,
                "rule_name": rule_name,
                "args": list(args),
                "kwargs": dict(kwargs),
                "message": message,
            }
        )

    return normalized


def _validate_custom_sync(
    data: Any,
    rules: Union[Mapping[str, Any], Sequence[Any]],
    registry: Optional[Mapping[str, Callable[..., bool]]],
    delimiter: str,
) -> Dict[str, Any]:
    if not rules:
        return {"valid": True, "failed": {}, "failed_count": 0}

    merged_registry: Dict[str, Callable[..., bool]] = DEFAULT_RULES.copy()
    if registry:
        merged_registry.update(registry)

    normalized_rules = _normalize_custom_rules(rules, merged_registry)
    failed: Dict[str, Dict[str, Any]] = {}

    for spec in normalized_rules:
        func = spec.get("callable")
        if func is None:
            rule_name = spec.get("rule_name")
            failed[spec.get("field") or rule_name or "unknown"] = {
                "message": f"Unknown rule '{rule_name}'"
            }
            continue

        field = spec.get("field")
        value = data if field is None else _get_nested_value(data, field, delimiter)
        if value is MISSING:
            failed[field or spec.get("rule_name") or "unknown"] = {
                "message": "Field not found for custom rule",
            }
            continue
        try:
            call_args = [value]
            call_args.extend(spec.get("args", []))
            call_kwargs = dict(spec.get("kwargs", {}))
            call_kwargs.setdefault("data", data)
            call_kwargs.setdefault("field", field)
            result = func(*call_args, **call_kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            failed[field or spec.get("rule_name") or "unknown"] = {
                "message": spec.get("message") or "Custom rule raised exception",
                "exception": str(exc),
            }
            continue
        if not result:
            failed[field or spec.get("rule_name") or "unknown"] = {
                "message": spec.get("message") or "Custom rule failed",
                "value": value,
            }

    return {"valid": not failed, "failed": failed, "failed_count": len(failed)}


async def validate_schema(data: Any, schema: Mapping[str, Any], draft: Optional[str] = None) -> Dict[str, Any]:
    return await asyncio.to_thread(_validate_schema_sync, data, schema, draft)


async def validate_required(
    data: Any,
    required_fields: Iterable[str],
    allow_empty: bool = False,
    delimiter: str = ".",
) -> Dict[str, Any]:
    return await asyncio.to_thread(_validate_required_sync, data, required_fields, allow_empty, delimiter)


async def validate_types(
    data: Any,
    type_rules: Mapping[str, Union[str, Sequence[str]]],
    skip_missing: bool = True,
    delimiter: str = ".",
) -> Dict[str, Any]:
    return await asyncio.to_thread(_validate_types_sync, data, type_rules, skip_missing, delimiter)


async def validate_constraints(
    data: Any,
    constraints: Mapping[str, Mapping[str, Any]],
    delimiter: str = ".",
) -> Dict[str, Any]:
    return await asyncio.to_thread(_validate_constraints_sync, data, constraints, delimiter)


async def validate_custom(
    data: Any,
    rules: Union[Mapping[str, Any], Sequence[Any]],
    registry: Optional[Mapping[str, Callable[..., bool]]] = None,
    delimiter: str = ".",
) -> Dict[str, Any]:
    return await asyncio.to_thread(_validate_custom_sync, data, rules, registry, delimiter)


VALIDATION_DISPATCH = {
    "schema": validate_schema,
    "required": validate_required,
    "types": validate_types,
    "constraints": validate_constraints,
    "custom": validate_custom,
}


async def run_validation_suite(
    checks: Sequence[Mapping[str, Any]],
    defaults: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    defaults = defaults or {}
    overall_valid = True
    results: List[Dict[str, Any]] = []
    stop_on_failure = bool(defaults.get("stop_on_failure"))

    for check in checks:
        ctype = str(check.get("type", defaults.get("default_type", "schema"))).lower()
        label = check.get("label")
        data = check.get("data", defaults.get("data", {}))
        dispatch = VALIDATION_DISPATCH.get(ctype)
        if dispatch is None:
            result = {
                "type": ctype,
                "label": label,
                "valid": False,
                "error": f"Unsupported validation type '{ctype}'",
            }
        else:
            kwargs: Dict[str, Any] = {"data": data}
            if ctype == "schema":
                kwargs["schema"] = check.get("schema")
                kwargs["draft"] = check.get("draft") or defaults.get("jsonschema_draft")
            elif ctype == "required":
                kwargs["required_fields"] = check.get("required") or check.get("fields") or []
                kwargs["allow_empty"] = check.get("allow_empty", defaults.get("allow_empty_strings", False))
                kwargs["delimiter"] = check.get("delimiter", ".")
            elif ctype == "types":
                kwargs["type_rules"] = check.get("type_rules") or check.get("rules") or {}
                kwargs["skip_missing"] = check.get("skip_missing", True)
                kwargs["delimiter"] = check.get("delimiter", ".")
            elif ctype == "constraints":
                kwargs["constraints"] = check.get("constraints") or {}
                kwargs["delimiter"] = check.get("delimiter", ".")
            elif ctype == "custom":
                kwargs["rules"] = check.get("rules") or {}
                kwargs["registry"] = check.get("registry") or defaults.get("custom_registry")
                kwargs["delimiter"] = check.get("delimiter", ".")

            missing_param = any(
                value is None and key in {"schema", "required_fields", "type_rules", "constraints", "rules"}
                for key, value in kwargs.items()
                if key != "data"
            )
            if missing_param:
                result = {
                    "type": ctype,
                    "label": label,
                    "valid": False,
                    "error": "Missing required parameters for validation",
                }
            else:
                validation_outcome = await dispatch(**kwargs)
                validation_outcome.update({"type": ctype, "label": label})
                result = validation_outcome

        results.append(result)
        if not result.get("valid", False):
            overall_valid = False
            if stop_on_failure or check.get("stop_on_failure"):
                break

    return {"valid": overall_valid, "results": results}
