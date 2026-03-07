"""Claim management business logic."""

from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.claim import Claim


class ClaimService:
	def __init__(self, db: Session) -> None:
		self.db = db

	def create_claim(self, user_id: int, policy_number: str, claim_amount: float, accident_date: date) -> Claim:
		claim = Claim(
			user_id=user_id,
			policy_number=policy_number,
			claim_amount=claim_amount,
			accident_date=accident_date,
			status="submitted",
		)
		self.db.add(claim)
		self.db.commit()
		self.db.refresh(claim)
		return claim

	async def create_claims_from_csv(self, user_id: int, file: UploadFile) -> list[Claim]:
		content = (await file.read()).decode("utf-8", errors="ignore")
		reader = csv.DictReader(io.StringIO(content))
		created: list[Claim] = []
		for row in reader:
			policy_number = str(row.get("policy_number", "")).strip()
			claim_amount = float(row.get("claim_amount", 0) or 0)
			accident_date = date.fromisoformat(str(row.get("accident_date")))
			if policy_number and claim_amount > 0:
				created.append(self.create_claim(user_id, policy_number, claim_amount, accident_date))
		return created

	def list_claims(
		self,
		*,
		page: int,
		page_size: int,
		status: str | None = None,
		policy_number: str | None = None,
		user_id: int | None = None,
	) -> tuple[list[Claim], int]:
		stmt = select(Claim)
		count_stmt = select(func.count(Claim.id))

		if user_id is not None:
			stmt = stmt.where(Claim.user_id == user_id)
			count_stmt = count_stmt.where(Claim.user_id == user_id)

		if status:
			stmt = stmt.where(Claim.status == status)
			count_stmt = count_stmt.where(Claim.status == status)
		if policy_number:
			stmt = stmt.where(Claim.policy_number.like(f"%{policy_number}%"))
			count_stmt = count_stmt.where(Claim.policy_number.like(f"%{policy_number}%"))

		stmt = stmt.order_by(Claim.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
		items = list(self.db.execute(stmt).scalars().all())
		total = int(self.db.execute(count_stmt).scalar_one())
		return items, total

	def get_claim(self, claim_id: int) -> Claim | None:
		return self.db.get(Claim, claim_id)

	def update_claim(self, claim: Claim, data: dict) -> Claim:
		for key, value in data.items():
			if value is not None and hasattr(claim, key):
				setattr(claim, key, value)
		self.db.add(claim)
		self.db.commit()
		self.db.refresh(claim)
		return claim

	def delete_claim(self, claim: Claim) -> None:
		self.db.delete(claim)
		self.db.commit()

