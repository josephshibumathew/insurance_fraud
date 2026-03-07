from __future__ import annotations

from datetime import date

from app.models.claim import Claim
from app.models.user import User


def test_user_crud(test_db):
    user = User(email="crud@test.com", hashed_password="hashed", full_name="CRUD User", role="surveyor", is_active=True)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    fetched = test_db.get(User, user.id)
    assert fetched is not None
    assert fetched.email == "crud@test.com"

    fetched.full_name = "Updated Name"
    test_db.add(fetched)
    test_db.commit()

    updated = test_db.get(User, user.id)
    assert updated.full_name == "Updated Name"


def test_claim_crud(test_db, test_user):
    claim = Claim(user_id=test_user.id, policy_number="P-CRUD", claim_amount=1200.0, accident_date=date(2025, 1, 1), status="submitted")
    test_db.add(claim)
    test_db.commit()
    test_db.refresh(claim)

    loaded = test_db.get(Claim, claim.id)
    assert loaded is not None
    assert loaded.policy_number == "P-CRUD"

    test_db.delete(loaded)
    test_db.commit()
    assert test_db.get(Claim, claim.id) is None
