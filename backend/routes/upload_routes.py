def register_upload_routes(app, handlers):
    @app.route("/api/upload/pdf", methods=["POST"], endpoint="api_upload_pdf")
    def api_upload_pdf():
        return handlers["upload_pdf"]()

    @app.route("/api/upload/image", methods=["POST"], endpoint="api_upload_image")
    def api_upload_image():
        return handlers["upload_image"]()
