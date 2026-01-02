"""
ACE-Step Playground
Entry point for the Gradio-based music generation playground.
"""
import os
import sys
import argparse

# Add project root to sys.path
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from playground.playground_handler import PlaygroundHandler
    from playground.playground_ui import create_ui
except ImportError:
    # Fallback if running as script from playground directory
    sys.path.append(os.path.join(project_root, "playground"))
    from playground_handler import PlaygroundHandler
    from playground_ui import create_ui


def main():
    parser = argparse.ArgumentParser(description="ACE-Step Playground")
    parser.add_argument("--port", type=int, default=7860, help="Port to run the gradio server on")
    parser.add_argument("--share", action="store_true", help="Create a public link")
    parser.add_argument("--listen", action="store_true", help="Listen on 0.0.0.0")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("ACE-Step Playground")
    print("=" * 60)
    
    print("\n[1/2] Initializing Playground Handler...")
    handler = PlaygroundHandler()
    
    print("[2/2] Creating UI...")
    demo = create_ui(handler)
    
    server_name = "0.0.0.0" if args.listen else "127.0.0.1"
    
    print(f"\nStarting server on {server_name}:{args.port}")
    if args.share:
        print("Public link will be created...")
    
    print("\n" + "=" * 60)
    
    demo.launch(
        server_name=server_name,
        server_port=args.port,
        share=args.share
    )


if __name__ == "__main__":
    main()
