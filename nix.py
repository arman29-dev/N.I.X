import uvicorn


if __name__ == "__main__":
    reload_dirs = ["app", "templates", "static"]

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=reload_dirs,
    )
