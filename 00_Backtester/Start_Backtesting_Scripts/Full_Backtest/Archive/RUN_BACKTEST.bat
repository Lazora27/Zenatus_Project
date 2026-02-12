@echo off
echo ================================================================================
echo PRODUCTION BACKTEST - ADAPTIVE PARAMETERS
echo ================================================================================
echo.
echo Starting backtest with individually optimized parameters...
echo This will take approximately 15-20 minutes.
echo.
echo Press Ctrl+C to cancel, or any other key to continue...
pause

C:\Users\nikol\CascadeProjects\Superindikator_Alpha\Alpha_Superindikator\Scripts\python.exe PRODUCTION_1H_ADAPTIVE.py

echo.
echo ================================================================================
echo BACKTEST COMPLETE!
echo ================================================================================
echo.
echo Check Documentation/Fixed_Exit/1h/ for results.
echo.
pause
