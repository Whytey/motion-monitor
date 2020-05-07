import logging
import sys

from flask import Flask, jsonify
from flask.helpers import get_debug_flag
from flask_cors import CORS

from motionmonitor.config import Development
from motionmonitor.config import Production


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


def create_app(config_object=Production):
    app = Flask(__name__, instance_relative_config=True)

    # Load the configguration from the config_object
    app.config.from_object(config_object)

    # Load the overiding configuration from the instance folder
    app.config.from_pyfile('config.py')

    logging.info(app.config)

    cors = CORS(app)

    # app.register_blueprint(connect_bp, url_prefix='/api/v1.0')
    # app.register_blueprint(members_bp, url_prefix='/api/v1.0')
    # app.register_blueprint(challenges_bp, url_prefix='/api/v1.0')
    # app.register_blueprint(attempts_bp, url_prefix='/api/v1.0')

    @app.route("/")
    def index():
        return app.send_static_file('index.html')

    @app.route('/appconfig.json')
    def config():
        """Provide a JSON object describing the configuration needed for the frontend"""
        api_url = app.config['API_URL']
        logging.debug("sharing API URL: {}".format(api_url))
        return jsonify({"api": api_url})

    @app.route('/<path:the_path>')
    def all_other_routes(the_path):
        return app.send_static_file(the_path)

    return app


CONFIG = Development if get_debug_flag() else Production
app = create_app(CONFIG)

# For running in dev, need to actually run the app!
if __name__ == '__main__':
    app.run(debug=True)
