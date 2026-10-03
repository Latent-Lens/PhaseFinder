@echo off
setlocal
rem Headless FJ Commandline driver for the FlowJo comparison sweep.
rem See flowjo_sweep_RUNBOOK.md, step 5, for the one-time GUI setup this
rem depends on (flowjo_sweep_template.wsp must already exist with the 3 gate
rem variants x 3 Cell Cycle model configs and a Table Editor table marked for
rem command-line batch export).
rem
rem Reference: https://flowjo.com/docs/flowjo10/advanced-features/fj-commandline
rem   First argument must be one of: .wspt / .wsp / .acs / .txt (sample list).
rem   -save        saves the workspace after processing (recomputed gates/stats).
rem   -batchTable  exports Table Editor tables using their assigned settings.
rem   -outputFolder destination for the exported table(s).
rem   -verbose     prints extended execution details (useful for diagnosing a
rem                config that doesn't behave as expected -- FJ Commandline's
rem                own docs are thin on -batchTable's exact requirements).
rem
rem EDIT THESE FOUR PATHS for your machine, then run this file.
rem FLOWJO_EXE still needs the real FlowJo 11.2 install path (vXX below is a
rem placeholder). WORKSPACE/OUTPUT_FOLDER default to sit next to the 30 FCS
rem files already at DATA_FOLDER -- save flowjo_sweep_template.wsp there in
rem step 8 of the runbook, or edit these to wherever you actually save it.
set FLOWJO_EXE=C:\Program Files\FlowJo vXX\FlowJo64.exe
set DATA_FOLDER=C:\Users\lapt3u\Downloads\archivedwl-864
set WORKSPACE=%DATA_FOLDER%\flowjo_sweep_template.wsp
set OUTPUT_FOLDER=%DATA_FOLDER%\exports

if not exist "%FLOWJO_EXE%" (
    echo ERROR: FLOWJO_EXE not found: %FLOWJO_EXE%
    echo Edit the path at the top of this file to match your FlowJo install.
    exit /b 1
)
if not exist "%WORKSPACE%" (
    echo ERROR: WORKSPACE not found: %WORKSPACE%
    echo Complete flowjo_sweep_RUNBOOK.md steps 1-4 first, saving to this path.
    exit /b 1
)

if not exist "%OUTPUT_FOLDER%" mkdir "%OUTPUT_FOLDER%"

echo Running FlowJo headlessly against %DATA_FOLDER% ...
"%FLOWJO_EXE%" "%WORKSPACE%" "%DATA_FOLDER%" -save "%OUTPUT_FOLDER%\flowjo_sweep_output.wsp" -batchTable -outputFolder "%OUTPUT_FOLDER%" -verbose

if errorlevel 1 (
    echo FlowJo exited with an error. Check %OUTPUT_FOLDER% for partial output and rerun with -verbose output above for detail.
    exit /b 1
)

echo Done. Exported table(s) should be in %OUTPUT_FOLDER%.
echo Next: copy %OUTPUT_FOLDER% back to the Linux dev box and run
echo   python3 tests/validation/driving_code/flowjo_sweep_parse_export.py --exports-dir ^<path^>
endlocal
