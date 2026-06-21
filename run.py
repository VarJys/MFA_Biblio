from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True activa el recargado automático al guardar archivos
    # Nunca usar debug=True en producción
    app.run(debug=True, host="0.0.0.0", port=5000)