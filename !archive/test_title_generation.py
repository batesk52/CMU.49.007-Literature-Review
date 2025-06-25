#!/usr/bin/env python3
"""
Test script to demonstrate the improved title generation.
"""

import os
import requests
from dotenv import load_dotenv

def test_title_generation():
    """Test the improved title generation."""
    load_dotenv()
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return
    
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    
    # Test with a sample transcript
    test_file_name = "20250625_research_meeting.mp3"
    test_transcript = "Today we discussed the specific aims for the NIH grant proposal. The team reviewed the preliminary data and outlined the key objectives for the next phase of research. We also addressed questions about the methodology and timeline for the project."
    
    title_prompt = f"Generate a concise, descriptive title (3-8 words) for this audio recording. Return only the title text, no quotes or extra formatting. Audio filename: {test_file_name}\n\nTranscript preview: {test_transcript[:200]}..."
    
    print("=== Testing Improved Title Generation ===\n")
    print(f"Test file: {test_file_name}")
    print(f"Transcript preview: {test_transcript[:100]}...")
    print("\nGenerating title...")
    
    try:
        title_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json={
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that generates concise, descriptive titles for audio recordings. Return only the title text without any quotation marks, punctuation, or extra formatting."},
                    {"role": "user", "content": title_prompt}
                ],
                "max_tokens": 50,
                "temperature": 0.3
            }
        )
        
        if title_response.status_code == 200:
            ai_title = title_response.json()["choices"][0]["message"]["content"].strip()
            # Remove any quotation marks that might still be present
            ai_title = ai_title.replace('"', '').replace('"', '').replace('"', '').replace('"', '').replace("'", '').replace("'", '')
            final_title = f"{ai_title} - {test_file_name}"
            
            print(f"\n✓ Generated title: {final_title}")
            print(f"✓ Clean title (no quotes): {ai_title}")
            
        else:
            print(f"✗ Error: {title_response.status_code} - {title_response.text}")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")

if __name__ == "__main__":
    test_title_generation() 