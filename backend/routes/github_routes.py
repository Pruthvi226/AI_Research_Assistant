def register_github_routes(app, handlers):
    @app.route("/api/github", methods=["POST"], endpoint="api_github")
    def api_github():
        return handlers["github"]()
