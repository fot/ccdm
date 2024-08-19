@REM @echo off
ssh -T rhoover@131.142.113.13 /proj/sot/ska3/flight/bin/python /home/rhoover/python/Code/ccdm/AC\ Bias/"ac_bias_hit_persistent.py"
pause
python auto_open.py
pause
exit /b
