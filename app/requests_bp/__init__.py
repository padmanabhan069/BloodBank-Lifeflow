"""Requests Blueprint — __init__"""
from flask import Blueprint
requests = Blueprint('requests', __name__)
from app.requests_bp import routes  # noqa: F401, E402
