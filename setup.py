from cx_Freeze import setup, Executable

# Incluir las carpetas 'firmwares' y 'logs'
includefiles = ['SW_ACC','pswd.env']

options = {
    'build_exe': {
        'include_files': includefiles,
        'packages': ['dotenv', 'netmiko'],        
    }
}
setup(
    name="running-config-script",
    version="0.3",
    description="Script para remplazar la configuración de los switches de acceso",
    options=options,
    executables=[Executable("bwd-script.py")],
)