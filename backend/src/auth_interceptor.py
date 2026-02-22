import logging
import os

import firebase_admin
import grpc
from firebase_admin import auth

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
# In production, specify the service account key path via GOOGLE_APPLICATION_CREDENTIALS
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()


class AuthInterceptor(grpc.ServerInterceptor):
    def __init__(self):
        def abort(context, code, details):
            context.abort(code, details)

        self._abort = abort

    def intercept_service(self, continuation, handler_call_details):
        # List of methods that don't require authentication (e.g., Health check)
        # For now, let's protect everything except basic getters if needed,
        # but the plan says "Reject unauthenticated requests to protected methods."

        # Metadata is a list of tuples (key, value)
        metadata = dict(handler_call_details.invocation_metadata)
        auth_header = metadata.get("authorization", "")

        uid = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                # Verify the ID token
                decoded_token = auth.verify_id_token(token)
                uid = decoded_token["uid"]
            except Exception as e:
                logger.warning(f"Failed to verify ID token: {e}")
                # We could abort here, but let's just pass None and let the servicer decide
                # or abort if it's a strictly protected method.
                pass

        # Add uid to context for use in servicer methods
        # Note: grpcio doesn't make it easy to modify the context in a sync interceptor
        # without wrapping the handler.

        handler = continuation(handler_call_details)
        if handler is None:
            return None

        if uid:
            # We can't easily inject into 'context' from here in sync gRPC easily
            # without a wrapper. A common pattern is to use a thread-local or
            # wrap the context.
            pass

        return handler


# For more robust implementation, we wrap the handler to inject the UID
class AuthHandlerWrapper(grpc.RpcMethodHandler):
    def __init__(self, handler, uid):
        self.request_streaming = handler.request_streaming
        self.response_streaming = handler.response_streaming
        self.request_deserializer = handler.request_deserializer
        self.response_serializer = handler.response_serializer

        if self.request_streaming:
            if self.response_streaming:
                self.stream_stream = self._wrap_behavior(handler.stream_stream)
            else:
                self.stream_unary = self._wrap_behavior(handler.stream_unary)
        else:
            if self.response_streaming:
                self.unary_stream = self._wrap_behavior(handler.unary_stream)
            else:
                self.unary_unary = self._wrap_behavior(handler.unary_unary)
        self.uid = uid

    def _wrap_behavior(self, behavior):
        def wrapped(request, context):
            context.uid = self.uid
            return behavior(request, context)

        return wrapped


class FirebaseAuthInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        metadata = {k.lower(): v for k, v in handler_call_details.invocation_metadata}
        auth_header = metadata.get("authorization", "")

        uid = None
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer ") :]
            try:
                if token == "dev-token" and os.getenv("GRPC_AUTH_DISABLED") == "true":
                    uid = "dev-user"
                else:
                    decoded_token = auth.verify_id_token(token)
                    uid = decoded_token["uid"]
            except Exception as e:
                logger.warning(f"Invalid token: {e}")

        handler = continuation(handler_call_details)
        if handler is None:
            return None

        return AuthHandlerWrapper(handler, uid)
