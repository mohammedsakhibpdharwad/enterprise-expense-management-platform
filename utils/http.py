from flask import request, url_for
from math import ceil


def page_number():
    try:
        return max(int(request.args.get("page", 1)), 1)
    except ValueError:
        return 1


def pager(total, page, per_page=20):
    pages = max(ceil(total / per_page), 1) if total else 1
    return {"total": total, "page": page, "per_page": per_page, "pages": pages}


def expense_filters_from_request():
    return {
        "q": request.args.get("q", "").strip(),
        "employee_id": request.args.get("employee_id"),
        "employee_code": request.args.get("employee_code", "").strip(),
        "department": request.args.get("department", "").strip(),
        "department_id": request.args.get("department_id"),
        "category_id": request.args.get("category_id"),
        "status": request.args.get("status", "").strip(),
        "stage": request.args.get("stage", "").strip(),
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to"),
        "amount_min": request.args.get("amount_min"),
        "amount_max": request.args.get("amount_max"),
        "risk": request.args.get("risk"),
    }


def safe_next_url(candidate, fallback_endpoint):
    if candidate and candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return url_for(fallback_endpoint)
