import os

from livereload import Server, shell

if __name__ == "__main__":
    if not os.path.exists("_build"):
        print('Initial build using "make html"')
        shell("make html")()
    server = Server()
    server.watch("*.rst", shell("make html"), delay=1)
    server.watch("*.md", shell("make html"), delay=1)
    server.watch("*.py", shell("make html"), delay=1)
    server.watch("images/*", shell("make html"), delay=1)
    server.serve(root="_build/html")
