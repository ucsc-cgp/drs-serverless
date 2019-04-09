import drs
from flask import jsonify

app = drs.create_app()

@app.route("/")
def serve_swagger_ui():
    return jsonify({})

if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
