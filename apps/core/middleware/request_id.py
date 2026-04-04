"""Request ID middleware for correlation across logs."""
import uuid


class RequestIdMiddleware:
    """Attach a unique request_id to every request for log correlation."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.META.get("HTTP_X_REQUEST_ID", str(uuid.uuid4()))
        response = self.get_response(request)
        response["X-Request-Id"] = request.request_id
        return response
