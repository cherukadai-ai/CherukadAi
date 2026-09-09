from app.domain.base import TenantContext
import uuid

import pytest

from app.core.exceptions import ForbiddenError


def test_tenant_context_permission_check():
    ctx = TenantContext(
        organisation_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        permissions=frozenset({"projects:create"}),
    )
    assert ctx.has_permission("projects:create") is True
    assert ctx.has_permission("projects:delete") is False


def test_platform_admin_bypasses_permission_check():
    ctx = TenantContext(
        organisation_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        permissions=frozenset(),
        is_platform_admin=True,
    )
    assert ctx.has_permission("anything:whatsoever") is True


def test_suspended_membership_cannot_resolve():
    with pytest.raises(ForbiddenError):
        TenantContext.from_membership(
            organisation_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            permissions={"projects:read"},
            organisation_status="suspended",
        )
