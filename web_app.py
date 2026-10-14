"""Flask Web 入口：python web_app.py；CLI 入口保持独立。"""

import os

from venue_app.web import create_app


if __name__ == "__main__":
    app = create_app(data_dir=os.environ.get("VENUE_DATA_DIR"))
    app.run(host="127.0.0.1", port=5000, debug=False)
