from app import create_app

application = create_app()

app_options = {
    'use_reloader': True,
    'use_debugger': True,
    'host': '0.0.0.0',
    'port': 5000
}

if __name__ == '__main__':
    application.run(**app_options)
