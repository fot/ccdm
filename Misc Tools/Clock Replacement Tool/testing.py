from pathlib import Path
from clock_processing import (
    calculate_clock_drift, generate_trending_report,
    generate_residual_plot)
from results_report import generate_correlation_report

erp_base_path= Path("//noodle/fot/engineering/ccdm/Clock_Timing/ERPFiles")
nrt_base_path= Path("//noodle/fot/engineering/ccdm/Clock_Timing/NRTFiles")
output_path= Path("C:/Users/RHoover/Desktop")

erp_path= erp_base_path / "DE26145.erp"
nrt_paths= [
    nrt_base_path / "rclk_26_138_10_6.nrt", nrt_base_path / "rclk_26_139_10_6.nrt",
    nrt_base_path / "rclk_26_140_12_6.nrt", nrt_base_path / "rclk_26_141_10_6.nrt",
    nrt_base_path / "rclk_26_142_10_6.nrt", nrt_base_path / "rclk_26_143_11_6.nrt",
    nrt_base_path / "rclk_26_144_11_6.nrt", nrt_base_path / "rclk_26_145_16_6.nrt",
    nrt_base_path / "rclk_26_146_10_6.nrt", nrt_base_path / "rclk_26_147_11_6.nrt",
    nrt_base_path / "rclk_26_148_10_6.nrt", nrt_base_path / "rclk_26_149_14_6.nrt",
    nrt_base_path / "rclk_26_150_10_6.nrt", nrt_base_path / "rclk_26_151_10_6.nrt",
    nrt_base_path / "rclk_26_152_13_6.nrt"]

results_df= calculate_clock_drift(erp_path, nrt_paths)
generate_correlation_report(results_df, nrt_paths, erp_path, f"{output_path}/correlation_results.txt")
# generate_trending_report(results_df, f"{output_path}/clock_rate_new.txt")
# generate_residual_plot(results_df, f"{output_path}/residuals.html")

results_df.to_csv(f"{output_path}/results_df.csv", index=False)
