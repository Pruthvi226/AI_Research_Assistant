def register_podcast_routes(app, handlers):
    @app.route("/api/podcast", methods=["POST"], endpoint="api_podcast")
    def api_podcast():
        return handlers["podcast"]()

    @app.route("/api/generated-audio/<session_id>.mp3", methods=["GET"], endpoint="api_generated_audio")
    def api_generated_audio(session_id):
        return handlers["generated_audio"](session_id)
