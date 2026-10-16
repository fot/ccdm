import json
import subprocess
from pathlib import Path

from misc import get_bundled_path

# Local variables for configuration
SVN_CONFIG_PATH  = Path.home() / ".clockapp_svn_config.json"

# Update this path to the actual SVN working copy where refdata.txt is located.
SVN_FILE_TARGET = Path(r"//noodle/fot/users/rhoover/Clock Tool Development Files/MAUDE_refdata_update/MAUDE_refdata/refdata.txt")
# SVN_FILE_TARGET = Path(r"//noodle/fot/engineering/ccdm/Clock_Timing/MAUDE_refdata_update/MAUDE_refdata/refdata.txt")


def commit_refdata(commit_message):
    """
    Commits the refdata.txt file to SVN using credentials from a local JSON config.
    Raises exceptions on failure so the GUI dialog can safely display the error.
    """
    # 1. Check for the credentials file
    if not SVN_CONFIG_PATH.exists():
        template = {
            "username": "your_username",
            "password": "your_password"
        }
        with open(SVN_CONFIG_PATH, 'w') as f:
            json.dump(template, f, indent=4)
        
        raise FileNotFoundError(
            f"SVN config not found. A template was created at {SVN_CONFIG_PATH}. "
            "Please add your credentials to this file and try again."
        )

    # 2. Load the credentials
    with open(SVN_CONFIG_PATH, 'r') as f:
        try:
            cfg = json.load(f)
            username = cfg['username']
            password = cfg['password']
        except KeyError:
            raise ValueError(
                f"SVN config at {SVN_CONFIG_PATH} is missing 'username' or 'password' keys."
            )

    # 3. Verify the target file exists before attempting to commit
    if not SVN_FILE_TARGET.exists():
        raise FileNotFoundError(f"Target file for SVN commit does not exist: {SVN_FILE_TARGET}")

    # 4. Construct the SVN commit command
    svn_executable = get_bundled_path("svn-tools/bin/svn.exe")

    cmd = [
        svn_executable, "commit", str(SVN_FILE_TARGET),
        "-m", commit_message,
        "--username", username,
        "--password", password,
        "--non-interactive",
        "--no-auth-cache"  # Prevents SVN from globally caching the JSON credentials
    ]

    # 5. Execute the command
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        # If SVN fails (e.g., authentication error, file out of date), it writes to stderr
        error_message = e.stderr.strip() if e.stderr else e.stdout.strip()
        raise RuntimeError(f"SVN Command Failed:\n{error_message}")
    except FileNotFoundError:
        # This catches cases where the 'svn' command-line tool is not installed or not in the system PATH
        raise FileNotFoundError(
            "SVN executable not found. Ensure SVN is installed and added to your system PATH."
        )
