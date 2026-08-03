from flask import Blueprint, render_template

call_centers = Blueprint("call_centers", __name__)

@call_centers.get("/call-centers")
@call_centers.get("/call-centers/")
def landing():
    """Presenta Talent Call y los servicios DPIA para call centers."""
    return render_template("callCenters/index.html")
