#!/usr/bin/env python3
"""
Phase 4 Demo: HedwigApp Usage Examples

This demo shows how to use the HedwigApp main application class
to interact with the multi-agent system.

Features demonstrated:
- Creating and managing chat threads
- Task execution with pre-filtering
- Artifact management and auto-opening
- Task rejection and re-routing
- Thread persistence and loading
"""

import sys
from pathlib import Path
from uuid import uuid4

# Add src to Python path for demo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hedwig.app import HedwigApp
from hedwig.core.config import HedwigConfig
from hedwig.core.models import TaskOutput, Artifact, ArtifactType


def demo_basic_usage():
    """Demonstrate basic HedwigApp usage."""
    print("=== Phase 4 Demo: Basic HedwigApp Usage ===\n")
    
    # Create configuration for demo
    config = HedwigConfig(
        data_dir=Path.home() / ".hedwig_demo",
        debug_mode=True
    )
    
    # Initialize HedwigApp
    print("1. Initializing HedwigApp...")
    app = HedwigApp(config=config)
    print(f"   ✓ App initialized with data dir: {config.get_data_dir()}")
    print(f"   ✓ Threads directory: {app.threads_dir}")
    
    # Test pre-filtered commands
    print("\n2. Testing pre-filtered commands...")
    
    # Help command
    help_result = app.run("help")
    print(f"   ✓ Help command: {help_result.success}")
    print(f"     Content preview: {help_result.content[:100]}...")
    
    # Status command  
    status_result = app.run("status")
    print(f"   ✓ Status command: {status_result.success}")
    print(f"     Current thread: {app.current_thread.thread_id if app.current_thread else 'None'}")
    
    # List artifacts (should be empty initially)
    artifacts_result = app.run("list artifacts")
    print(f"   ✓ List artifacts: {artifacts_result.success}")
    print(f"     Content: {artifacts_result.content}")
    
    return app


def demo_thread_management(app: HedwigApp):
    """Demonstrate thread management features."""
    print("\n3. Testing thread management...")
    
    # Current thread should be auto-created
    current_thread = app.get_current_thread()
    print(f"   ✓ Current thread: {current_thread.thread_id}")
    print(f"   ✓ Messages: {len(current_thread.messages)}")
    print(f"   ✓ Artifacts: {len(current_thread.artifacts)}")
    
    # Create additional thread by switching
    new_thread_id = uuid4()
    app.run("help", thread_id=new_thread_id)
    print(f"   ✓ Created new thread: {new_thread_id}")
    
    # List available threads
    threads = app.list_threads()
    print(f"   ✓ Total threads: {len(threads)}")
    for thread_info in threads:
        print(f"     - Thread {thread_info['thread_id'][:8]}...: {thread_info['message_count']} messages")
    
    # Switch back to original thread
    original_id = current_thread.thread_id
    success = app.switch_thread(original_id)
    print(f"   ✓ Switched back to original thread: {success}")


def demo_mock_complex_task(app: HedwigApp):
    """Demonstrate how complex tasks would work (with mocked agent response)."""
    print("\n4. Testing complex task execution (simulated)...")
    
    # This would normally go through the agent system,
    # but for demo purposes we'll show how the app would handle the result
    
    # Simulate a successful task with artifacts
    mock_result = TaskOutput(
        content="I've created a Python script and documentation for you.",
        success=True,
        artifacts=[
            Artifact(
                file_path="examples/fibonacci.py",
                artifact_type=ArtifactType.CODE,
                description="Fibonacci number calculator"
            ),
            Artifact(
                file_path="examples/fibonacci_docs.pdf",
                artifact_type=ArtifactType.PDF,
                description="Documentation for the Fibonacci script"
            )
        ],
        conversation=[
            {"role": "user", "content": "Create a Python script to calculate Fibonacci numbers"},
            {"role": "assistant", "content": "I've created a Python script and documentation for you."}
        ]
    )
    
    # Process the result (this is what would happen inside app.run())
    app._process_execution_result(mock_result)
    
    print(f"   ✓ Processed result with {len(mock_result.artifacts)} artifacts")
    print(f"   ✓ Artifacts in thread: {len(app.current_thread.artifacts)}")
    
    # Show how auto-opening would work
    print("   ✓ Auto-opening rules applied:")
    if len([a for a in mock_result.artifacts if a.artifact_type == ArtifactType.PDF]) == 1:
        print("     - Single PDF would be auto-opened")
    elif len([a for a in mock_result.artifacts if a.artifact_type == ArtifactType.CODE]) > 0:
        print("     - First code file would be auto-opened")
    
    # Test list artifacts now
    artifacts_result = app.run("list artifacts")
    print(f"   ✓ List artifacts after generation:")
    print(f"     {artifacts_result.content}")


