import os
import time
import subprocess
import threading
from pyngrok import ngrok
import qrcode
from config import PORT

def start_flask():
    """Start the Flask app via subprocess."""
    print("[*] Starting OptiGreeks Web Server...")
    # Add an environment variable so server.py knows it's tunneled and maybe run silently
    env = os.environ.copy()
    subprocess.Popen(["python", "server.py"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3) # Give Flask a moment to boot up

def start_tunnel():
    """Start the Ngrok tunnel and generate the QR code."""
    print(f"[*] Opening secure Ngrok tunnel to port {PORT}...")
    
    # Open a HTTP tunnel on the default port 5000
    public_url = ngrok.connect(PORT).public_url
    
    print("\n" + "="*60)
    print("SUCCESS! Your Mobile App is Live.")
    print("="*60)
    print(f"\nPublic HTTPS URL: {public_url}")
    print("\nScan this QR Code with your phone's camera:")
    print("1. Open the link in Safari/Chrome.")
    print("2. Tap 'Share' -> 'Add to Home Screen' (iOS).")
    print("3. Or tap 'Menu' -> 'Install App' (Android).\n")
    
    # Generate and print ASCII QR code directly to terminal
    qr = qrcode.QRCode()
    qr.add_data(public_url)
    qr.make(fit=True)
    qr.print_ascii()
    
    print("\nPress Ctrl+C to shut down the server and tunnel.")
    
    # Keep the main thread alive to keep tunnel open
    try:
        # Block until CTRL-C or some other terminating event
        ngrok_process = ngrok.get_ngrok_process()
        ngrok_process.proc.wait()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        ngrok.kill()

if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    start_tunnel()
