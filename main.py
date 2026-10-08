"""OutcomeOS: local HTTP server + Vercel-compatible WSGI entrypoint."""
from vercel_wsgi import application
app = application

if __name__ == '__main__':
    from app.http_api import main
    main()
