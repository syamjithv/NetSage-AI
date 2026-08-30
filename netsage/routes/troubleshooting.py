from flask import Blueprint, render_template

troubleshooting_bp = Blueprint("troubleshooting", __name__, url_prefix="/troubleshoot")


@troubleshooting_bp.route("/")
def troubleshoot_home():
    return render_template("troubleshoot.html")
