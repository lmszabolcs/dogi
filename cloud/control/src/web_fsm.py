from flask import Flask, render_template
from flask import jsonify

PORT = 5056

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('web_fsm.html')

def read_fsm_state():
    try:
        with open("/tmp/fsm_state", "r") as f:
            return f.read().strip()
    except Exception:
        pass
    return "unknown"


@app.route('/state')
def state_api():
    state_val = read_fsm_state()
    print(f"[WEB] /state endpoint called, returning: {state_val}")
    return jsonify({'state': state_val})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
