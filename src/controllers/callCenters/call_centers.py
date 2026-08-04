from flask import Blueprint, render_template

call_centers = Blueprint("call_centers", __name__)

@call_centers.get("/call-centers")
@call_centers.get("/call-centers/")
def landing():
    """Presenta Talent Call y los servicios DPIA para call centers."""
    return render_template("callCenters/index.html")


@call_centers.get("/call-centers/servicios-ia")
@call_centers.get("/call-centers/servicios-ia/")
def servicios_ia():
    """Presenta las soluciones de inteligencia artificial para contact centers."""
    return render_template("callCenters/servicios_ia.html")


@call_centers.get("/call-centers/desarrollo")
@call_centers.get("/call-centers/desarrollo/")
def desarrollo():
    """Describe los servicios de desarrollo de software a medida de DPIA."""
    return render_template("callCenters/desarrollo.html")


@call_centers.get("/call-centers/soluciones")
@call_centers.get("/call-centers/soluciones/")
def soluciones():
    """Detalle de soluciones modulares para operaciones de contact center."""
    return render_template("callCenters/soluciones.html")
