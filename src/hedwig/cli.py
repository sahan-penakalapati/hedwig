"""
Command-line interface for Hedwig.

Provides a basic CLI for testing and development of the core system
before the GUI is implemented.
"""

import argparse
import sys
from pathlib import Path
from uuid import uuid4

from hedwig.core.config import get_config, load_config
from hedwig.core.logging_config import setup_logging
from hedwig.core.models import ChatThread, TaskInput
from hedwig.core.persistence import ThreadPersistence


def setup_hedwig():
    """Initialize Hedwig configuration and logging."""
    config = get_config()
    setup_logging(config.log_level)
    config.setup_directories()
    return config


def cmd_init(args):
    """Initialize a new Hedwig configuration."""
    config_file = Path(args.config) if args.config else Path.cwd() / 'hedwig.json'
    
    if config_file.exists() and not args.force:
        print(f"Configuration file already exists: {config_file}")
        print("Use --force to overwrite")
        return 1
    
    from hedwig.core.config import ConfigManager
    ConfigManager.create_default_config_file(config_file)
    print(f"Created configuration file: {config_file}")
    
    # Create .env file if it doesn't exist
    env_file = config_file.parent / '.env'
    if not env_file.exists():
        template_content = """# Hedwig Configuration
# Add your API keys here

HEDWIG_LLM__API_KEY=your_api_key_here
HEDWIG_LLM__PROVIDER=openai
HEDWIG_LLM__MODEL=gpt-4

HEDWIG_LOG_LEVEL=INFO
"""
        with open(env_file, 'w') as f:
            f.write(template_content)
        print(f"Created environment template: {env_file}")
    
    return 0


def cmd_chat(args):
    """Start an interactive chat session."""
    config = setup_hedwig()
    
    # Initialize HedwigApp for agent processing
    try:
        from hedwig.app import HedwigApp
        hedwig_app = HedwigApp()
        print("🦉 Hedwig AI Agent System initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Hedwig agent system: {e}")
        print("Make sure all dependencies are installed and API keys are configured in .env")
        return 1
    
    # Determine thread ID
    thread_id = None
    if args.thread_id:
        from uuid import UUID
        try:
            thread_id = UUID(args.thread_id)
            print(f"📂 Using existing thread: {thread_id}")
        except ValueError:
            print(f"❌ Invalid thread ID format: {args.thread_id}")
            return 1
    else:
        print("📝 Creating new conversation thread")
    
    print("\n" + "=" * 60)
    print("🦉 HEDWIG CLI CHAT INTERFACE")
    print("=" * 60)
    print("Commands:")
    print("  • Type your message and press Enter")
    print("  • 'exit' or 'quit' to end session")
    print("  • 'help' for more commands")
    print("  • 'threads' to list all conversations")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\n🧑 You: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print("👋 Goodbye! Your conversation has been saved.")
                break
                
            elif user_input.lower() == 'help':
                print("""
🔧 Available CLI Commands:
  • exit/quit     - End the chat session
  • help          - Show this help message
  • threads       - List all conversation threads
  • clear         - Clear screen (conversation history preserved)
  • status        - Show system status
  
💡 Tips:
  • All messages are processed by Hedwig's AI agent system
  • Generated files are saved in the artifacts/ directory
  • Conversation history is automatically preserved
  • Use Ctrl+C to interrupt long-running operations
""")
                continue
                
            elif user_input.lower() == 'threads':
                # Get thread information from HedwigApp
                try:
                    threads_dir = hedwig_app.threads_dir
                    thread_dirs = [d for d in threads_dir.iterdir() if d.is_dir()]
                    
                    if not thread_dirs:
                        print("📭 No conversation threads found.")
                    else:
                        print(f"📚 Found {len(thread_dirs)} conversation threads:")
                        for i, thread_dir in enumerate(sorted(thread_dirs)[-10:], 1):  # Show last 10
                            thread_id = thread_dir.name
                            thread_file = thread_dir / "thread.json"
                            if thread_file.exists():
                                try:
                                    import json
                                    with open(thread_file, 'r') as f:
                                        data = json.load(f)
                                    msg_count = len(data.get('messages', []))
                                    created = data.get('created_at', 'Unknown')[:16]  # Show date only
                                    print(f"  {i:2}. {thread_id} ({msg_count} messages, {created})")
                                except:
                                    print(f"  {i:2}. {thread_id} (metadata unavailable)")
                            else:
                                print(f"  {i:2}. {thread_id} (no data)")
                        
                        print("\n💡 To continue a specific thread, restart with: hedwig chat --thread-id <ID>")
                except Exception as e:
                    print(f"❌ Error listing threads: {e}")
                continue
                
            elif user_input.lower() == 'clear':
                os.system('clear' if os.name == 'posix' else 'cls')
                print("🦉 Hedwig CLI - Screen cleared (conversation history preserved)")
                continue
                
            elif user_input.lower() == 'status':
                print("🔍 Hedwig System Status:")
                print(f"  • Agent System: ✅ Active")
                print(f"  • Thread ID: {hedwig_app.current_thread.thread_id if hedwig_app.current_thread else 'New session'}")
                print(f"  • Data Directory: {hedwig_app.threads_dir}")
                print(f"  • Session Stats: {hedwig_app.session_stats}")
                continue
                
            elif not user_input:
                continue
            
            # Process message with Hedwig agent system
            print("🤖 Processing with AI agents...")
            
            try:
                result = hedwig_app.run(user_input, thread_id)
                
                if result.success:
                    print(f"🦉 Assistant: {result.content}")
                    
                    # Show artifacts if any were generated
                    artifacts = result.metadata.get('artifacts', []) if result.metadata else []
                    if artifacts:
                        print(f"\n📁 Generated {len(artifacts)} file(s):")
                        for artifact in artifacts:
                            print(f"   • {artifact.file_path} ({artifact.artifact_type})")
                else:
                    print(f"❌ Error: {result.error}")
                    if result.error_code:
                        print(f"   Error Code: {result.error_code}")
                    
            except KeyboardInterrupt:
                print("\n⏹️  Operation interrupted by user")
                continue
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                print("💡 Try 'status' to check system state or 'help' for commands")
                continue
            
        except KeyboardInterrupt:
            print("\n\n👋 Session ended. Your conversation has been saved.")
            break
        except EOFError:
            print("\n👋 Session ended.")
            break
        except Exception as e:
            print(f"❌ CLI Error: {e}")
            print("💡 Type 'help' for available commands")
    
    return 0


