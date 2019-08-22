@echo off
set args=
:start
if [%1] == [] goto done
set args=%args% %1
shift
goto start

:done

python tsmc180_main.py %args% | findstr /v "warning: vin: no DC value, ..."
