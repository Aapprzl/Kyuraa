import asyncio
import os
import time

def test_truncation():
    os.environ['KYURAA_TEST_MODE'] = '1'
    os.environ['ACTIVE_PROVIDER'] = 'google'
    os.environ['GOOGLE_API_KEY'] = 'dummy_key'
    
    from src.agent.agent_loop import AgentLoop
    
    # Patch LLMClient to simulate a mid-stream crash
    from src.agent.llm_client import LLMClient
    original_stream = LLMClient.stream
    
    crash_injected = False
    
    def mocked_stream(self, system, messages):
        nonlocal crash_injected
        # Yield first few tokens
        if not crash_injected:
            yield ("Ini adalah tes ", None, None)
            yield ("koneksi ", None, None)
            yield ("terputus", None, None)
            
            crash_injected = True
            # Raise exception mid-stream
            raise ConnectionError("Simulated Network Drop!")
        else:
            # Second call (auto-resume)
            yield ("...", None, None)
            yield (" (berhasil menyambung!)", None, "stop")
            
    LLMClient.stream = mocked_stream
            
    print("Mempersiapkan Test AgentLoop untuk Reconnect...")
    agent = AgentLoop()
    
    user_input = "Tolong analisis"
    finish_reason_captured = None
    
    print("\nStreaming response:")
    for item in agent.run_stream(user_input):
        token = item[0] if isinstance(item, tuple) else item
        finish_reason = item[2] if (isinstance(item, tuple) and len(item) > 2) else None
        
        print(token, end='', flush=True)
        if finish_reason:
            finish_reason_captured = finish_reason
            
    print(f"\n\nTest DONE. Last finish_reason: {finish_reason_captured}")

if __name__ == "__main__":
    test_truncation()
