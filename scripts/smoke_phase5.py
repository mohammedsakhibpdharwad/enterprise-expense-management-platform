from datetime import date

from app import create_app


PASSWORD = "Password123!"


def login(client, email):
    return client.post(
        "/login",
        data={"email": email, "password": PASSWORD},
        follow_redirects=False,
    )


def main():
    app = create_app()
    client = app.test_client()

    # Unauthenticated access
    r = client.get("/admin/dashboard", follow_redirects=False)
    print("unauth admin:", r.status_code, r.headers.get("Location"))

    # Employee
    r = login(client, "test@example.com")
    print("employee login:", r.status_code, r.headers.get("Location"))

    print("employee dash:", client.get("/employee/dashboard").status_code)

    r = client.get("/admin/dashboard", follow_redirects=False)
    print("employee -> admin:", r.status_code, r.headers.get("Location"))

    # Get a category
    page = client.get("/employee/dashboard")
    marker = b'option value="'
    start = page.data.find(marker)
    category_id = None

    if start != -1:
        start += len(marker)
        end = page.data.find(b'"', start)
        category_id = page.data[start:end].decode()

    print("category:", category_id)

    # Valid employee submission
    if category_id:
        r = client.post(
            "/employee/dashboard",
            data={
                "category_id": category_id,
                "amount": "12.50",
                "description": "Smoke test expense",
                "date": date.today().isoformat(),
            },
            follow_redirects=True,
        )
        print(
            "employee submit:",
            r.status_code,
            b"submitted successfully" in r.data,
        )

    # Invalid submission
    r = client.post(
        "/employee/dashboard",
        data={
            "category_id": category_id or "1",
            "amount": "-1",
            "description": "",
            "date": "2099-01-01",
        },
        follow_redirects=True,
    )

    print(
        "invalid submit:",
        r.status_code,
        (
            b"greater than zero" in r.data
            or b"required" in r.data
            or b"future" in r.data
        ),
    )

    client.get("/logout")

    # Super Admin
    r = login(client, "admin@example.com")
    print("super admin login:", r.status_code, r.headers.get("Location"))

    print("super admin dashboard:", client.get("/admin/system").status_code)
    print("employees:", client.get("/admin/employees").status_code)
    print("departments:", client.get("/admin/departments").status_code)
    print("rules:", client.get("/admin/rules").status_code)
    print("audit:", client.get("/admin/audit").status_code)

    # Existing admin/analytics functionality
    print("admin dashboard:", client.get("/admin/dashboard").status_code)
    print("analytics:", client.get("/admin/analytics").status_code)

    summary = client.get("/admin/api/analytics/summary")
    print("summary:", summary.status_code, summary.get_json())

    print("csv:", client.get("/admin/analytics/download").status_code)

    # Super admin should not access employee-only dashboard
    r = client.get("/employee/dashboard", follow_redirects=False)
    print("super admin -> employee:", r.status_code, r.headers.get("Location"))

    client.get("/logout")

    # Manager
    r = login(client, "manager@example.com")
    print("manager login:", r.status_code, r.headers.get("Location"))
    print("manager dashboard:", client.get("/manager/dashboard").status_code)
    print("manager approvals:", client.get("/approvals").status_code)

    client.get("/logout")

    # Finance
    r = login(client, "finance@example.com")
    print("finance login:", r.status_code, r.headers.get("Location"))
    print("finance dashboard:", client.get("/finance/dashboard").status_code)
    print("finance reports:", client.get("/finance/reports").status_code)
    print("finance policies:", client.get("/finance/policies").status_code)

    client.get("/logout")

    # Notifications
    r = login(client, "test@example.com")
    print("notification page:", client.get("/notifications").status_code)

    print("\nSMOKE TEST COMPLETE")


if __name__ == "__main__":
    main()