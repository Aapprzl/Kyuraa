import asyncio
from src.agent.agent_loop import AgentLoop
from src.agent.skill_manager import SkillManager

async def test_truncation():
    # Force language detection tool mapping
    import os
    os.environ['KYURAA_TEST_MODE'] = '1'
    os.environ['ACTIVE_PROVIDER'] = 'google'
    
    print("Mempersiapkan Test AgentLoop...")
    agent = AgentLoop()
    
    # Enable skill
    agent._skill_manager.set_active("analisis-data-4d")
    print(f"Active skill: {agent._skill_manager.active_skill}")
    
    user_input = "Tolong analisis data uji coba instrumen berikut berdasarkan metode 4D (jalur D). Data: 80, 90, 85, 75, 95, 100, 80, 85"
    print(f"\nUser Input: {user_input}")
    
    print("\nStreaming response...")
    finish_reason_captured = None
    
    for item in agent.run_stream(user_input):
        token = item[0] if (hasattr(item, '__getitem__') or isinstance(item, tuple)) else item
        finish_reason = item[2] if (hasattr(item, '__len__') and len(item) > 2) else None
        
        # print character by character like terminal
        print(token, end='', flush=True)
        if finish_reason:
            finish_reason_captured = finish_reason
            
    print(f"\n\nTest DONE. Last finish_reason: {finish_reason_captured}")

if __name__ == "__main__":
    asyncio.run(test_truncation())
