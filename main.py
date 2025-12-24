#!/usr/bin/env python3
"""Bicameral Mind - Main Entry Point"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.bicameral_mind import BicameralMind
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


async def interactive_mode(mind: BicameralMind):
    """Interactive REPL for bicameral mind"""
    
    console.print(Panel(
        "[bold cyan]Bicameral Mind[/bold cyan]\n"
        "Type your queries, or:\n"
        "  /status - View consciousness state\n"
        "  /history - View conversation history\n"
        "  /quit - Exit",
        title="🧠 Welcome"
    ))
    
    await mind.start()
    
    try:
        while True:
            user_input = console.input("\n[bold green]You:[/bold green] ")
            
            if not user_input.strip():
                continue
            
            # Commands
            if user_input.strip() == "/quit":
                break
            
            elif user_input.strip() == "/status":
                state = mind.get_consciousness_state()
                console.print(Panel(
                    f"Mode: {state['mode']}\n"
                    f"Active: {state['active_hemisphere']}\n"
                    f"Tick Rate: {state['tick_rate']:.2f} Hz\n"
                    f"Total Ticks: {state['tick_count']}",
                    title="Consciousness State"
                ))
                continue
            
            elif user_input.strip() == "/history":
                for i, entry in enumerate(mind.conversation_history[-5:], 1):
                    console.print(f"{i}. [{entry['mode']}] {entry['input'][:50]}...")
                continue
            
            # Process query
            result = await mind.process(user_input)
            
            # Display result
            hemisphere = result.get("hemisphere", "unknown")
            mode = result.get("mode", "unknown")
            
            console.print(f"\n[bold cyan]{hemisphere.upper()} ({mode}):[/bold cyan]")
            
            if isinstance(result["output"], dict):
                output = result["output"].get("output", str(result["output"]))
            else:
                output = str(result["output"])
            
            console.print(output)
            
    except KeyboardInterrupt:
        console.print("\n\nInterrupted")
    
    finally:
        mind.stop()


async def batch_mode(mind: BicameralMind, queries: list):
    """Process batch of queries"""
    
    await mind.start()
    
    results = []
    for query in queries:
        logger.info(f"Processing: {query}")
        result = await mind.process(query)
        results.append(result)
    
    mind.stop()
    return results


def main():
    """Main entry point"""
    
    # Initialize mind
    config_path = "config/config.yaml"
    mind = BicameralMind(config_path)
    
    # Run interactive mode
    asyncio.run(interactive_mode(mind))


if __name__ == "__main__":
    main()
