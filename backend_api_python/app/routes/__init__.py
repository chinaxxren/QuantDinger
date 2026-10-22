"""OpenAPI-registered single-host API routes."""
from flask import Flask


def register_routes(app: Flask):
    """Register the human web API via flask-smorest."""
    from app.openapi import init_openapi
    init_openapi(app)
