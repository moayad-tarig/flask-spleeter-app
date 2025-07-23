from flask import Flask, request, jsonify
import os
import uuid
import boto3
from dotenv import load_dotenv
from spleeter.separator import Separator
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('us-east-1')
)
BUCKET_NAME = os.getenv('AWS_S3_BUCKET')

@app.route('/separate', methods=['POST'])
def handle_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    # Create unique workspace
    job_id = uuid.uuid4().hex
    temp_dir = f"tmp_{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # 1. Save uploaded file (with sanitized filename)
        original_filename = str(file.filename)  # Ensure string type
        input_path = os.path.join(temp_dir, original_filename)
        file.save(input_path)

        # 2. Process with Spleeter
        separator = Separator('spleeter:2stems')
        output_dir = os.path.join(temp_dir, 'output')
        separator.separate_to_file(input_path, temp_dir)

        # 3. Prepare S3 upload
        stems = []
        base_name = os.path.splitext(original_filename)[0]
        output_folder = os.path.join(temp_dir, base_name)

        for stem_file in ['vocals.wav', 'accompaniment.wav']:
            local_path = os.path.join(output_folder, stem_file)
            s3_key = f"outputs/{job_id}/{stem_file}"

            # Verify file exists before upload
            if os.path.exists(local_path):
                s3.upload_file(local_path, BUCKET_NAME, s3_key)
                stems.append({
                    "stem": stem_file.replace('.wav', ''),
                    "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                })
            else:
                logger.warning(f"Missing stem file: {local_path}")

        return jsonify({
            "success": True,
            "stems": stems,
            "job_id": job_id
        })

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Processing failed",
            "details": str(e)
        }), 500

    finally:
        # Cleanup temp files
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5050)