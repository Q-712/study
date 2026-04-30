import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import app as flask_app
    print("Server will run on http://127.0.0.1:8080")
    flask_app.app.run(host='127.0.0.1', port=8080, debug=False, use_reloader=False)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()