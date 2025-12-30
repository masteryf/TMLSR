import uvicorn
import os
import sys

# Ensure the project root is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Starting TMLSR Server...")
    # Run the server
    # host 0.0.0.0 to be accessible
    # port 6008 default
    uvicorn.run("server.main:app", host="0.0.0.0", port=6008, reload=True)
