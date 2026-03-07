# Sentry Integration

## Backend
1. Install `sentry-sdk[fastapi]`.
2. Initialize in backend startup:

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "development"),
)
```

## Frontend
1. Install `@sentry/react`.
2. Initialize in `frontend/src/index.js`.
3. Capture route errors and performance transactions.
