import sys
import subprocess
import os


def generate_ts_files(translations_folder, ui_files, args):
    if not os.path.isdir(translations_folder): return None, None
    for filename in ui_files:
        if not os.path.isfile(filename): return None, None
    exe = ['pylupdate5']
    for filename in ui_files:
        exe.append(filename)
    exe.append('-ts')
    for filename in os.listdir(translations_folder):
        name, ext = os.path.splitext(filename)
        if ext == '.ts':
            exe.append(os.path.join(translations_folder, filename))
    for additional_language in args:
        name, ext = os.path.splitext(additional_language)
        if ext != '.ts':
            additional_language += '.ts'
        exe.append(os.path.join(translations_folder, additional_language))
    pylupdate = subprocess.Popen(exe)
    output, error = pylupdate.communicate()
    return output, error


def generate_qm_files(translations_folder):
    if not os.path.isdir(translations_folder): return None, None
    exe = ['lrelease']
    for filename in os.listdir(translations_folder):
        name, ext = os.path.splitext(filename)
        if ext == '.ts':
            exe.append(os.path.join(translations_folder, filename))
    lrelease = subprocess.Popen(exe)
    output, error = lrelease.communicate()
    return output, error


if __name__ == '__main__':
    translations_folder = os.path.join('.', 'languages')
    ui_files = ['InteractiveConeBeamReconstruction_GUI.py', 'InteractiveConeBeamReconstruction.pyw', 'GraphicsView.py']
    additional_languages = sys.argv[1:]
    generate_ts_files(translations_folder, ui_files, additional_languages)
    generate_qm_files(translations_folder)
