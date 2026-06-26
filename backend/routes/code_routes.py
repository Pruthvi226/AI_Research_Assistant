def register_code_routes(app, handlers):
    @app.route("/api/code", methods=["POST"], endpoint="api_code")
    def api_code():
        return handlers["code"]()
