def register_chat_routes(app, handlers):
    @app.route("/api/chat", methods=["POST"], endpoint="api_chat")
    def api_chat():
        return handlers["chat"]()

    @app.route("/api/history", methods=["GET"], endpoint="api_history")
    def api_history():
        return handlers["history"]()
