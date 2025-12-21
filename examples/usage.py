"""Example: Using the Bicameral Mind"""
import asyncio
from core.bicameral_mind import BicameralMind


async def basic_example():
    """Basic usage example"""
    
    # Initialize
    mind = BicameralMind("config/config.yaml")
    await mind.start()
    
    # Process queries
    queries = [
        "What is the capital of France?",
        "Explain the concept of entropy",
        "How would you design a chat application?"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        result = await mind.process(query)
        
        print(f"Mode: {result['mode']}")
        print(f"Hemisphere: {result['hemisphere']}")
        print(f"\nResponse: {result['output']}")
        
        # Get consciousness state
        state = mind.get_consciousness_state()
        print(f"\nTick Rate: {state['tick_rate']:.2f} Hz")
    
    mind.stop()


async def rag_example():
    """Example with RAG knowledge base"""
    
    mind = BicameralMind("config/config.yaml")
    await mind.start()
    
    # Add knowledge
    documents = [
        """Quantum computing uses quantum bits (qubits) that can exist in superposition,
        allowing them to be in multiple states simultaneously. This enables exponential
        speedup for certain computational problems.""",
        
        """Machine learning is a subset of AI that enables systems to learn from data
        without explicit programming. It includes supervised, unsupervised, and
        reinforcement learning approaches."""
    ]
    
    mind.add_knowledge(documents)
    
    # Query with RAG
    result = await mind.process("What is quantum computing?", use_rag=True)
    print(result["output"])
    
    mind.stop()


async def consciousness_monitoring():
    """Monitor consciousness ticks and mode switches"""
    
    mind = BicameralMind("config/config.yaml")
    await mind.start()
    
    # Process multiple queries to trigger mode switches
    queries = [
        "What is 2+2?",                           # Binary/simple
        "Imagine a new color that doesn't exist", # Creative/exploratory
        "Is Python better than JavaScript?",      # Subjective/conflicting
    ]
    
    for query in queries:
        result = await mind.process(query)
        state = mind.get_consciousness_state()
        
        print(f"\nQuery: {query}")
        print(f"Mode: {state['mode']} | Active: {state['active_hemisphere']}")
        print(f"Tick Rate: {state['tick_rate']:.2f} Hz")
        
        await asyncio.sleep(2)  # Allow ticks to accumulate
    
    mind.stop()


if __name__ == "__main__":
    print("Running basic example...")
    asyncio.run(basic_example())
    
    # Uncomment to run other examples:
    # asyncio.run(rag_example())
    # asyncio.run(consciousness_monitoring())
