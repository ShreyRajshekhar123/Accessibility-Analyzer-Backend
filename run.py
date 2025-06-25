import uvicorn
import os

# Set environment variables for development here if needed
# For example, if you have a default local environment for certain services.
# os.environ["MY_ENV_VAR"] = "development_value"

if __name__ == "__main__":
    # Ensure the current working directory is the 'backend' folder
    # so that uvicorn can find 'app.main:app'
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)