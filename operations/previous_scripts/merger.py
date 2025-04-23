from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
from mainp import app as app1
from addp import app as app2

# Create a dispatcher middleware.
# The first argument is the WSGI app for the default path ("/").
# Then we mount additional apps under sub-paths.
application = DispatcherMiddleware(app1.server, {
    '/app2': app2.server,  # Access app2 at http://localhost:8050/app2
})

if __name__ == '__main__':
    # Run the combined WSGI app on port 8050.
    run_simple('0.0.0.0', 8050, application, use_reloader=True, use_debugger=True)
