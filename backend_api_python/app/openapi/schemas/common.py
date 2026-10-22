"""
Shared Marshmallow schemas for the single-host web API.
"""
from marshmallow import Schema, fields


class HumanSuccessEnvelopeSchema(Schema):
    """Standard success wrapper for human web API routes."""

    code = fields.Integer(
        metadata={"description": "1 on success", "example": 1},
    )
    msg = fields.String(metadata={"example": "success"})
    data = fields.Raw(allow_none=True)


class HumanErrorEnvelopeSchema(Schema):
    """Standard error wrapper for human web API routes."""

    code = fields.Integer(
        metadata={"description": "0 on error", "example": 0},
    )
    msg = fields.String()
    data = fields.Raw(allow_none=True)


class PaginationMetaSchema(Schema):
    """Common list pagination metadata."""

    page = fields.Integer()
    page_size = fields.Integer()
    total = fields.Integer()


class ApiInfoSchema(Schema):
    """GET / — API identity payload."""

    name = fields.String(metadata={"example": "QuantDinger Python API"})
    version = fields.String(metadata={"example": "5.0.1"})
    status = fields.String(metadata={"example": "running"})
    timestamp = fields.DateTime(format="iso")


class HealthStatusSchema(Schema):
    """GET /health and GET /api/health."""

    status = fields.String(metadata={"example": "healthy"})
    timestamp = fields.DateTime(format="iso")
    role = fields.String(metadata={"example": "api"})


class ReadinessStatusSchema(HealthStatusSchema):
    checks = fields.Dict(keys=fields.String(), values=fields.Boolean())


class WorkerHealthSchema(HealthStatusSchema):
    workers = fields.List(fields.Dict())