def cmd_threads(args):
    """List available chat threads."""
    config = setup_hedwig()
    persistence = ThreadPersistence(config.get_data_dir())
    
    threads = persistence.list_threads()
    
    if not threads:
        print("No chat threads found.")
        return 0
    
    print(f"Found {len(threads)} chat threads:")
    print("-" * 80)
    
    for thread in threads:
        print(f"ID: {thread['thread_id']}")
        print(f"Created: {thread['created_at']}")
        print(f"Updated: {thread['updated_at']}")
        print(f"Messages: {thread['message_count']}")
        if thread['last_message']:
            print(f"Last: {thread['last_message'][:60]}...")
        print("-" * 80)
    
    return 0


def cmd_cleanup(args):
    """Clean up old threads and artifacts."""
    config = setup_hedwig()
    persistence = ThreadPersistence(config.get_data_dir())
    
    keep_days = args.keep_days if args.keep_days else config.artifacts.cleanup_days
    
    if not args.force:
        response = input(f"Delete threads older than {keep_days} days? [y/N]: ")
        if response.lower() != 'y':
            print("Cleanup cancelled.")
            return 0
    
    deleted_count = persistence.cleanup_old_threads(keep_days)
    print(f"Cleaned up {deleted_count} old threads.")
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Hedwig Multi-Agent Task Execution System",
        prog="hedwig"
    )
    parser.add_argument(
        "--config", "-c",
        help="Configuration file path",
        type=str
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize Hedwig configuration")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing config")
    init_parser.set_defaults(func=cmd_init)
    
    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Start interactive chat session")
    chat_parser.add_argument("--thread-id", help="Continue existing thread")
    chat_parser.set_defaults(func=cmd_chat)
    
    # Threads command
    threads_parser = subparsers.add_parser("threads", help="List chat threads")
    threads_parser.set_defaults(func=cmd_threads)
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old data")
    cleanup_parser.add_argument("--keep-days", type=int, help="Days to keep data")
    cleanup_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    cleanup_parser.set_defaults(func=cmd_cleanup)
    
    args = parser.parse_args()
    
    if args.config:
        load_config(Path(args.config))
    
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())