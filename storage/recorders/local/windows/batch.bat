set command=python recorder.py --performance_db --performance_file --arangoimport --inputfile

for /F "delims=" %%f in (%1) do (
    echo %command% %%f
    %command% %%f
)