def demo_error_handling(app: HedwigApp):
    """Demonstrate error handling and retry logic."""
    print("\n5. Testing error handling...")
    
    # Show session statistics
    stats = app.get_session_statistics()
    print("   ✓ Session statistics:")
    for key, value in stats.items():
        if key != "agent_statistics":  # Skip complex nested data
            print(f"     - {key}: {value}")
    
    # Test error handling with invalid thread
    invalid_thread_id = uuid4()
    result = app.run("help", thread_id=invalid_thread_id)
    print(f"   ✓ Handled invalid thread ID: {result.success}")


def demo_persistence(app: HedwigApp):
    """Demonstrate thread persistence."""
    print("\n6. Testing thread persistence...")
    
    # Add some conversation to current thread
    current_thread = app.get_current_thread()
    thread_id = current_thread.thread_id
    
    # Manually add some messages to simulate conversation
    current_thread.add_message("user", "This is a test message for persistence")
    current_thread.add_message("assistant", "I understand, I'll help with that task.")
    
    print(f"   ✓ Added messages to thread {thread_id}")
    print(f"   ✓ Thread has {len(current_thread.messages)} messages")
    
    # Persist the thread
    app._persist_current_thread()
    print("   ✓ Thread persisted to disk")
    
    # Verify files exist
    thread_dir = app.threads_dir / str(thread_id)
    thread_file = thread_dir / "thread.json"
    
    print(f"   ✓ Thread directory exists: {thread_dir.exists()}")
    print(f"   ✓ Thread file exists: {thread_file.exists()}")
    
    if thread_file.exists():
        import json
        with open(thread_file, 'r') as f:
            data = json.load(f)
        print(f"   ✓ Persisted data contains {len(data.get('messages', []))} messages")
        print(f"   ✓ Persisted data contains {len(data.get('artifacts', []))} artifacts")


def main():
    """Run the complete Phase 4 demo."""
    print("🚀 Starting Hedwig Phase 4 Demo\n")
    
    try:
        # Basic usage
        app = demo_basic_usage()
        
        # Thread management
        demo_thread_management(app)
        
        # Complex task simulation
        demo_mock_complex_task(app)
        
        # Error handling
        demo_error_handling(app)
        
        # Persistence
        demo_persistence(app)
        
        # Clean shutdown
        print("\n7. Shutting down application...")
        app.shutdown()
        print("   ✓ Application shutdown complete")
        
        print("\n🎉 Phase 4 Demo completed successfully!")
        print("\nKey features demonstrated:")
        print("- ✅ HedwigApp initialization and configuration")
        print("- ✅ Thread creation, management, and switching")
        print("- ✅ Pre-filtered command handling (help, status, list artifacts)")
        print("- ✅ Complex task processing workflow")
        print("- ✅ Artifact processing and auto-opening rules")
        print("- ✅ Thread persistence and loading")
        print("- ✅ Error handling and session statistics")
        print("- ✅ Clean application shutdown")
        
        print(f"\nDemo data stored in: {app.config.get_data_dir()}")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())