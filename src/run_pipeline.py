import subprocess
import sys

pipeline_steps = ["src/extract.py", "src/clean.py", "src/load.py"]

for step_script in pipeline_steps:
    print(f"Running {step_script}...")
    step_result = subprocess.run([sys.executable, step_script])
    if step_result.returncode != 0:
        print(f"Stopped: {step_script} failed.")
        sys.exit(1)

print("Pipeline finished successfully.")