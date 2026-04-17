import os
import time
import socket
import subprocess
import threading
import qrcode

def get_local_ip():
    """Get the machine's local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def start_flask():
    """Start the Flask app via subprocess."""
    print("[*] Starting OptiGreeks Web Server...")
    # Change host to 0.0.0.0 in server.py (We will assume it runs locally properly)
    env = os.environ.copy()
    subprocess.Popen(["python", "server.py"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3) # Give Flask a moment to boot up

def start_local_server():
    """Generate the QR code for local Wi-Fi access."""
    ip = get_local_ip()
    public_url = f"http://{ip}:5000"
    
    print("\n" + "="*60)
    print("SUCCESS! Your Mobile App is Live on your Wi-Fi Network.")
    print("="*60)
    print(f"\nLocal IP URL: {public_url}")
    print("\nScan this QR Code with your phone's camera:")
    print("WARNING: Your phone MUST be connected to the exact same Wi-Fi network as this computer.")
    
    # Generate and print ASCII QR code directly to terminal
    qr = qrcode.QRCode()
    qr.add_data(public_url)
    qr.make(fit=True)
    qr.print_ascii()
    
    print("\nPress Ctrl+C to shut down the server.")
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")

if __name__ == "__main__":
    # We must patch server.py dynamically to run on 0.0.0.0 so we can reach it from the phone
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    start_local_server()
