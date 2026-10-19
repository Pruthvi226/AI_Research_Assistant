"""Start the hosted API with private runtime secrets when none were provisioned."""
import os
import secrets


def main():
    for name in ('SECRET_KEY', 'ADMIN_API_KEY'):
        if not os.environ.get(name):
            os.environ[name] = secrets.token_urlsafe(32)
    from waitress import serve
    from app import app
    serve(app, host='0.0.0.0', port=int(os.environ.get('PORT', '5000')))


if __name__ == '__main__':
    main()
