from flask import Flask
from flask_cors import CORS
from api.routes import api_blueprint


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(api_blueprint, url_prefix="/api")
    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)