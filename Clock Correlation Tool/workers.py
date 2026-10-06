import json
import traceback
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import pandas as pd

from data_parsing import parse_sto_file
from misc import SFTP_CONFIG_PATH

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

class ConsoleStream(QObject):
    """Intercepts sys.stdout for real-time GUI console updates."""
    text_written = pyqtSignal(str)

    def write(self, text):
        self.text_written.emit(str(text))

    def flush(self):
        pass


class SFTPWorker(QThread):
    """Generic background worker to fetch the newest file from an SFTP directory."""
    finished = pyqtSignal(str) 
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, remote_dir, file_ext, dest_dir=None, file_prefix=None):
        super().__init__()
        self.remote_dir = remote_dir
        self.file_ext = file_ext
        self.dest_dir = dest_dir
        self.file_prefix = file_prefix

    def run(self):
        if not PARAMIKO_AVAILABLE:
            self.error.emit("The 'paramiko' library is missing. Run 'pip install paramiko' to use SFTP features.")
            return

        if not SFTP_CONFIG_PATH.exists():
            self.error.emit("SFTP Config not found. Please set credentials in Settings -> SFTP Configuration.")
            return

        try:
            with open(SFTP_CONFIG_PATH, 'r') as f:
                cfg = json.load(f)

            self.log.emit(f"[UI] Connecting to SFTP server {cfg.get('host')}...\n")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": cfg.get('host'),
                "port": int(cfg.get('port', 22)),
                "username": cfg.get('user'),
                "timeout": 10
            }
            if cfg.get('password'):
                connect_kwargs["password"] = cfg.get('password')

            ssh.connect(**connect_kwargs)
            sftp = ssh.open_sftp()

            self.log.emit(f"[UI] Scanning remote directory: {self.remote_dir}\n")
            latest_time = 0
            latest_file = None

            for attr in sftp.listdir_attr(self.remote_dir):
                filename_lower = attr.filename.lower()

                # Check extension
                if filename_lower.endswith(self.file_ext.lower()):

                    # Check prefix if one was provided
                    if self.file_prefix and not filename_lower.startswith(self.file_prefix.lower()):
                        continue 

                    # Find the newest matching file
                    if attr.st_mtime > latest_time:
                        latest_time = attr.st_mtime
                        latest_file = attr.filename

            if not latest_file:
                raise FileNotFoundError(f"[UI] No {self.file_ext} files matching criteria found in {self.remote_dir}\n")

            self.log.emit(f"[UI] Found latest file: {latest_file}. Downloading...\n")

            if self.dest_dir:
                cache_dir = Path(self.dest_dir)
            else:
                cache_dir = Path.home() / ".sftp_cache"

            cache_dir.mkdir(parents=True, exist_ok=True)
            local_path = cache_dir / latest_file

            sftp.get(f"{self.remote_dir}/{latest_file}", str(local_path))

            sftp.close()
            ssh.close()

            self.finished.emit(str(local_path))
        except Exception as e:
            self.error.emit(f"SFTP Error: {e}\n{traceback.format_exc()}")


class PipelineWorker(QThread):
    """Runs heavy calculations in a background thread to keep the GUI responsive."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, erp_file, nrt_files, legacy_mode=False, telemetry_df=None):
        super().__init__()
        self.erp_file = erp_file
        self.nrt_files = nrt_files
        self.legacy_mode = legacy_mode
        self.telemetry_df = telemetry_df

    def run(self):
        try:
            from data_parsing import parse_erp_file, parse_nrt_file
            from clock_processing import calculate_clock_drift

            # 1. Parse Ephemeris Data
            erp_df = parse_erp_file(self.erp_file)

            # 2. Parse all NRT paths and concatenate with any pre-sliced telemetry
            nrt_dataframes = []

            if self.telemetry_df is not None:
                nrt_dataframes.append(self.telemetry_df)

            for path in self.nrt_files:
                nrt_dataframes.append(parse_nrt_file(path))

            if not nrt_dataframes:
                raise ValueError("No telemetry data was provided to process.")

            nrt_df = pd.concat(nrt_dataframes, ignore_index=True)

            # 3. Execute Processing Logic using pure DataFrames
            result_df = calculate_clock_drift(erp_df, nrt_df, legacy_mode=self.legacy_mode)

            self.finished.emit(result_df)

        except Exception as e:
            self.error.emit(f"{str(e)}\n{traceback.format_exc()}")


class StoParserWorker(QThread):
    """Background worker to parse massive STO files without freezing the main GUI."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)  # Emits the parsed DataFrame
    error = pyqtSignal(str)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self._is_cancelled = False

    def cancel(self):
        """Flag the loop to abort on the next iteration."""
        self._is_cancelled = True

    def run(self):
        try:
            # Pass our local update method as the callback to the parser
            df = parse_sto_file(self.filepath, progress_callback=self.update_progress)

            # Only emit finished if it completed naturally
            if not self._is_cancelled:
                self.finished.emit(df)

        except Exception as e:
            self.error.emit(f"{str(e)}\n{traceback.format_exc()}")

    def update_progress(self, val):
        """Emits the progress back to the main thread. Returns False to abort if cancelled."""
        if self._is_cancelled:
            return False
        self.progress.emit(val)
        return True
