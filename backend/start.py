"""Start the hosted API with a per-instance Flask secret when none was provisioned."""
import os
import secrets


def main():
    if not os.environ.get('SECRET_KEY'):
        os.environ['SECRET_KEY'] = secrets.token_urlsafe(32)
    from waitress import serve
    from app import app
    serve(app, host='0.0.0.0', port=int(os.environ.get('PORT', '5000')))


if __name__ == '__main__':
    main()
