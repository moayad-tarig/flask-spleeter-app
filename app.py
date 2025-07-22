from flask import Flask, request, jsonify
import os
from spleeter.separator import Separator

app = Flask(__name__)

@app.route('/separate', methods=['POST'])
def separate():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = file.filename
    input_path = os.path.join('tmp', filename)
    os.makedirs('tmp', exist_ok=True)
    file.save(input_path)

    try:
        # output_dir = os.path.join('tmp', filename.split('.')[0])
        output_subdir = os.path.splitext(filename)[0]
        output_path = os.path.join('tmp', output_subdir)
        separator = Separator('spleeter:2stems')
        separator.separate_to_file(input_path, 'tmp')
        return jsonify({"message": "Separation successful", "output_dir": output_path}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
