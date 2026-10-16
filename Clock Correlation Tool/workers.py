import json
import traceback
import shutil
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from datetime import datetime, timezone
import pandas as pd

from data_parsing import parse_erp_file, parse_nrt_file, parse_sto_file
from clock_processing import calculate_clock_drift
from misc import SFTP_CONFIG_PATH, get_incremented_clkhst_name
from binary_convert import convert_dis_file, convert_dat_file
from reports import (generate_trending_report, generate_correlation_report,
                     update_html_table, get_correlation_report_title)
from plots import generate_residual_plot

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

            self.log.emit(f"[UI] Connecting to SFTP server {cfg.get('host')}.\n")
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

            self.log.emit(f"[UI] Found latest file: {latest_file}. Downloading.\n")

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

    def __init__(self, erp_file, nrt_files, erp_interpolate, legacy_mode=False, telemetry_df=None):
        super().__init__()
        self.erp_file = erp_file
        self.nrt_files = nrt_files
        self.legacy_mode = legacy_mode
        self.telemetry_df = telemetry_df
        self.erp_interpolate = erp_interpolate

    def run(self):
        try:
            # 1. Parse Ephemeris Data
            erp_df = parse_erp_file(self.erp_file)

            # 2. Parse all NRT paths and concatenate with any pre-sliced telemetry
            nrt_dataframes = []

            if self.telemetry_df is not None:
                print(f"[UI] Passing {len(self.telemetry_df)} sliced STO data points into the correlation engine.")
                nrt_dataframes.append(self.telemetry_df)

            for path in self.nrt_files:
                nrt_dataframes.append(parse_nrt_file(path))

            if not nrt_dataframes:
                raise ValueError("No telemetry data was provided to process.")

            nrt_df = pd.concat(nrt_dataframes, ignore_index=True)

            # 3. Execute Processing Logic using pure DataFrames
            result_df = calculate_clock_drift(erp_df, nrt_df, self.erp_interpolate, legacy_mode=self.legacy_mode)

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


class BatchOutputsWorker(QThread):
    """Background worker for batch output generation without UI freezing."""
    log = pyqtSignal(str)
    finished = pyqtSignal(dict)  # Returns generated metadata like dest_dis/dest_dat
    error = pyqtSignal(str)

    def __init__(self, nrt_df, nrt_files, erp_file, sto_file, out_dir, base_dis=None, base_dat=None, parent=None):
        super().__init__(parent)
        self.nrt_df = nrt_df
        self.nrt_files = nrt_files
        self.erp_file = erp_file
        self.sto_file = sto_file
        self.out_dir = out_dir
        self.base_dis = base_dis
        self.base_dat = base_dat

    def run(self):
        results = {'dest_dis': None, 'dest_dat': None}
        out_path = Path(self.out_dir)

        try:
            # 1. Export Binaries (.dis / .dat)
            if self.base_dis:
                self.log.emit("[Batch] Converting .DIS binary database.")
                dest_dis = (out_path / get_incremented_clkhst_name(self.base_dis)).with_suffix('.dis')
                shutil.copy(self.base_dis, dest_dis)
                convert_dis_file(self.nrt_df, inputdir=str(self.base_dis), outputdir=str(dest_dis))
                results['dest_dis'] = dest_dis
                if ".sftp_cache" in Path(self.base_dis).parts:
                    Path(self.base_dis).unlink(missing_ok=True)
                self.log.emit(f"[Batch] .DIS exported: {dest_dis.name}\n")

            if self.base_dat:
                self.log.emit("[Batch] Converting .DAT binary database.")
                dest_dat = (out_path / get_incremented_clkhst_name(self.base_dat)).with_suffix('.dat')
                shutil.copy(self.base_dat, dest_dat)
                convert_dat_file(self.nrt_df, inputdir=str(self.base_dat), outputdir=str(dest_dat))
                results['dest_dat'] = dest_dat
                if ".sftp_cache" in Path(self.base_dat).parts:
                    Path(self.base_dat).unlink(missing_ok=True)
                self.log.emit(f"[Batch] .DAT exported: {dest_dat.name}\n")

            # 2. Trending Report (.xlsx)
            self.log.emit("[Batch] Generating Trending Report (.xlsx).")
            trend_dir = Path("//noodle/fot/users/rhoover/Clock Tool Development Files")
            trend_file = trend_dir / "Clock Rate Trending (Test).xlsx"
            generate_trending_report(self.nrt_df, trend_file)
            self.log.emit("[Batch] Trending Report generated.\n")

            # 3. Correlation Report (.txt)
            self.log.emit("[Batch] Generating Correlation Report (.txt).")
            filetitle = get_correlation_report_title(self.nrt_df)
            corr_file = out_path / f"{filetitle}.txt"
            generate_correlation_report(
                self.nrt_df, self.nrt_files, self.erp_file, self.sto_file, corr_file.parent
            )
            self.log.emit(f"[Batch] Correlation Report generated: {corr_file.name}\n")

            # 4. Residual Plot (.png)
            self.log.emit("[Batch] Rendering Residual Plot (.png).")
            plot_file = out_path / f"{filetitle}_residuals.png"
            generate_residual_plot(self.nrt_df, plot_file)
            self.log.emit(f"[Batch] Residual Plot saved: {plot_file.name}\n")

            # 5. Master HTML Record Table
            self.log.emit("[Batch] Updating Master HTML Record Table.")
            now = datetime.now(timezone.utc)
            html_dir = Path("//noodle/fot/users/rhoover/Clock Tool Development Files")
            html_file = html_dir / f"Clock_Correlation{now.strftime('%Y')}.htm"
            update_html_table(self.nrt_df, html_file)
            self.log.emit("[Batch] Master HTML Table updated.\n")

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(f"{e}\n{traceback.format_exc()}")
