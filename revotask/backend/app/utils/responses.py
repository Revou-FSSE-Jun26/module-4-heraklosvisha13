from flask import jsonify


def success_response(data, status: int = 200):
    """Success envelope: {"data": ...}."""
    return jsonify({"data": data}), status


def error_response(message: str, status: int):
    """Failure envelope: flat {"error": "<message>"}."""
    return jsonify({"error": str(message)}), status
