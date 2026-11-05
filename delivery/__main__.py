"""Run the Layer 4 delivery UI/API: python -m delivery"""

import uvicorn


if __name__ == "__main__":
    uvicorn.run("delivery.app:app", host="127.0.0.1", port=8010, reload=False)
