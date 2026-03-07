import random
import time

import requests

BASE = "http://localhost:8000"
IMG = "ml_models/data/raw/images/validation/claim_000/0001.JPEG"
now = int(time.time())
suffix = f"route{now}{random.randint(100, 999)}"

results = []


def record(name, method, path, status, ok, detail=""):
    results.append({"name": name, "method": method, "path": path, "status": status, "ok": ok, "detail": detail})


def call(name, method, path, expected=(200, 201), **kwargs):
    url = BASE + path
    try:
        response = requests.request(method, url, timeout=30, **kwargs)
        ok = response.status_code in expected
        detail = "" if ok else response.text[:220].replace("\n", " ")
        record(name, method, path, response.status_code, ok, detail)
        return response
    except Exception as exc:
        record(name, method, path, "ERR", False, str(exc))
        return None


def main():
    call("health", "GET", "/health", (200,))
    call("metrics", "GET", "/metrics", (200,))

    admin_login = call(
        "auth.login.admin",
        "POST",
        "/api/v1/auth/login",
        (200,),
        json={"email": "admin1@frauddemo.com", "password": "Admin@123!"},
    )
    if not admin_login or admin_login.status_code != 200:
        print("FATAL: admin login failed")
        return 1

    admin_access = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_access}"}

    email = f"{suffix}@frauddemo.com"
    password = "User@1234"
    new_password = "User@5678"

    call(
        "auth.register",
        "POST",
        "/api/v1/auth/register",
        (201,),
        json={"email": email, "full_name": "Route User", "password": password},
    )
    login = call(
        "auth.login.user",
        "POST",
        "/api/v1/auth/login",
        (200,),
        json={"email": email, "password": password},
    )
    if login is None or login.status_code != 200:
        print("FATAL: user login failed")
        return 1

    user_data = login.json()
    user_access = user_data["access_token"]
    user_refresh = user_data["refresh_token"]
    user_headers = {"Authorization": f"Bearer {user_access}"}

    call("auth.me", "GET", "/api/v1/auth/me", (200,), headers=user_headers)
    call("auth.refresh", "POST", "/api/v1/auth/refresh", (200,), json={"refresh_token": user_refresh})
    call(
        "auth.change_password",
        "PUT",
        "/api/v1/auth/change-password",
        (200,),
        headers=user_headers,
        json={"old_password": password, "new_password": new_password},
    )

    login2 = call(
        "auth.login.user.newpw",
        "POST",
        "/api/v1/auth/login",
        (200,),
        json={"email": email, "password": new_password},
    )
    logout_headers = user_headers
    logout_refresh = user_refresh
    if login2 is not None and login2.status_code == 200:
        login2_data = login2.json()
        logout_headers = {"Authorization": f"Bearer {login2_data['access_token']}"}
        logout_refresh = login2_data["refresh_token"]

    call("admin.users.list", "GET", "/api/v1/admin/users", (200,), headers=admin_headers)

    admin_created_id = None
    create_user = call(
        "admin.users.create",
        "POST",
        "/api/v1/admin/users",
        (201,),
        headers=admin_headers,
        json={
            "email": f"admincreate_{suffix}@frauddemo.com",
            "full_name": "Created User",
            "password": "Temp@1234",
            "role": "surveyor",
            "is_active": True,
        },
    )
    if create_user is not None and create_user.status_code == 201:
        admin_created_id = create_user.json()["id"]

    call("admin.roles.list", "GET", "/api/v1/admin/roles", (200,), headers=admin_headers)

    role_id = None
    role_create = call(
        "admin.roles.create",
        "POST",
        "/api/v1/admin/roles",
        (200,),
        headers=admin_headers,
        json={"name": f"auditor_{suffix}", "permissions": {"claims": ["read"]}},
    )
    if role_create is not None and role_create.status_code == 200:
        role_id = role_create.json().get("id")

    if role_id is not None:
        call(
            "admin.roles.update_permissions",
            "PUT",
            f"/api/v1/admin/roles/{role_id}/permissions",
            (200,),
            headers=admin_headers,
            json={"permissions": {"claims": ["read", "update"]}},
        )

    if admin_created_id is not None:
        call(
            "admin.users.update_role",
            "PUT",
            f"/api/v1/admin/users/{admin_created_id}/role",
            (200,),
            headers=admin_headers,
            json={"role": "admin"},
        )
        call(
            "admin.users.deactivate",
            "PUT",
            f"/api/v1/admin/users/{admin_created_id}/activate/deactivate",
            (200,),
            headers=admin_headers,
            json={"is_active": False},
        )
        call(
            "admin.users.activate",
            "PUT",
            f"/api/v1/admin/users/{admin_created_id}/activate/deactivate",
            (200,),
            headers=admin_headers,
            json={"is_active": True},
        )

    call(
        "claims.create.admin_forbidden",
        "POST",
        "/api/v1/claims",
        (403,),
        headers=admin_headers,
        data={"policy_number": f"P-{suffix}-admin", "claim_amount": "9999", "accident_date": "2026-03-01"},
    )

    claim = call(
        "claims.create",
        "POST",
        "/api/v1/claims",
        (201,),
        headers=user_headers,
        data={"policy_number": f"P-{suffix}", "claim_amount": "9999", "accident_date": "2026-03-01"},
    )
    if claim is None or claim.status_code not in (200, 201):
        print("FATAL: claim create failed")
        return 1

    claim_id = claim.json()["id"]

    call("claims.list", "GET", "/api/v1/claims", (200,), headers=user_headers)
    call("claims.get", "GET", f"/api/v1/claims/{claim_id}", (200,), headers=user_headers)
    call(
        "claims.update",
        "PUT",
        f"/api/v1/claims/{claim_id}",
        (200,),
        headers=user_headers,
        json={"status": "under_review"},
    )

    with open(IMG, "rb") as file_obj:
        uploaded = call(
            "claims.images.upload",
            "POST",
            f"/api/v1/claims/{claim_id}/images",
            (201,),
            headers=user_headers,
            files={"image_file": ("0001.JPEG", file_obj, "image/jpeg")},
        )

    image_id = None
    if uploaded is not None and uploaded.status_code in (200, 201):
        image_id = uploaded.json()["id"]

    call("claims.images.list", "GET", f"/api/v1/claims/{claim_id}/images", (200,), headers=user_headers)

    with open(IMG, "rb") as file_obj:
        image_uploaded = call(
            "images.upload",
            "POST",
            f"/api/v1/images/upload?claim_id={claim_id}",
            (200,),
            headers=user_headers,
            files={"image_file": ("0001.JPEG", file_obj, "image/jpeg")},
        )
    if image_uploaded is not None and image_uploaded.status_code == 200 and image_id is None:
        image_id = image_uploaded.json()["id"]

    with open(IMG, "rb") as first_file, open(IMG, "rb") as second_file:
        call(
            "images.batch_upload",
            "POST",
            f"/api/v1/images/batch-upload?claim_id={claim_id}",
            (200,),
            headers=user_headers,
            files=[
                ("image_files", ("a.JPEG", first_file, "image/jpeg")),
                ("image_files", ("b.JPEG", second_file, "image/jpeg")),
            ],
        )

    if image_id is not None:
        call("images.damage", "GET", f"/api/v1/images/{image_id}/damage", (200,), headers=user_headers)
        call("images.visualization", "GET", f"/api/v1/images/{image_id}/visualization", (200,), headers=user_headers)

    call("fraud.predict", "POST", "/api/v1/fraud/predict", (200,), headers=user_headers, json={"claim_id": claim_id})
    call("fraud.status", "GET", f"/api/v1/fraud/status/{claim_id}", (200,), headers=user_headers)
    call("fraud.results", "GET", f"/api/v1/fraud/results/{claim_id}", (200,), headers=user_headers)
    call("fraud.batch", "POST", "/api/v1/fraud/batch", (200,), headers=user_headers, json={"claim_ids": [claim_id]})

    call("reports.generate.admin_forbidden", "POST", f"/api/v1/reports/generate/{claim_id}", (403,), headers=admin_headers)
    report = call("reports.generate", "POST", f"/api/v1/reports/generate/{claim_id}", (200,), headers=user_headers)
    report_id = None
    if report is not None and report.status_code == 200:
        report_id = report.json()["report_id"]

    call("reports.list", "GET", "/api/v1/reports", (200,), headers=user_headers)
    call("reports.by_claim", "GET", f"/api/v1/reports/claim/{claim_id}", (200,), headers=user_headers)
    if report_id is not None:
        call("reports.download", "GET", f"/api/v1/reports/{report_id}", (200,), headers=user_headers)

    call("dashboard.stats", "GET", "/api/v1/dashboard/stats", (200,), headers=user_headers)
    call("dashboard.trends", "GET", "/api/v1/dashboard/trends", (200,), headers=user_headers)
    call("dashboard.high_risk", "GET", "/api/v1/dashboard/high-risk", (200,), headers=user_headers)
    call("dashboard.recent_activity", "GET", "/api/v1/dashboard/recent-activity", (200,), headers=user_headers)

    call("admin.dashboard.stats", "GET", "/api/v1/admin/dashboard/stats", (200,), headers=admin_headers)
    call("admin.logs", "GET", "/api/v1/admin/logs", (200,), headers=admin_headers)
    call("admin.ml_models", "GET", "/api/v1/admin/ml-models", (200,), headers=admin_headers)
    call("admin.surveyors", "GET", "/api/v1/admin/surveyors", (200,), headers=admin_headers)
    call("admin.claims", "GET", "/api/v1/admin/claims", (200,), headers=admin_headers)
    call("admin.reports", "GET", "/api/v1/admin/reports", (200,), headers=admin_headers)

    if admin_created_id is not None:
        call("admin.users.delete", "DELETE", f"/api/v1/admin/users/{admin_created_id}", (200,), headers=admin_headers)

    call("claims.delete", "DELETE", f"/api/v1/claims/{claim_id}", (200,), headers=user_headers)
    call(
        "auth.logout",
        "POST",
        "/api/v1/auth/logout",
        (200,),
        headers={**logout_headers, "X-Refresh-Token": logout_refresh},
    )

    failures = [item for item in results if not item["ok"]]
    print(f"TOTAL {len(results)}")
    print(f"PASS {len(results) - len(failures)}")
    print(f"FAIL {len(failures)}")
    for item in failures:
        print(f"FAIL {item['method']} {item['path']} -> {item['status']} :: {item['detail']}")

    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
