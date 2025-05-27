from flask import Blueprint

pharmacy = Blueprint('pharmacy', __name__)

from . import views


