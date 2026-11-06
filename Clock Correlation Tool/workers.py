import json
import traceback
import shutil
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from datetime import datetime, timedelta, timezone
import pandas as pd

from data_parsing import parse_erp_file, parse_nrt_file, parse_sto_file
from clock_processing import calculate_clock_drift
from misc import SFTP_CONFIG_PATH, get_incremented_clkhst_name
from binary_convert import convert_dis_file, convert_dat_file
from reports import (generate_trending_report, generate_correlation_report,
                     update_html_table, get_correlation_report_title)
from plots import generate_residual_plot
from maude_query import get_data

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
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, file_paths, parent=None):
        super().__init__(parent)
        if isinstance(file_paths, (str, Path)):
            self.file_paths = [file_paths]
        else:
            self.file_paths = list(file_paths)
        self._is_canceled = False

    def cancel(self):
        self._is_canceled = True

    def filter_dataframe(self, df):
        """Truncate data to at most the most current 15-day window, bounded from 08:00 to 08:00."""
        if df.empty or 'datetime' not in df.columns:
            return df

        # 1. Get temporal extent of combined dataset
        min_dt = df['datetime'].min()
        max_dt = df['datetime'].max()

        # 2. Determine the most recent complete 08:00 end boundary
        end_base = max_dt.replace(hour=8, minute=0, second=0, microsecond=0)
        if max_dt < end_base:
            filter_end = end_base - timedelta(days=1)
        else:
            filter_end = end_base

        # 3. Target 15 days back from the latest 08:00 mark
        target_start = filter_end - timedelta(days=16)  # 16 days to include the full 15-day window

        # 4. If total dataset is shorter than 15 days, fall back to earliest 08:00
        earliest_base = min_dt.replace(hour=8, minute=0, second=0, microsecond=0)
        if min_dt > earliest_base:
            earliest_08 = earliest_base + timedelta(days=1)
        else:
            earliest_08 = earliest_base

        filter_start = max(target_start, earliest_08)

        # 5. Guard check: verify non-zero window
        if filter_start >= filter_end:
            msg = f"[WARNING] No valid 08:00-to-08:00 window available between {min_dt} and {max_dt}."
            self.status.emit(msg)
            print(msg)
            return pd.DataFrame(columns=df.columns)

        # 6. Apply filter
        df_filtered = df[(df['datetime'] >= filter_start) & (df['datetime'] <= filter_end)].copy()
        df_filtered = df_filtered.reset_index(drop=True)

        days_spanned = (filter_end - filter_start).days
        msg = (f"Truncated STO data to the most current {days_spanned}-day window "
               f"({filter_start.strftime('%Y:%j:%H:%M')} to {filter_end.strftime('%Y:%j:%H:%M')}). "
               f"{len(df_filtered)} entries remain.")
        self.status.emit(msg)
        print(f"[UI] {msg}")

        return df_filtered

    def run(self):
        try:
            parsed_dfs = []
            num_files = len(self.file_paths)

            for idx, fpath in enumerate(self.file_paths):
                if self._is_canceled:
                    self.error.emit("STO parsing canceled by user.")
                    return

                fname = Path(fpath).name
                self.status.emit(f"Loading file {idx + 1} of {num_files}: {fname}")

                start_pct = int((idx / num_files) * 100)
                self.progress.emit(start_pct)

                def file_progress_cb(file_pct):
                    overall_pct = int(((idx + (file_pct / 100.0)) / num_files) * 100)
                    self.progress.emit(overall_pct)

                try:
                    df = parse_sto_file(fpath, progress_callback=file_progress_cb)
                except TypeError:
                    df = parse_sto_file(fpath)

                if df is not None and not df.empty:
                    parsed_dfs.append(df)

                end_pct = int(((idx + 1) / num_files) * 100)
                self.progress.emit(end_pct)

            if not parsed_dfs:
                self.finished.emit(pd.DataFrame())
                return

            # Merge all parsed dataframes
            combined_df = pd.concat(parsed_dfs, ignore_index=True)

            if 'vcdu' in combined_df.columns:
                combined_df = combined_df.sort_values(by='vcdu')
                combined_df = combined_df.drop_duplicates(subset=['vcdu'])
                combined_df = combined_df.reset_index(drop=True)

            # Filter to clean 08:00 to 08:00 time ranges
            if len(combined_df) > 0:
                combined_df = self.filter_dataframe(combined_df)

            self.finished.emit(combined_df)

        except Exception as e:
            self.error.emit(f"{e}\n{traceback.format_exc()}")


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


class ExportCSVWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, df, file_path, parent=None):
        super().__init__(parent)
        self.df = df
        self.file_path = file_path
        self._is_canceled = False

    def cancel(self):
        self._is_canceled = True

    def run(self):
        try:
            total_rows = len(self.df)
            if total_rows == 0:
                self.df.to_csv(self.file_path, index=False)
                self.progress.emit(100)
                self.finished.emit(self.file_path)
                return

            # Divide dataframe into ~100 chunks for smooth progress updates
            chunk_size = max(1, total_rows // 100)

            for i in range(0, total_rows, chunk_size):
                if self._is_canceled:
                    self.error.emit("Export canceled by user.")
                    return

                chunk = self.df.iloc[i : i + chunk_size]

                # Write header only on the first chunk; append the rest
                mode = 'w' if i == 0 else 'a'
                header = True if i == 0 else False

                chunk.to_csv(self.file_path, mode=mode, header=header, index=False)

                # Calculate and emit completion percentage
                pct = int(((i + len(chunk)) / total_rows) * 100)
                self.progress.emit(pct)

            self.finished.emit(self.file_path)

        except Exception as e:
            self.error.emit(f"{e}\n{traceback.format_exc()}")


class MaudeQueryWorker(QThread):
    """Background thread to handle synchronous urllib requests without freezing the GUI."""
    status = pyqtSignal(str)
    finished = pyqtSignal(object)  # Emits a SINGLE merged pd.DataFrame (STO Compatible)
    error = pyqtSignal(str)

    def __init__(self, start_dt, end_dt, parent=None):
        super().__init__(parent)
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.msids = ["CCSDSVCD", "SFDU_BYTE043X", "SFDU_BYTE045X",
                      "SFDU_BYTE049X", "SDFU_BYTE087X", "CIUMBITR","SFDU_BYTE067"]
        self._is_canceled = False

    def cancel(self):
        self._is_canceled = True

    def run(self):
        try:
            self.status.emit(f"Initiating MAUDE fetch for {len(self.msids)} MSIDs...")

            # Execute the synchronous urllib fetch loop which now returns the unified DataFrame
            merged_df = get_data(self.start_dt, self.end_dt, self.msids)

            if self._is_canceled:
                self.error.emit("MAUDE query canceled by user.")
                return

            self.status.emit("MAUDE Data successfully retrieved.")
            self.finished.emit(merged_df)

        except Exception as e:
            self.error.emit(f"Failed to fetch MAUDE data:\n{e}\n{traceback.format_exc()}")
