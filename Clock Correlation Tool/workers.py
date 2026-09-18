import sys
import json
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThread

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

SFTP_CONFIG_PATH = Path.home() / ".ccdm_sftp_config.json"


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

    def __init__(self, remote_dir, file_ext, dest_dir=None):
        super().__init__()
        self.remote_dir = remote_dir
        self.file_ext = file_ext
        self.dest_dir = dest_dir

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

            self.log.emit(f"Connecting to SFTP server {cfg.get('host')}...")
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

            self.log.emit(f"Scanning remote directory: {self.remote_dir}")
            latest_time = 0
            latest_file = None

            for attr in sftp.listdir_attr(self.remote_dir):
                if attr.filename.lower().endswith(self.file_ext.lower()):
                    if attr.st_mtime > latest_time:
                        latest_time = attr.st_mtime
                        latest_file = attr.filename

            if not latest_file:
                raise FileNotFoundError(f"No {self.file_ext} files found in {self.remote_dir}")

            self.log.emit(f"Found latest file: {latest_file}. Downloading...")

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
            self.error.emit(f"SFTP Error: {str(e)}")


class PipelineWorker(QThread):
    """Runs heavy calculations in a background thread to keep the GUI responsive."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, erp_file, nrt_files, legacy_mode=False):
        super().__init__()
        self.erp_file = erp_file
        self.nrt_files = nrt_files
        self.legacy_mode = legacy_mode

    def run(self):
        try:
            from clock_processing import calculate_clock_drift
            nrt_df = calculate_clock_drift(self.erp_file, self.nrt_files, legacy_mode=self.legacy_mode)
            self.finished.emit(nrt_df)
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n{traceback.format_exc()}")
