python -m venv .venv
.venv\Scripts\activate.bat
set PYTHONPATH=.venv/Lib/site-packages
set PATH=D:\PrgCommissionati\opencheat\.venv\Scripts
set PATH=.venv\Scripts
pip3 install -r requirements.txt
pyinstaller --paths .venv/Lib/site-packages --add-data ".venv/Lib/site-packages/mem_edit/VERSION;mem_edit" --onefile --noconfirm --noconsole --clean --log-level=WARN opencheat.py
pyinstaller --paths .venv/Lib/site-packages --add-data ".venv/Lib/site-packages/mem_edit/VERSION;mem_edit" --clean --debug=all opencheat.py
pyinstaller --paths .venv/Lib/site-packages --add-data ".venv/Lib/site-packages/mem_edit/VERSION;mem_edit" --onefile --clean --debug=all opencheat.py