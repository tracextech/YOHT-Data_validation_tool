FROM python:3.9-slim

#setting work directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the Python modules from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8501 (the default port Streamlit runs on)
EXPOSE 8501

# to run your Streamlit app
CMD ["streamlit", "run", "validate.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
