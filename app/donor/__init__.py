"""Donor Blueprint — __init__"""
from flask import Blueprint
donor = Blueprint('donor', __name__)
from app.donor import routes  # noqa: F401, E402
