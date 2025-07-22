# Use the official Anaconda3 image as the base
FROM continuumio/anaconda3:latest



COPY requirements.txt /app/
WORKDIR /app
COPY . /app

# Install system dependencies required by Spleeter (ffmpeg for audio processing, libsndfile1 for sound files)
# These are common dependencies for audio processing libraries like Spleeter.
RUN apt-get update && \
    apt-get install -y ffmpeg libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

# Create a Conda environment named 'spleeter-env' with Python 3.7.
# Python 3.7 is chosen because it's compatible with tensorflow==1.15.2,
# which Spleeter often relies on.
RUN conda create -n work-env python=3.7 -y

SHELL ["conda", "run", "--no-capture-output", "-n", "work-env", "/bin/bash", "-c"]

RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from spleeter.separator import Separator; Separator('spleeter:2stems')"
RUN mkdir -p /app/tmp && chmod 755 /app/tmp
COPY . /app

# Expose port 5000, which is the default port for the Flask development server.
EXPOSE 5000

# Define the command to run the Flask application when the container starts.
# 'conda run -n spleeter-env' ensures that Flask and its dependencies
# are executed from within the 'spleeter-env' environment.

ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "work-env", "python3", "app.py"]

