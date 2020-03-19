from src import app
from src import background_task
import src.background
if __name__ == "__main__":
    # app = create_app(debug=True)
    app.run(host='0.0.0.0', port=5000)
