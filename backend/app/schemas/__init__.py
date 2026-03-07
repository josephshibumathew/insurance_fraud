"""Schema package exports."""

from app.schemas.auth import TokenResponse, UserInfo, UserLoginRequest, UserRegisterRequest
from app.schemas.claim import ClaimCreateRequest, ClaimListResponse, ClaimResponse, ClaimUpdateRequest
from app.schemas.dashboard import DashboardStatsResponse, DashboardTrendResponse
from app.schemas.fraud import FraudBatchRequest, FraudBatchResponse, FraudPredictRequest, FraudResultResponse
from app.schemas.image import DamageResultResponse, ImageResponse
from app.schemas.report import GenerateReportResponse, ReportResponse
from app.schemas.response import APIError, APIMessage

__all__ = [
	"UserRegisterRequest",
	"UserLoginRequest",
	"TokenResponse",
	"UserInfo",
	"ClaimCreateRequest",
	"ClaimUpdateRequest",
	"ClaimResponse",
	"ClaimListResponse",
	"FraudPredictRequest",
	"FraudResultResponse",
	"FraudBatchRequest",
	"FraudBatchResponse",
	"ImageResponse",
	"DamageResultResponse",
	"GenerateReportResponse",
	"ReportResponse",
	"DashboardStatsResponse",
	"DashboardTrendResponse",
	"APIMessage",
	"APIError",
]

