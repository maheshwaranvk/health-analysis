"""Run the Streamlit frontend."""

import subprocess
import sys

if __name__ == "__main__":
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "streamlit_app/app.py"],
        check=True,
    )
