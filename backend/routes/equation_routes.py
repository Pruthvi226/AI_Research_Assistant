def register_equation_routes(app, handlers):
    @app.route("/api/equation", methods=["POST"], endpoint="api_equation")
    def api_equation():
        return handlers["equation"]()
