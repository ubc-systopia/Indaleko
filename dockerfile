# Replace "prebuilt-unstructured-image" with the actual name/tag of the pre-built image
FROM downloads.unstructured.io/unstructured-io/unstructured as module-source

FROM python:3.10.13

# Set the working directory (optional if you're okay with the default in the base image)
WORKDIR /app

# Copy the unstructured directory to Python site-packages directly (adjust as necessary)
COPY --from=module-source /unstructured /usr/local/lib/python3.10/site-packages/unstructured


# Copy your Python script into the container
COPY script.py .

# Command to run your Python script
CMD ["python", "./script.py"]