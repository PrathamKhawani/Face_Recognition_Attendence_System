# Use a full Python image which has pre-installed build tools (gcc, make, etc.)
FROM python:3.10

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
# Limit compiler memory usage to prevent Out Of Memory (OOM) crashes on Hugging Face
ENV CMAKE_BUILD_PARALLEL_LEVEL=1
ENV MAKEFLAGS="-j1"

# Install OpenCV and GUI rendering system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Initialize required directories and grant open read/write permissions for runtime safety
RUN mkdir -p instance ImagesAttendance && chmod -R 777 instance ImagesAttendance

# Expose the port (Hugging Face Spaces expects 7860)
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]