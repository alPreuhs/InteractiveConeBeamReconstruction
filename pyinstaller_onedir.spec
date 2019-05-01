# -*- mode: python -*-

curr_dir = os.getcwd() #os.path.dirname(os.path.realpath(__file__))
import os
if not os.path.isdir('pyconrad'):
    os.makedirs('pyconrad')

# need to add pyconrad folder so we need a dummy file inside
with open(curr_dir + '/pyconrad/deleteMe.txt', 'w') as deleteMe:
    deleteMe.write('Dummy file...\n')
	
added_files = [
    (curr_dir + '/dependency/*.py', 'dependency'),
	(curr_dir + '/include/*', 'include'),
	(curr_dir + '/icons/*', 'icons'),
	(curr_dir + '/languages/*', 'languages'),
	(curr_dir + '/Math/*.py', 'Math'),
	(curr_dir + '/threads/*.py', 'threads'),
	(curr_dir + '/*.npy', '.'),
	(curr_dir + '/pyconrad/deleteMe.txt', 'pyconrad')
]

block_cipher = None

a = Analysis(['InteractiveConeBeamReconstruction.pyw'],
             pathex=['C:\\Users\\Jonas\\Git\\InteractiveConeBeamReconstruction'],
             binaries=[],
             datas=added_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='InteractiveConeBeamReconstruction',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='InteractiveConeBeamReconstruction')
