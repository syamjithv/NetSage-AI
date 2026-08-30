from flask import Blueprint, render_template

review_bp = Blueprint("review", __name__, url_prefix="/review")


@review_bp.route("/")
def review_home():
    return render_template("review.html")
