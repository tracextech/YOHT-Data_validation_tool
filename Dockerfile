FROM python:3.9-slim

# Setting work directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the Python modules from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install additional packages listed in apt.txt
RUN apt-get update && \
    xargs apt-get install -y < apt.txt

# Expose ports for both Streamlit and FastAPI
EXPOSE 8501 3000

# Command to run both Streamlit and FastAPI
CMD ["bash", "-c", "uvicorn validate:app --host 0.0.0.0 --port 3000 & streamlit run validate.py --server.port=8501 --server.enableCORS=false --server.enableXsrfProtection=false"]
