# Use official Python slim image (adjust version if needed)
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Copy only the source code for now
COPY . .

# Set default command (Lambda expects the handler to be set in CDK)
CMD ["app.handler"]
