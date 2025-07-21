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
    persistence = ThreadPersistence(config.get_data_dir())
    
    # Load or create thread
    if args.thread_id:
        from uuid import UUID
        thread_id = UUID(args.thread_id)
        try:
            thread, artifact_registry = persistence.load_thread(thread_id)
            print(f"Loaded existing thread: {thread_id}")
        except Exception as e:
            print(f"Error loading thread: {e}")
            return 1
    else:
        thread_id = uuid4()
        thread = ChatThread(thread_id=thread_id)
        from hedwig.core.artifact_registry import ArtifactRegistry
        artifact_registry = ArtifactRegistry(thread_id)
        print(f"Created new thread: {thread_id}")
    
    print("Hedwig CLI Chat Interface")
    print("Type 'exit' to quit, 'help' for commands")
    print("-" * 50)
    
    # Display conversation history
    for message in thread.messages:
        print(f"{message.role}: {message.content}")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                break
            elif user_input.lower() == 'help':
                print("""
Available commands:
- exit/quit: Exit the chat
- help: Show this help
- artifacts: List current artifacts
- threads: List all threads
- Any other input will be processed as a chat message
""")
                continue
            elif user_input.lower() == 'artifacts':
                print(artifact_registry.get_artifacts_summary())
                continue
            elif user_input.lower() == 'threads':
                threads = persistence.list_threads()
                print(f"\nAvailable threads ({len(threads)}):")
                for t in threads[:10]:  # Show last 10
                    print(f"  {t['thread_id']}: {t['message_count']} messages, updated {t['updated_at']}")
                continue
            elif not user_input:
                continue
            
            # Add user message to thread
            thread.add_message("user", user_input)
            
            # TODO: Process with agent system when implemented
            # For now, just echo back
            response = f"Echo: {user_input} (Agent system not yet implemented)"
            thread.add_message("assistant", response)
            
            print(f"Assistant: {response}")
            
            # Save thread
            persistence.save_thread(thread, artifact_registry)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
    
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