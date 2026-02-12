@echo off
echo ================================================================================
echo GENETIC PARAMETER OPTIMIZER - LAZORA VERFAHREN
echo ================================================================================
echo.
echo Starting parameter optimization for all 96 indicators...
echo This will take approximately 2-3 hours.
echo.
echo Press Ctrl+C to cancel, or any other key to continue...
pause

C:\Users\nikol\CascadeProjects\Superindikator_Alpha\Alpha_Superindikator\Scripts\python.exe GENETIC_PARAMETER_OPTIMIZER.py

echo.
echo ================================================================================
echo OPTIMIZATION COMPLETE!
echo ================================================================================
echo.
echo Check Parameter_Configs folder for optimized configurations.
echo.
pause
