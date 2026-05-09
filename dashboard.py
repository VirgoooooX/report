"""
Legacy dashboard entrypoint.

This module is intentionally side-effect free. It does not parse Excel files or
write to the database at import time. The supported runtime entrypoint is
`api.py` + Vue frontend.
"""

from flask import Flask, jsonify


app = Flask(__name__)


@app.route('/')
def legacy_index():
    return jsonify({
        'status': 'legacy_disabled',
        'message': 'Legacy Flask templates are disabled. Use api.py with the Vue frontend.',
    }), 410


@app.route('/api/stats')
def legacy_stats():
    return jsonify({
        'status': 'legacy_disabled',
        'message': 'Legacy stats endpoint is disabled. Use /api/dashboard/overview on api.py.',
    }), 410


if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5050)
