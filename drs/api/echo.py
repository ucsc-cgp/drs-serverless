from flask import Flask, jsonify, request

def post(message):
    return jsonify({'the message': message})
