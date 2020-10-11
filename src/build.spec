# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['opencheat.py'],
             pathex=['.venv/Lib/site-packages', 'D:\\PrgCommissionati\\opencheat'],
             binaries=[],
             datas=[('.venv/Lib/site-packages/mem_edit/VERSION', 'mem_edit')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=True)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [('v', None, 'OPTION')],
          exclude_binaries=True,
          name='opencheat',
          debug=True,
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
               upx_exclude=[],
               name='opencheat')
