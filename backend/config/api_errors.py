from django.http import JsonResponse
from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        code = "VALIDATION_ERROR"
        message = "One or more fields are invalid."
        details = response.data
    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "AUTHENTICATION_FAILED"
        message = "Authentication is required to complete this request."
        details = {}
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        code = "FORBIDDEN"
        message = "The request could not be authorized."
        details = {}
    else:
        code = "REQUEST_ERROR"
        message = "The request could not be completed."
        details = {}

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }
    return response


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "error": {
                "code": "CSRF_FAILED",
                "message": "The request could not be validated.",
                "details": {},
            }
        },
        status=403,
    )