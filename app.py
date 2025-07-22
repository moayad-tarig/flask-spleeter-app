import os
import uuid
import boto3
from flask import Flask, request, jsonify
from spleeter.separator import Separator
from dotenv import load_dotenv
import logging
import shutil
import threading

# Configuration
load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# AWS Setup
S3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('S3_REGION'),
    config=boto3.session.Config(connect_timeout=30, read_timeout=30)  # Timeouts
)
BUCKET = os.getenv('S3_BUCKET_NAME')

def async_cleanup(path):
    """Background file cleanup"""
    try:
        shutil.rmtree(path)
        logging.info(f"Cleaned up {path}")
    except Exception as e:
        logging.warning(f"Cleanup failed for {path}: {str(e)}")

@app.route('/separate', methods=['POST'])
def process_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if not file or not file.filename:
        return jsonify({"error": "Invalid file"}), 400

    # Setup workspace
    job_id = uuid.uuid4().hex
    temp_dir = f"tmp_{job_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 1. Save input
        input_path = os.path.join(temp_dir, file.filename)
        file.save(input_path)

        # 2. Process audio
        separator = Separator('spleeter:2stems')
        output_dir = os.path.join(temp_dir, 'output')
        separator.separate_to_file(input_path, temp_dir)

        # 3. Upload results
        base_name = os.path.splitext(file.filename)[0]
        stems = []
        
        for stem in ['vocals', 'accompaniment']:
            filename = f"{stem}.wav"
            local_path = os.path.join(temp_dir, base_name, filename)
            s3_path = f"outputs/{job_id}/{filename}"
            
            if not os.path.exists(local_path):
                logging.error(f"Missing stem file: {local_path}")
                continue
                
            try:
                S3.upload_file(local_path, BUCKET, s3_path)
                stems.append({
                    "stem": stem,
                    "url": f"https://{BUCKET}.s3.amazonaws.com/{s3_path}"
                })
            except Exception as upload_error:
                logging.error(f"Upload failed for {stem}: {str(upload_error)}")
                continue

        if not stems:
            return jsonify({"error": "No stems generated"}), 500

        return jsonify({
            "success": True,
            "job_id": job_id,
            "stems": stems
        })

    except Exception as e:
        logging.error(f"Processing failed: {str(e)}", exc_info=True)
        return jsonify({"error": "Processing failed", "details": str(e)}), 500

    finally:
        # Start cleanup in background
        threading.Thread(target=async_cleanup, args=(temp_dir,)).start()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5050, threaded=False)