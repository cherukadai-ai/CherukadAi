from app.core.exceptions import (
    FeatureDisabledError,
    ForbiddenError,
    NotFoundError,
    TenantMismatchError,
)


def test_not_found_error_defaults():
    err = NotFoundError()
    assert err.status_code == 404
    assert err.error_code == "not_found"


def test_custom_message_and_details():
    err = NotFoundError("Project not found", project_id="abc-123")
    assert str(err) == "Project not found"
    assert err.details == {"project_id": "abc-123"}


def test_feature_disabled_is_a_forbidden_error():
    err = FeatureDisabledError("BOQ AI is disabled for this organisation")
    assert isinstance(err, ForbiddenError)
    assert err.status_code == 403
    assert err.error_code == "feature_disabled"


def test_tenant_mismatch_is_a_forbidden_error():
    err = TenantMismatchError()
    assert isinstance(err, ForbiddenError)
    assert err.error_code == "tenant_mismatch"
