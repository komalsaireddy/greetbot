"""
GreetBot Entrypoint
====================
Main script to start the GreetBot AI Assistant.
"""

import sys
import argparse
from dotenv import load_dotenv

from utils.logger import get_logger

log = get_logger(__name__)


def check_dependencies() -> None:
    """Check for required system binaries."""
    import shutil
    import config

    if config.TTS_ENGINE.lower() == "piper":
        if not shutil.which("piper"):
            log.warning("Piper TTS is not installed or not in PATH. Falling back to EdgeTTS.")

    if not shutil.which("mpg123") and not shutil.which("aplay"):
        log.warning("mpg123 or aplay is required for audio playback. Audio may fail.")


def main():
    parser = argparse.ArgumentParser(description="Start GreetBot AI Assistant")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (shows vision window)")
    parser.add_argument("--no-camera", action="store_true", help="Disable the camera")
    parser.add_argument("--no-avatar", action="store_true", help="Disable the Pygame avatar UI")
    parser.add_argument("--servo", action="store_true", help="Enable hardware servo motors (Raspberry Pi only)")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Override config based on arguments
    import config
    if args.debug:
        config.DEBUG = True
        log.info("Debug mode enabled.")
    
    if args.no_camera:
        config.CAMERA_ENABLED = False
        log.info("Camera disabled.")
        
    if args.no_avatar:
        config.AVATAR_ENABLED = False
        log.info("Avatar UI disabled.")
        
    if args.servo:
        config.SERVO_ENABLED = True
        log.info("Hardware Servos enabled.")
    else:
        config.SERVO_ENABLED = False

    check_dependencies()

    try:
        from assistant.controller import AssistantController
        controller = AssistantController()
        controller.start()
    except KeyboardInterrupt:
        print("\nShutting down GreetBot...")
    except Exception as e:
        log.critical(f"Failed to start GreetBot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
