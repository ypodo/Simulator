# Use Python 3.9 slim image for a smaller container size
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy the Python files
COPY hardware_simulator.py multi_pump_controller.py ./

# Install required packages (minimal for this simulation)
RUN pip install --no-cache-dir pytest pytest-cov

# Set Python to run in unbuffered mode for better logging in containers
ENV PYTHONUNBUFFERED=1

# Command to run when container starts
# Default to running the example simulation
CMD ["python", "hardware_simulator.py"]