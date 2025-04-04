# Use an official Python runtime as a base image
FROM python:3.11

# Set the working directory
WORKDIR /app

# Copy project files to the container
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port 8000 for Django
EXPOSE 8000

# Start the Django app
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "sopchatbot.wsgi:application"]
