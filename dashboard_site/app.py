"""Flask application for the data quality dashboard site."""

from __future__ import annotations

from flask import Flask, abort, render_template, request, send_file

from dashboard_site.dashboard_data import (
    get_artifact_map,
    get_dashboard_context,
    get_explorer_filters,
    search_cleaned_dataset,
)


def create_app() -> Flask:
    """Create and configure the Flask dashboard app."""

    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    @app.get("/")
    def dashboard():
        context = get_dashboard_context(
            {
                "search": request.args.get("search", "", type=str),
                "province": request.args.get("province", "", type=str),
                "owner_org": request.args.get("owner_org", "", type=str),
                "year": request.args.get("year", "", type=str),
            }
        )
        return render_template("dashboard.html", **context)

    @app.get("/explorer")
    def explorer():
        query = request.args.get("q", "", type=str)
        field = request.args.get("field", "all", type=str)
        results = search_cleaned_dataset(query=query, field=field)
        return render_template(
            "explorer.html",
            filters=get_explorer_filters(),
            results=results,
        )

    @app.get("/downloads/<slug>")
    def download_artifact(slug: str):
        artifact = get_artifact_map().get(slug)
        if artifact is None or not artifact.path.exists():
            abort(404)
        return send_file(artifact.path, as_attachment=True, download_name=artifact.path.name)

    @app.get("/health")
    def healthcheck():
        return {"status": "ok"}

    return app


app = create_app()
