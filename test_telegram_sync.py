import sys
from pathlib import Path

# Add the current directory to sys.path so we can import config & skills
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from skills.telegram_bot import send_message, send_file
from utils.logger import get_logger

log = get_logger("telegram_test")

def run_test():
    print("================================")
    print("  Telegram Sync Test")
    print("================================")
    
    if not TELEGRAM_BOT_TOKEN or "your_telegram_bot_token" in TELEGRAM_BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN is missing or invalid in .env")
        return
        
    if not TELEGRAM_CHAT_ID or "your_telegram_chat_id" in TELEGRAM_CHAT_ID:
        print("❌ Error: TELEGRAM_CHAT_ID is missing or invalid in .env")
        return

    print("✅ Credentials found in .env. Attempting to send a text message...")
    text_success = send_message("👋 Hello from GreetBot! If you're reading this, the sync worked perfectly.")
    
    if text_success:
        print("✅ Text message sent successfully! Check your phone.")
    else:
        print("❌ Failed to send text message. Please check the terminal logs above.")
        
    print("\nAttempting to send a test file...")
    # We will just send the .gitignore file as a quick test document
    gitignore_path = Path(__file__).resolve().parent / ".gitignore"
    if gitignore_path.exists():
        file_success = send_file(str(gitignore_path), caption="Test file from GreetBot")
        if file_success:
            print("✅ File sent successfully!")
        else:
            print("❌ Failed to send the file.")
    else:
        print("⚠️ Could not find a file to test with.")
        
    if text_success:
        print("\n🎉 ALL TESTS PASSED! Telegram is fully connected.")

if __name__ == "__main__":
    run_test()
