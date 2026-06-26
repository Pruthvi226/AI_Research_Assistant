def register_citation_routes(app, handlers):
    @app.route("/api/citations", methods=["POST"], endpoint="api_citations")
    def api_citations():
        return handlers["citations"]()
