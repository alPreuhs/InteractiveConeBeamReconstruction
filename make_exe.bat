:: make sure to activate the virtual environment if using Anaconda

:: SET spec=pyinstaller_onefile.spec :: output everything into one exe file
SET spec=pyinstaller_onedir.spec :: output everything into a folder with exe and DLLs

pyinstaller %spec%